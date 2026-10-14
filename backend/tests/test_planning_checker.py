from dataclasses import replace
from datetime import date

from app.planning.checker import MarketInfo, check
from app.planning.plan import Day, Plan, Settings, Travel, TripRequest, Visit

D1, D2 = date(2026, 12, 15), date(2026, 12, 16)  # Tuesday, Wednesday


def fact(kind, **value):
    return {"kind": kind, "value": value}


def market(name, city, opens="11:00", closes="21:00", last="2026-12-23"):
    return MarketInfo(name, city, [
        fact("opening_date", date="2026-11-20"), fact("closing_date", date=last),
        fact("hours", days=["mon", "tue", "wed", "thu", "fri", "sat", "sun"], opens=opens, closes=closes)])


MARKETS = {1: market("Dom market", "Köln"), 2: market("Angel market", "Köln"),
           3: market("Aachen market", "Aachen", closes="19:00"), 4: market("Short season", "Aachen", last="2026-12-15")}


def leg(start, end, depart, arrive, estimate_from=None):
    return {"from": start, "to": end, "depart": depart, "arrive": arrive, "feed": "f",
            "estimate": estimate_from is not None, "estimate_from": estimate_from}


LINKS = {
    ("Köln", "Aachen", D2): [[leg("Köln Hbf", "Aachen Hbf", 495, 528, "2026-11-04")],  # 08:15 -> 08:48
                             [leg("Köln Hbf", "Aachen Hbf", 960, 1000)]],  # 16:00 -> 16:40
    ("Aachen", "Köln", D2): [[leg("Aachen Hbf", "Köln Hbf", 1230, 1265)]],  # 20:30 -> 21:05
}


def plan(*days):
    return Plan(tuple(days))


def visits(*market_ids):
    return tuple(Visit(market_id, "why") for market_id in market_ids)


GOOD = plan(Day(D1, None, visits(1, 2), "Köln"),
            Day(D2, Travel("Köln", "Aachen"), visits(3), "Aachen"))


def run(p, settings=Settings(), markets=MARKETS, **request):
    return check(p, TripRequest(D1, D2, settings, **request), markets, LINKS)


def test_a_good_plan_has_no_problems_and_gets_its_trains():
    result = run(GOOD)
    assert result.problems == []
    assert result.trains[(D2, "there")].depart == 495
    assert result.warnings == ["Wed 16 Dec: the train times are estimates from the timetable of Wed 04 Nov; "
                               "check before booking."]


def test_every_date_exactly_once():
    result = run(plan(GOOD.days[0]))
    assert result.problems == ["The plan must have exactly one day for each date from 2026-12-15 to 2026-12-16, "
                               "in order; it has 2026-12-15."]
    wrong_year = run(plan(replace(GOOD.days[0], day=date(2025, 12, 15)), GOOD.days[1]))
    assert "it has 2025-12-15, 2026-12-16" in wrong_year.problems[0]


def test_days_must_connect():
    p = plan(GOOD.days[0], Day(D2, Travel("Aachen", "Köln"), visits(), "Köln"))
    assert run(p).problems == ["Wed 16 Dec: the travel leaves from Aachen, but the night before was in Köln."]


def test_sleep_where_the_day_ends():
    p = plan(GOOD.days[0], Day(D2, Travel("Köln", "Aachen"), visits(3), "Köln"))
    assert run(p).problems == ["Wed 16 Dec: the night must be spent in Aachen, where the day ends, not Köln."]


def test_only_our_cities_and_markets():
    p = plan(Day(D1, None, visits(99), "Köln"), Day(D2, None, visits(), "Paris"))
    assert run(p).problems == ["Tue 15 Dec: market 99 is not one of our markets.",
                               "Wed 16 Dec: 'Paris' is not one of our cities ("
                               "Köln, Aachen, Nürnberg, Rothenburg ob der Tauber, Dresden, Strasbourg, Colmar, Brussels, Brugge)."]


def test_market_in_another_city():
    p = plan(Day(D1, None, visits(3), "Köln"), Day(D2, None, visits(), "Köln"))
    assert run(p).problems == ["Tue 15 Dec: Aachen market is in Aachen, but the day is spent in Köln."]


def test_market_closed_that_day():
    p = plan(GOOD.days[0], Day(D2, Travel("Köln", "Aachen"), visits(4), "Aachen"))
    assert run(p).problems == ["Wed 16 Dec: Short season is closed: it is only open from 20 Nov to 15 Dec."]


def test_too_many_markets():
    p = plan(Day(D1, None, visits(1, 2), "Köln"), GOOD.days[1])
    assert run(p, Settings(max_markets_per_day=1)).problems == ["Tue 15 Dec: 2 markets is more than 1 in one day."]


def test_not_enough_time_after_a_late_train():
    # Earliest train allowed is 10:00, so the 16:00 train arrives 16:40; Aachen closes 19:00, so
    # one market fits (16:40-18:40) but a 3-hour stay does not.
    settings = Settings(earliest_train=600, min_market_minutes=180)
    problems = run(GOOD, settings).problems
    assert problems == ["Wed 16 Dec: not enough time at Aachen market: it is open 11:00-19:00, "
                        "the earliest you can be there is 16:40, and at least 180 minutes are needed."]


def test_two_markets_must_both_fit():
    late = {**MARKETS, 2: market("Angel market", "Köln", opens="11:00", closes="14:30")}
    problems = run(GOOD, Settings(min_market_minutes=120), late).problems
    assert problems == ["Tue 15 Dec: not enough time at Angel market: it is open 11:00-14:30, "
                        "the earliest you can be there is 13:00, and at least 120 minutes are needed."]


def test_no_train_within_the_settings():
    problems = run(GOOD, Settings(earliest_train=17 * 60)).problems
    assert problems == ["Wed 16 Dec: no train from Köln to Aachen on 16 Dec leaves after 17:00 "
                        "and takes at most 6 h 00 min."]


DAY_TRIP = plan(GOOD.days[0], Day(D2, Travel("Köln", "Aachen"), visits(3), "Köln", travel_back=Travel("Aachen", "Köln")))


def test_day_trips_are_off_by_default():
    assert run(DAY_TRIP).problems == ["Wed 16 Dec: this is a day trip, but day trips are off for this trip."]


def test_a_day_trip_when_allowed_gets_a_train_back_after_the_market():
    result = run(DAY_TRIP, Settings(day_trips=True))
    assert result.problems == []
    assert result.trains[(D2, "back")].depart == 1230  # 20:30, after the market (08:48 + 2 h)


def test_start_and_end_cities_when_asked():
    assert run(GOOD, start_city="Köln", end_city="Aachen").problems == []
    assert run(GOOD, start_city="Aachen", end_city="Köln").problems == [
        "Tue 15 Dec: the trip must start in Aachen, not Köln.",
        "Wed 16 Dec: the last night must be in Köln, not Aachen."]


def test_never_visit_a_market_twice():
    p = plan(Day(D1, None, visits(1), "Köln"), Day(D2, None, visits(2, 1), "Köln"))
    assert run(p).problems == ["Wed 16 Dec: Dom market is already visited on Tue 15 Dec; never visit a market twice."]
