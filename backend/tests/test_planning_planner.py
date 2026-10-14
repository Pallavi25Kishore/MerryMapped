import json
from datetime import date
from types import SimpleNamespace

from app.planning.checker import MarketInfo
from app.planning.plan import Settings, TripRequest
from app.planning.planner import MAX_FIX_ROUNDS, market_text, plan_schema, plan_trip, travel_text, trip_text

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
        "Tags from the wishes: medieval (a medieval town, old crafts or period music)")


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



def test_market_text_marks_tags_that_match_the_wishes():
    market = MarketInfo("Pretend market", "Köln", [fact("tag", tag="cathedral"), fact("tag", tag="old-town")])
    text = market_text(1, market, [D1], wish_tags=("old-town", "medieval"))
    assert "Tags: cathedral, old-town\nMatches the wishes: old-town\nDetails:" in text
    assert "Matches the wishes" not in market_text(1, market, [D1], wish_tags=("medieval",))

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



class PretendClaude:
    """Stands in for the Anthropic client: returns prepared answers and records every request."""

    def __init__(self, *answers):
        self.answers = list(answers)
        self.requests = []
        self.messages = self

    def create(self, **request):
        self.requests.append({**request, "messages": list(request["messages"])})
        answer = self.answers.pop(0)
        text = answer if isinstance(answer, str) else json.dumps(answer)
        return SimpleNamespace(content=[SimpleNamespace(type="text", text=text)])


OPEN = [fact("opening_date", date="2026-11-20"), fact("closing_date", date="2026-12-24"),
        fact("hours", days=["mon", "tue", "wed", "thu", "fri", "sat", "sun"], opens="11:00", closes="21:00")]
MARKETS = {1: MarketInfo("Köln market", "Köln", OPEN), 2: MarketInfo("Aachen market", "Aachen", OPEN)}
LINKS = {("Köln", "Aachen", D2): [[leg("Köln Hbf", "Aachen Hbf", 500, 540)]]}
REQUEST = TripRequest(D1, D2)


def day(when, visits, sleep_in, travel=None):
    return {"date": when, "travel": travel, "visits": [{"market_id": m, "why": "why"} for m in visits],
            "sleep_in": sleep_in, "travel_back": None}


GOOD = {"days": [day("2026-12-23", [1], "Köln"), day("2026-12-24", [2], "Aachen", {"from": "Köln", "to": "Aachen"})]}
WRONG_BED = {"days": [day("2026-12-23", [1], "Köln"), day("2026-12-24", [2], "Köln", {"from": "Köln", "to": "Aachen"})]}


def test_a_good_first_plan_is_kept():
    planned = plan_trip(REQUEST, MARKETS, LINKS, client=PretendClaude(GOOD))
    assert (planned.answers, planned.result.problems) == (1, [])
    assert planned.plan.days[1].visits[0].market_id == 2
    assert planned.result.trains[(D2, "there")].depart == 500


def test_problems_go_back_to_the_planner_until_fixed():
    claude = PretendClaude(WRONG_BED, GOOD)
    planned = plan_trip(REQUEST, MARKETS, LINKS, client=claude)
    assert (planned.answers, planned.result.problems) == (2, [])
    assert planned.rounds == [["Thu 24 Dec: the night must be spent in Aachen, where the day ends, not Köln."], []]
    feedback = claude.requests[1]["messages"][-1]["content"]
    assert "- Thu 24 Dec: the night must be spent in Aachen, where the day ends, not Köln." in feedback


def test_an_unreadable_answer_is_a_problem_too():
    claude = PretendClaude('{"days": [{"date": "24th"}]}', GOOD)
    planned = plan_trip(REQUEST, MARKETS, LINKS, client=claude)
    assert planned.answers == 2
    assert "could not be read" in claude.requests[1]["messages"][-1]["content"]


def test_gives_up_after_the_fixing_rounds_and_returns_the_problems():
    claude = PretendClaude(*[WRONG_BED] * (MAX_FIX_ROUNDS + 1))
    planned = plan_trip(REQUEST, MARKETS, LINKS, client=claude)
    assert planned.answers == MAX_FIX_ROUNDS + 1
    assert planned.result.problems and planned.plan is not None


def test_the_answer_format_allows_only_our_cities_and_markets():
    schema = plan_schema([1, 2])
    day_schema = schema["properties"]["days"]["items"]
    assert day_schema["properties"]["visits"]["items"]["properties"]["market_id"]["enum"] == [1, 2]
    assert "Brugge" in day_schema["properties"]["sleep_in"]["enum"]
