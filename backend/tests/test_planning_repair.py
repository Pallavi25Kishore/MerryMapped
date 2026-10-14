from datetime import date

from app.planning.checker import MarketInfo
from app.planning.plan import Day, Plan, Settings, Travel, TripRequest, Visit
from app.planning.repair import Removed, repair

D1, D2 = date(2026, 12, 23), date(2026, 12, 24)
REQUEST = TripRequest(D1, D2)


def open_hours(opens, closes):
    return [{"kind": "opening_date", "value": {"date": "2026-11-20"}},
            {"kind": "closing_date", "value": {"date": "2026-12-24"}},
            {"kind": "hours", "value": {"days": ["mon", "tue", "wed", "thu", "fri", "sat", "sun"],
                                        "opens": opens, "closes": closes}}]


MARKETS = {1: MarketInfo("Köln market", "Köln", open_hours("11:00", "21:00")),
           2: MarketInfo("Aachen market", "Aachen", open_hours("11:00", "21:00")),
           3: MarketInfo("Short market", "Köln", open_hours("11:00", "12:00")),
           4: MarketInfo("Other Köln market", "Köln", open_hours("11:00", "21:00")),
           5: MarketInfo("Late Köln market", "Köln", open_hours("11:00", "23:59"))}
LINKS = {("Köln", "Aachen", D2): [[{"from": "Köln Hbf", "to": "Aachen Hbf", "depart": 500, "arrive": 540,
                                     "feed": "f", "estimate": False, "estimate_from": None}]]}
TO_AACHEN = Travel("Köln", "Aachen")


def plan(day1_visits, day2_visits, travel=TO_AACHEN, sleep2="Aachen"):
    return Plan((Day(D1, None, tuple(Visit(m) for m in day1_visits), "Köln"),
                 Day(D2, travel, tuple(Visit(m) for m in day2_visits), sleep2)))


def ids(repaired):
    return [[v.market_id for v in day.visits] for day in repaired.plan.days]


def test_a_plan_that_passes_is_unchanged():
    repaired = repair(plan([1], [2]), REQUEST, MARKETS, LINKS)
    assert (ids(repaired), repaired.removed, repaired.result.problems) == ([[1], [2]], [], [])


def test_only_the_market_without_enough_time_is_removed():
    repaired = repair(plan([3, 1], [2]), REQUEST, MARKETS, LINKS)
    assert ids(repaired) == [[1], [2]]
    assert repaired.result.problems == []
    assert repaired.removed[0].market_id == 3
    assert repaired.removed[0].reason.startswith("not enough time at Short market")


def test_a_market_over_the_daily_limit_is_removed():
    repaired = repair(plan([1, 4, 5], [2]), REQUEST, MARKETS, LINKS)
    assert ids(repaired) == [[1, 4], [2]]
    assert [r.market_id for r in repaired.removed] == [5]
    assert "more than 2 in one day" in repaired.removed[0].reason


def test_a_market_already_visited_is_removed():
    stay = Plan((Day(D1, None, (Visit(1),), "Köln"), Day(D2, None, (Visit(1), Visit(4)), "Köln")))
    repaired = repair(stay, REQUEST, MARKETS, LINKS)
    assert ids(repaired) == [[1], [4]]
    assert "never visit a market twice" in repaired.removed[0].reason


def test_a_day_whose_travel_fails_stays_marked_and_keeps_no_markets():
    late_trains = TripRequest(D1, D2, Settings(earliest_train=10 * 60))  # the only train leaves 08:20
    repaired = repair(plan([1], [2]), late_trains, MARKETS, LINKS)
    assert ids(repaired) == [[1], []]
    assert len(repaired.result.problems) == 1 and repaired.result.problems[0].startswith("Thu 24 Dec:")
    assert repaired.removed == [Removed(D2, 2, "this day's travel has a problem of its own, "
                                               "so its markets could not be checked")]


def test_wrong_dates_cannot_be_repaired():
    one_day = Plan((Day(D1, None, (Visit(1),), "Köln"),))
    repaired = repair(one_day, REQUEST, MARKETS, LINKS)
    assert (repaired.plan, repaired.removed) == (one_day, [])
    assert "exactly one day for each date" in repaired.result.problems[0]
