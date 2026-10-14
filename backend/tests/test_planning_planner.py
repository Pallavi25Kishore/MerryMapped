from datetime import date

from app.planning.checker import MarketInfo
from app.planning.plan import Settings, TripRequest
from app.planning.planner import market_text, travel_text, trip_text

D1, D2 = date(2026, 12, 23), date(2026, 12, 24)


def fact(kind, **value):
    return {"kind": kind, "value": value}


def test_trip_text_spells_out_the_request():
    request = TripRequest(D1, D2, Settings(day_trips=True), wishes="quiet markets", tags=("medieval",), start_city="Köln")
    assert trip_text(request) == (
        "Dates: Wed 23 Dec to Thu 24 Dec (2 days)\n"
        "Start city: Köln\n"
        "End city: any\n"
        "Settings: earliest train 08:00; at least 2 h 00 min at each market; at most 6 h 00 min of travel a day; "
        "up to 2 markets a day; day trips allowed\n"
        "Wishes: quiet markets\n"
        "Picked tags: medieval (a medieval theme: costumes, old crafts, period music)")


def test_market_text_lists_hours_for_each_trip_day():
    market = MarketInfo("Pretend market", "Köln", [
        fact("opening_date", date="2026-11-20"), fact("closing_date", date="2026-12-23"),
        fact("hours", days=["mon", "tue", "wed", "thu", "fri", "sat", "sun"], opens="11:00", closes="21:00"),
        fact("tag", tag="cathedral"), fact("detail", text="mulled wine stalls")], "A market by the cathedral.")
    assert market_text(1, market, [D1, D2]) == (
        "Market 1: Pretend market (Köln)\n"
        "Description: A market by the cathedral.\n"
        "Tags: cathedral\n"
        "Details: mulled wine stalls\n"
        "Open: 23 Dec 11:00-21:00; 24 Dec closed")


def leg(start, end, depart, arrive):
    return {"from": start, "to": end, "depart": depart, "arrive": arrive, "feed": "f", "estimate": False, "estimate_from": None}


def test_travel_text_uses_the_settings_and_marks_pairs_over_the_limit():
    links = {
        ("Köln", "Aachen", D1): [[leg("Köln Hbf", "Aachen Hbf", 500, 540)]],
        ("Köln", "Aachen", D2): [[leg("Köln Hbf", "Aachen Hbf", 500, 545)]],
        ("Köln", "Nürnberg", D1): [[leg("Köln Hbf", "Nürnberg Hbf", 400, 620)]],  # leaves 06:40, too early
    }
    lines = travel_text(links, [D1, D2], Settings()).splitlines()
    assert "Köln -> Aachen: 0 h 40 min to 0 h 45 min" in lines
    assert "Köln -> Nürnberg: over your limit (no train within your settings)" in lines
    assert len(lines) == 72  # every pair of our 9 cities, both ways
