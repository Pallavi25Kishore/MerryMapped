import json
from types import SimpleNamespace

import pytest

from app.reading.description_writer import DescriptionFailed, write_description

PAGE = "Über 140 festlich geschmückte Stände. Over 140 festively decorated stalls offering arts and crafts."


def fact(kind, value, quote):
    return {"kind": kind, "value": value, "evidence_quote": quote, "evidence_translation": None}


FACTS = [
    fact("opening_date", {"date": "2026-11-16"}, "Mo 16.11. bis Di 23.12.2026"),
    fact("closing_date", {"date": "2026-12-23"}, "Mo 16.11. bis Di 23.12.2026"),
    fact("closed_on", {"date": "2026-11-22"}, "Am Totensonntag geschlossen"),
    fact("hours", {"days": ["sat"], "opens": "10:00", "closes": "22:00"}, "Sa 10-22 Uhr"),
    fact("address", {"text": "Roncalliplatz"}, "Auf dem Roncalliplatz"),
    fact("detail", {"text": "over 140 stalls"}, "Über 140 festlich geschmückte Stände"),
    fact("tag", {"tag": "artisan"}, "Kunsthandwerk"),
]

GOOD = "A large cathedral-side market on Roncalliplatz. It runs from mid-November to 23 December."
COPIED = "Expect over 140 festively decorated stalls offering arts and crafts."
TOO_LONG = "One. Two. Three. Four. Five. Six. Seven."


class PretendClaude:
    """Stands in for the Anthropic client: returns prepared descriptions and records every request."""

    def __init__(self, *descriptions):
        self.descriptions = list(descriptions)
        self.requests = []
        self.messages = self  # so code can call client.messages.create(...)

    def create(self, **request):
        self.requests.append({**request, "messages": list(request["messages"])})
        reply = json.dumps({"description": self.descriptions.pop(0)})
        return SimpleNamespace(content=[SimpleNamespace(type="text", text=reply)])


def write(claude):
    return write_description("Pretend Cathedral Market", "Köln", "DE", FACTS, [PAGE], client=claude)


def test_a_good_description_on_the_first_try():
    claude = PretendClaude(GOOD)

    assert write(claude) == GOOD
    assert len(claude.requests) == 1


def test_copied_wording_is_fixed_on_the_retry():
    claude = PretendClaude(COPIED, GOOD)

    assert write(claude) == GOOD
    feedback = claude.requests[1]["messages"][-1]["content"]
    assert 'copied wording: "over 140 festively decorated stalls offering arts and crafts"' in feedback


def test_two_failures_give_no_description():
    with pytest.raises(DescriptionFailed, match="7 sentences, at most 5"):
        write(PretendClaude(TOO_LONG, TOO_LONG))


def test_the_sites_quotes_are_never_sent():
    claude = PretendClaude(GOOD)
    write(claude)
    sent = claude.requests[0]["messages"][0]["content"]

    for f in FACTS:
        assert f["evidence_quote"] not in sent


def test_the_facts_are_sent_without_the_hours():
    claude = PretendClaude(GOOD)
    write(claude)
    sent = claude.requests[0]["messages"][0]["content"]

    assert "Market: Pretend Cathedral Market, Köln, DE" in sent
    assert "Season: 2026-11-16 to 2026-12-23" in sent
    assert "Closed: 2026-11-22" in sent
    assert "Where: Roncalliplatz" in sent
    assert "Details: over 140 stalls" in sent
    assert "Features: handcrafts and makers" in sent
    assert "artisan" not in sent
    assert "10:00" not in sent
