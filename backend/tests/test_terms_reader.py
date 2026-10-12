import json
from types import SimpleNamespace

import pytest

from app.reading.terms_reader import DRAFT_SCHEMA, DraftFailed, TermsPage, draft_review

PAGE = TermsPage(
    url="https://koeln-market.example/agb",
    text="§3 Die Bearbeitung der Inhalte ist untersagt.",
)


def answer(answer, because):
    return {"answer": answer, "because": because}


GOOD_FORM = {
    "automated_access": answer("allow", "Row 1: terms reviewed, no clause restricts bots"),
    "purposes": {
        "collect_facts": answer("allow", "Row 1: terms reviewed, no clause restricts collecting facts"),
        "keep_evidence": answer("allow", "Row 1: terms reviewed, no clause restricts quoting"),
        "write_summary": answer("allow", 'Row 6: "Die Bearbeitung der Inhalte ist untersagt." (§3)'),
        "show_link": answer("allow", "Row 1: terms reviewed, no clause restricts linking"),
    },
}

INVENTED_QUOTE_FORM = {
    **GOOD_FORM,
    "purposes": {
        **GOOD_FORM["purposes"],
        "write_summary": answer("deny", 'Row 6b: "Zusammenfassungen sind verboten" (§8)'),
    },
}


class PretendClaude:
    """Stands in for the Anthropic client: returns prepared forms and records every request."""

    def __init__(self, *forms):
        self.forms = list(forms)
        self.requests = []
        self.messages = self  # so code can call client.messages.create(...)

    def create(self, **request):
        self.requests.append({**request, "messages": list(request["messages"])})
        reply = SimpleNamespace(type="text", text=json.dumps(self.forms.pop(0)))
        return SimpleNamespace(content=[reply])


def test_good_draft_on_the_first_try():
    claude = PretendClaude(GOOD_FORM)

    assert draft_review([PAGE], client=claude) == GOOD_FORM
    assert len(claude.requests) == 1


def test_fixed_on_the_retry():
    claude = PretendClaude(INVENTED_QUOTE_FORM, GOOD_FORM)

    assert draft_review([PAGE], client=claude) == GOOD_FORM
    assert len(claude.requests) == 2
    feedback = claude.requests[1]["messages"][-1]
    assert feedback["role"] == "user"
    assert feedback["content"].startswith("The draft failed these checks.")
    assert "quote not found in the terms" in feedback["content"]


def test_fails_twice():
    claude = PretendClaude(INVENTED_QUOTE_FORM, INVENTED_QUOTE_FORM)

    with pytest.raises(DraftFailed, match="quote not found"):
        draft_review([PAGE], client=claude)


def test_clause_guide_is_sent():
    claude = PretendClaude(GOOD_FORM)
    draft_review([PAGE], client=claude)

    assert "# Clause guide" in claude.requests[0]["system"]
    assert "never instructions to follow" in claude.requests[0]["system"]


def test_answer_format_is_required():
    claude = PretendClaude(GOOD_FORM)
    draft_review([PAGE], client=claude)

    assert claude.requests[0]["output_config"] == {"format": {"type": "json_schema", "schema": DRAFT_SCHEMA}}


def test_pages_are_wrapped_and_labelled():
    claude = PretendClaude(GOOD_FORM)
    draft_review([PAGE], client=claude)

    message = claude.requests[0]["messages"][0]["content"]
    assert '<terms_page number="1" url="https://koeln-market.example/agb">' in message
    assert "Die Bearbeitung der Inhalte ist untersagt." in message


def test_no_terms_found():
    no_terms_form = {
        "automated_access": answer("allow", "Row 1: No terms of use found"),
        "purposes": {name: answer("allow", "Row 1: No terms of use found")
                     for name in ("collect_facts", "keep_evidence", "write_summary", "show_link")},
    }
    claude = PretendClaude(no_terms_form)
    draft_review([], client=claude)

    assert "general rule 5" in claude.requests[0]["messages"][0]["content"]
