from datetime import date

from app.planning.checker import CheckResult, MarketInfo, hhmm
from app.planning.opening import open_window
from app.planning.plan import Plan
from app.planning.repair import Removed
from app.planning.trains import Train
from app.planning.wishes import WishNote
from app.reading.market_reader import TAGS

TILES = 3  # vibe tiles shown per market
PRACTICAL = {"vegan-options", "accessible", "paid-entry"}  # facilities, not vibe: no tile


def label(tag: str) -> str:
    return tag.replace("-", " ").capitalize()


def vibe_tiles(market: MarketInfo) -> list[str]:
    """Up to three tiles showing a market's vibe: its checked tags in the order of our tag list
    (setting, then theme, then food and extras), leaving out practical ones."""
    tags = {fact["value"]["tag"] for fact in market.facts if fact["kind"] == "tag"}
    return [label(tag) for tag in TAGS if tag in tags and tag not in PRACTICAL][:TILES]


def train_json(train: Train | None) -> dict | None:
    if train is None:
        return None
    return {"depart": hhmm(train.depart), "arrive": hhmm(train.arrive), "via": train.via,
            "legs": [{"from": leg["from"], "to": leg["to"], "depart": hhmm(leg["depart"]), "arrive": hhmm(leg["arrive"]),
                      "minutes": leg["arrive"] - leg["depart"], "railway": leg.get("feed"),
                      "estimate": bool(leg.get("estimate"))} for leg in train.legs]}


def visit_json(market_id: int, why: str, market: MarketInfo) -> dict:
    """One market on the itinerary: the planner's why line, the vibe tiles, the description, the
    "don't miss" items (its checked details, as found) and the link."""
    return {"market_id": market_id, "name": market.name, "why": why, "tiles": vibe_tiles(market),
            "description": market.description,
            "dont_miss": [fact["value"]["text"] for fact in market.facts if fact["kind"] == "detail"],
            "website": market.website}


def free_day(day, markets: dict[int, MarketInfo]) -> dict | None:
    """For a day without markets: the city it is spent in, and why it is free. "closed" when every
    market in that city is closed that day; otherwise "rest" (kept free on purpose)."""
    if day.visits:
        return None
    city = day.travel.to_city if day.travel else day.sleep_in
    here = [m for m in markets.values() if m.city == city]
    closed = all(not isinstance(open_window(m.facts, day.day), tuple) for m in here)
    return {"city": city, "reason": "closed" if here and closed else "rest"}


def build_itinerary(plan: Plan, result: CheckResult, markets: dict[int, MarketInfo], removed: list[Removed] = (),
                    day_tips: dict[date, str] = None, wish_notes: list[WishNote] = ()) -> dict:
    """What the website shows: for each day the trains, the markets (see visit_json), the city slept in, any market left out (with the reason and a tip), and the
    day's own problem if it is marked; then the estimate warnings and the wish review."""
    day_tips = day_tips or {}
    days = []
    for day in plan.days:
        prefix = f"{day.day:%a %d %b}:"
        problems = [p.removeprefix(prefix).strip() for p in result.problems if p.startswith(prefix)]
        days.append({
            "date": day.day.isoformat(),
            "travel": day.travel and {"from": day.travel.from_city, "to": day.travel.to_city,
                                      "train": train_json(result.trains.get((day.day, "there")))},
            "travel_back": day.travel_back and {"from": day.travel_back.from_city, "to": day.travel_back.to_city,
                                                "train": train_json(result.trains.get((day.day, "back")))},
            "visits": [visit_json(v.market_id, v.why, markets[v.market_id]) for v in day.visits],
            "sleep_in": day.sleep_in,
            "left_out": [{"market_id": r.market_id, "name": markets[r.market_id].name if r.market_id in markets else None,
                          "reason": r.reason, "tip": r.tip} for r in removed if r.day == day.day],
            "free_day": free_day(day, markets),
            "problem": "; ".join(problems) or None,
            "tip": day_tips.get(day.day),
        })
    return {"days": days, "warnings": result.warnings,
            "wishes": [{"wish": n.wish, "verdict": n.verdict, "note": n.note,
                        "evidence": [{"market_id": i, "text": text} for i, text in n.evidence]} for n in wish_notes]}
