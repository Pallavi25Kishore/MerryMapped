import json
from types import SimpleNamespace

from app.reading.fact_verifier import VERDICTS_SCHEMA, verify_facts


def fact(kind, value, quote="Handwerk und Kunst aus und mit natürlichen Materialien"):
    return {"kind": kind, "value": value, "evidence_quote": quote, "evidence_translation": None}


CRAFTS = fact("detail", {"text": "handcrafts and unique gifts from natural materials"})
OPENING = fact("opening_date", {"date": "2026-11-16"}, quote="Mo 16.11.2026")
CANOPY = fact("tag", {"tag": "light-show"}, quote="unter dem funkelnden Lichterzelt")


def verdict(number, said, trimmed=None, reason=None):
    return {"id": number, "verdict": said, "trimmed": trimmed, "reason": reason}


class PretendClaude:
    """Stands in for the Anthropic client: returns prepared verdicts and records the request."""

    def __init__(self, *verdicts):
        self.verdicts = list(verdicts)
        self.requests = []
        self.messages = self  # so code can call client.messages.create(...)

    def create(self, **request):
        self.requests.append(request)
        reply = json.dumps({"verdicts": self.verdicts})
        return SimpleNamespace(content=[SimpleNamespace(type="text", text=reply)])


def test_a_supported_fact_is_kept():
    claude = PretendClaude(verdict(1, "supported"))
    verified = verify_facts([OPENING], client=claude)

    assert verified.facts == [OPENING]
    assert claude.requests[0]["output_config"]["format"]["schema"] == VERDICTS_SCHEMA


def test_a_detail_is_trimmed_to_what_its_quote_supports():
    trim = "handcrafts and gifts from natural materials"
    verified = verify_facts([CRAFTS], client=PretendClaude(verdict(1, "partly", trimmed=trim)))

    assert verified.facts == [{**CRAFTS, "value": {"text": trim}}]
    assert verified.trimmed == [("handcrafts and unique gifts from natural materials", trim)]


def test_a_trim_that_adds_words_drops_the_detail():
    claude = PretendClaude(verdict(1, "partly", trimmed="handmade presents", reason="adds unique"))
    verified = verify_facts([CRAFTS], client=claude)

    assert verified.facts == []
    assert verified.dropped == [(CRAFTS, "adds unique")]


def test_partly_on_a_date_drops_it():
    verified = verify_facts([OPENING], client=PretendClaude(verdict(1, "partly", trimmed="2026-11")))

    assert verified.facts == []
    assert verified.dropped == [(OPENING, "the quote does not support it")]


def test_unsupported_drops_with_the_reason():
    claude = PretendClaude(verdict(1, "unsupported", reason="the quote names no year"))
    verified = verify_facts([CRAFTS], client=claude)

    assert verified.dropped == [(CRAFTS, "the quote names no year")]


def test_a_fact_the_verifier_skipped_is_kept_unverified():
    verified = verify_facts([OPENING, CRAFTS], client=PretendClaude(verdict(1, "supported")))

    assert verified.facts == [OPENING, CRAFTS]
    assert verified.unverified == [CRAFTS]


def test_a_fact_without_a_quote_is_not_sent_and_kept_unverified():
    no_quote = {**OPENING, "evidence_quote": None}
    claude = PretendClaude(verdict(1, "supported"))
    verified = verify_facts([no_quote, CANOPY], client=claude)

    assert verified.facts == [no_quote, CANOPY]
    assert verified.unverified == [no_quote]
    assert 'fact id="1" kind="tag"' in claude.requests[0]["messages"][0]["content"]


def test_tags_are_sent_with_their_meaning():
    claude = PretendClaude(verdict(1, "supported"))
    verify_facts([CANOPY], client=claude)

    assert "meaning: illuminations, light installations or a light canopy" in claude.requests[0]["messages"][0]["content"]
