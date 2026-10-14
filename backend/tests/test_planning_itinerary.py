from datetime import date

from app.planning.checker import CheckResult, MarketInfo
from app.planning.itinerary import build_itinerary, vibe_tiles
from app.planning.plan import Day, Plan, Travel, Visit
from app.planning.repair import Removed
from app.planning.trains import Train
from app.planning.wishes import WishNote


def tagged(*tags: str) -> MarketInfo:
    return MarketInfo("A market", "Köln", [{"kind": "tag", "value": {"tag": tag}} for tag in tags]
                      + [{"kind": "detail", "value": {"text": "mulled wine"}}])


def test_tiles_follow_our_tag_list_order_and_stop_at_three():
    market = tagged("stage-programme", "light-show", "family", "sustainable", "cathedral", "artisan")
    assert vibe_tiles(market) == ["Cathedral", "Light show", "Sustainable"]


def test_practical_tags_get_no_tile():
    assert vibe_tiles(tagged("vegan-options", "family", "paid-entry", "accessible")) == ["Family"]


def test_a_market_without_tags_has_no_tiles():
    assert vibe_tiles(tagged()) == []



D1, D2 = date(2026, 12, 23), date(2026, 12, 24)
MARKETS = {1: MarketInfo("Köln market", "Köln", [{"kind": "tag", "value": {"tag": "cathedral"}},
                                                  {"kind": "detail", "value": {"text": "mulled wine"}}],
                         "A market by the cathedral.", "https://koeln-market.example/"),
           2: MarketInfo("Aachen market", "Aachen", [], None, "https://aachen-market.example/")}
TRAIN = Train(({"from": "Köln Hbf", "to": "Aachen Hbf", "depart": 500, "arrive": 540},))


def test_the_itinerary_shows_trains_markets_and_wishes():
    plan = Plan((Day(D1, None, (Visit(1, "By the cathedral, as you wished."),), "Köln"),
                 Day(D2, Travel("Köln", "Aachen"), (Visit(2),), "Aachen")))
    result = CheckResult(warnings=["Thu 24 Dec: the train times are estimates"], trains={(D2, "there"): TRAIN})
    notes = [WishNote("mulled wine", "met", ((1, "mulled wine"),), "Köln market has mulled wine.")]
    itinerary = build_itinerary(plan, result, MARKETS, wish_notes=notes)
    first, second = itinerary["days"]
    assert first["travel"] is None and first["sleep_in"] == "Köln"
    assert first["visits"] == [{"market_id": 1, "name": "Köln market", "why": "By the cathedral, as you wished.",
                                "tiles": ["Cathedral"], "description": "A market by the cathedral.",
                                "dont_miss": ["mulled wine"], "website": "https://koeln-market.example/"}]
    assert second["travel"] == {"from": "Köln", "to": "Aachen", "train": {
        "depart": "08:20", "arrive": "09:00", "via": None,
        "legs": [{"from": "Köln Hbf", "to": "Aachen Hbf", "depart": "08:20", "arrive": "09:00"}]}}
    assert second["visits"][0]["tiles"] == [] and second["visits"][0]["website"] == "https://aachen-market.example/"
    assert itinerary["warnings"] == ["Thu 24 Dec: the train times are estimates"]
    assert itinerary["wishes"] == [{"wish": "mulled wine", "verdict": "met", "note": "Köln market has mulled wine.",
                                    "evidence": [{"market_id": 1, "text": "mulled wine"}]}]


def test_left_out_markets_and_a_marked_day_are_shown_with_tips():
    plan = Plan((Day(D1, None, (), "Köln"), Day(D2, Travel("Köln", "Aachen"), (), "Aachen")))
    result = CheckResult(problems=["Thu 24 Dec: no train from Köln to Aachen fits your settings."])
    removed = [Removed(D2, 2, "this day's travel has a problem of its own, so its markets could not be checked")]
    itinerary = build_itinerary(plan, result, MARKETS, removed, {D2: "allowing trains from 08:00 would make this day work."})
    first, second = itinerary["days"]
    assert (first["problem"], first["left_out"]) == (None, [])
    assert second["travel"]["train"] is None
    assert second["problem"] == "no train from Köln to Aachen fits your settings."
    assert second["tip"] == "allowing trains from 08:00 would make this day work."
    assert second["left_out"] == [{"market_id": 2, "name": "Aachen market", "reason": removed[0].reason, "tip": None}]
