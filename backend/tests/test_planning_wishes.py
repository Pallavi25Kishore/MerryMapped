import json
from datetime import date
from types import SimpleNamespace

from app.planning.checker import MarketInfo
from app.planning.plan import Day, Plan, Travel, TripRequest, Visit
from app.planning.wishes import WishNote, checked, review_wishes, tag_notes

D1, D2 = date(2026, 12, 15), date(2026, 12, 16)


def fact(kind, **value):
    return {"kind": kind, "value": value}


MARKETS = {
    1: MarketInfo("Old town market", "Köln", [fact("tag", tag="old-town"), fact("detail", text="mulled wine stalls")],
                  "A market in the old town."),
    2: MarketInfo("Castle market", "Aachen", [fact("tag", tag="castle")], None),
    3: MarketInfo("Not planned", "Aachen", [fact("tag", tag="medieval"), fact("detail", text="knights' tournament")]),
}
PLAN = Plan((Day(D1, None, (Visit(1),), "Köln"), Day(D2, Travel("Köln", "Aachen"), (Visit(2),), "Aachen")))


def test_picked_tags_are_judged_in_code():
    notes = tag_notes(("old-town", "medieval"), PLAN, MARKETS)
    assert notes[0] == WishNote("old-town", "met", ((1, "old-town"),), "Tagged old-town: Old town market.")
    assert notes[1].verdict == "not_met"
    assert notes[1].note.startswith("None of the planned markets is tagged medieval (")


def test_evidence_must_be_word_for_word_in_a_planned_markets_facts():
    real = WishNote("mulled wine", "met", ((1, "Mulled wine stalls"),), "Yes.")
    assert checked(real, PLAN, MARKETS) == real
    made_up = WishNote("mulled wine", "met", ((1, "hot chocolate stalls"),), "Yes.")
    assert checked(made_up, PLAN, MARKETS) == WishNote("mulled wine", "no_information", (), "Our checked facts don't show this.")


def test_evidence_from_a_market_not_in_the_plan_does_not_count():
    note = WishNote("knights", "met", ((3, "knights' tournament"),), "Yes.")
    assert checked(note, PLAN, MARKETS).verdict == "no_information"


def test_not_met_and_no_information_keep_their_verdict():
    for verdict in ("not_met", "no_information"):
        note = WishNote("quiet", verdict, (), "Not shown.")
        assert checked(note, PLAN, MARKETS) == note


class PretendClaude:
    def __init__(self, answer):
        self.answer, self.requests, self.messages = answer, [], self

    def create(self, **request):
        self.requests.append(request)
        return SimpleNamespace(content=[SimpleNamespace(type="text", text=json.dumps(self.answer))])


def test_review_wishes_combines_tags_typed_wishes_and_what_we_cannot_do():
    claude = PretendClaude({"wishes": [
        {"wish": "mulled wine", "verdict": "met", "evidence": [{"market_id": 1, "text": "mulled wine stalls"}], "note": "Köln has it."},
        {"wish": "not too touristy", "verdict": "no_information", "evidence": [], "note": "Our facts don't say."}]})
    request = TripRequest(D1, D2, wishes="mulled wine; not too touristy", tags=("castle",))
    notes = review_wishes(request, PLAN, MARKETS, not_covered=["Vienna"], client=claude)
    assert [(n.wish, n.verdict) for n in notes] == [
        ("castle", "met"), ("mulled wine", "met"), ("not too touristy", "no_information"), ("Vienna", "not_covered")]
    message = claude.requests[0]["messages"][0]["content"]
    assert "- not too touristy" in message and "Not planned" not in message  # only planned markets' facts


def test_no_typed_wishes_means_no_ai_call():
    notes = review_wishes(TripRequest(D1, D2, tags=("castle",)), PLAN, MARKETS, client=None)
    assert [n.verdict for n in notes] == ["met"]
