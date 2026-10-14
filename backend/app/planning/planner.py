import json
from dataclasses import dataclass
from datetime import date, timedelta
from itertools import permutations
from pathlib import Path

import anthropic

from app.planning.checker import CheckResult, MarketInfo, check, hhmm
from app.planning.opening import open_window
from app.planning.plan import Day, Plan, Settings, Travel, TripRequest, Visit
from app.planning.repair import Repaired, repair
from app.planning.trains import Links, Train, pick_train
from app.reading.market_reader import TAGS
from app.settings import PLANNER_MODEL
from app.trains.stations import STATIONS

PLANNER_PROMPT = Path(__file__).resolve().parents[2] / "prompts" / "planner.md"
MAX_FIX_ROUNDS = 3  # after the first draft, the planner may fix its plan this many times


def trip_days(request: TripRequest) -> list[date]:
    return [request.first_day + timedelta(days=n) for n in range((request.last_day - request.first_day).days + 1)]


def duration(minutes: int) -> str:
    return f"{minutes // 60} h {minutes % 60:02} min"


def settings_text(settings: Settings) -> str:
    return "; ".join([
        f"earliest train {hhmm(settings.earliest_train)}",
        f"at least {duration(settings.min_market_minutes)} at each market",
        f"at most {duration(settings.max_travel_minutes)} of travel a day",
        f"up to {settings.max_markets_per_day} markets a day",
        "day trips allowed" if settings.day_trips else "no day trips",
    ])


def trip_text(request: TripRequest) -> str:
    """The request: dates, start and end city, settings, wishes and the tags found in them."""
    days = trip_days(request)
    lines = [
        f"Dates: {request.first_day:%a %d %b} to {request.last_day:%a %d %b} ({len(days)} days)",
        f"Start city: {request.start_city or 'any'}",
        f"End city: {request.end_city or 'any'}",
        f"Settings: {settings_text(request.settings)}",
        f"Wishes: {request.wishes or 'none given'}",
    ]
    if request.tags:
        lines.append("Tags from the wishes: " + "; ".join(f"{tag} ({TAGS.get(tag, 'no meaning known')})" for tag in request.tags))
    return "\n".join(lines)


def market_text(market_id: int, market: MarketInfo, days: list[date], wish_tags: tuple[str, ...] = ()) -> str:
    """One market: name, city, description, tags (and which match the wishes), details, and its
    hours on each day of the trip."""
    values = lambda kind: [fact["value"] for fact in market.facts if fact["kind"] == kind]
    hours = []
    for day in days:
        opening = open_window(market.facts, day)
        hours.append(f"{day:%d %b} " + (f"{hhmm(opening[0])}-{hhmm(opening[1])}" if isinstance(opening, tuple) else "closed"))
    lines = [f"Market {market_id}: {market.name} ({market.city})",
             f"Description: {market.description or 'none'}",
             f"Tags: {', '.join(v['tag'] for v in values('tag')) or 'none'}",
             f"Details: {'; '.join(v['text'] for v in values('detail')) or 'none'}",
             f"Open: {'; '.join(hours)}"]
    matching = [tag for tag in wish_tags if tag in {v["tag"] for v in values("tag")}]
    if matching:
        lines.insert(3, f"Matches the wishes: {', '.join(matching)}")
    return "\n".join(lines)


def travel_text(links: Links, days: list[date], settings: Settings) -> str:
    """One line per pair of our cities: how long the best train takes with the traveller's
    settings (over the trip's days), or that it is over their limit."""
    lines = []
    for from_city, to_city in permutations(STATIONS, 2):
        trains = [pick_train(links, from_city, to_city, day, settings.earliest_train, settings.max_travel_minutes)
                  for day in days]
        found = [train for train in trains if isinstance(train, Train)]
        if not found:
            lines.append(f"{from_city} -> {to_city}: over your limit (no train within your settings)")
            continue
        times = sorted(train.arrive - train.depart for train in found)
        took = duration(times[0]) if times[0] == times[-1] else f"{duration(times[0])} to {duration(times[-1])}"
        via = sorted({train.via for train in found if train.via})
        line = f"{from_city} -> {to_city}: {took}" + (f", via {', '.join(via)}" if via else "")
        missing = [day for day, train in zip(days, trains) if not isinstance(train, Train)]
        if missing:
            line += f"; no train within your settings on {', '.join(f'{d:%d %b}' for d in missing)}"
        lines.append(line)
    return "\n".join(lines)


def plan_schema(market_ids: list[int]) -> dict:
    """The answer format: city names limited to our cities and market ids to our markets."""
    city = {"type": "string", "enum": list(STATIONS)}
    travel = {"anyOf": [{"type": "object", "properties": {"from": city, "to": city},
                         "required": ["from", "to"], "additionalProperties": False},
                        {"type": "null"}]}
    visit = {"type": "object",
             "properties": {"market_id": {"type": "integer", "enum": market_ids}, "why": {"type": "string"}},
             "required": ["market_id", "why"], "additionalProperties": False}
    day = {"type": "object",
           "properties": {"date": {"type": "string", "description": "YYYY-MM-DD"}, "travel": travel,
                          "visits": {"type": "array", "items": visit}, "sleep_in": city, "travel_back": travel},
           "required": ["date", "travel", "visits", "sleep_in", "travel_back"], "additionalProperties": False}
    return {"type": "object", "properties": {"days": {"type": "array", "items": day}},
            "required": ["days"], "additionalProperties": False}


def parse_plan(reply: str) -> Plan | str:
    """The planner's answer as a Plan, or a sentence saying why it could not be read."""
    def travel(value):
        return Travel(value["from"], value["to"]) if value else None
    try:
        days = json.loads(reply)["days"]
        return Plan(tuple(Day(date.fromisoformat(d["date"]), travel(d["travel"]),
                              tuple(Visit(v["market_id"], v["why"]) for v in d["visits"]),
                              d["sleep_in"], travel(d["travel_back"])) for d in days))
    except (ValueError, KeyError, TypeError) as error:
        return f"The plan could not be read ({error}); answer again in the required format."


def plan_message(request: TripRequest, markets: dict[int, MarketInfo], links: Links) -> str:
    days = trip_days(request)
    market_blocks = "\n\n".join(market_text(market_id, market, days, request.tags) for market_id, market in sorted(markets.items()))
    return ("Plan this trip.\n\n"
            f"<trip>\n{trip_text(request)}\n</trip>\n\n"
            f"<markets>\n{market_blocks}\n</markets>\n\n"
            f"<travel>\n{travel_text(links, days, request.settings)}\n</travel>")


@dataclass
class Planned:
    """The planner's best plan (the one with the fewest problems; None if none could be read),
    its check, and the problems the checker found in each answer, in order (the last list is
    empty when the plan passed). When problems are left, repaired holds the best plan with only
    what is broken removed, and tips."""
    plan: Plan | None
    result: CheckResult
    rounds: list[list[str]]
    repaired: Repaired | None = None

    @property
    def answers(self) -> int:
        return len(self.rounds)


def plan_trip(request: TripRequest, markets: dict[int, MarketInfo], links: Links,
              client=None, model: str = PLANNER_MODEL) -> Planned:
    """Draft a plan, check it, and send the problems back for fixing, at most MAX_FIX_ROUNDS times.
    If no answer passes, the one with the fewest problems is returned (a later one on a tie),
    with its repair."""
    client = client or anthropic.Anthropic()
    messages = [{"role": "user", "content": plan_message(request, markets, links)}]
    schema = plan_schema(sorted(markets))
    best, result, rounds = None, CheckResult(), []  # best: (plan, its check)
    for _ in range(MAX_FIX_ROUNDS + 1):
        response = client.messages.create(
            model=model, max_tokens=8000, system=PLANNER_PROMPT.read_text(encoding="utf-8"),
            output_config={"format": {"type": "json_schema", "schema": schema}},
            messages=messages,
        )
        reply = next(block.text for block in response.content if block.type == "text")
        parsed = parse_plan(reply)
        if isinstance(parsed, str):
            result = CheckResult(problems=[parsed])
        else:
            result = check(parsed, request, markets, links)
            if best is None or len(result.problems) <= len(best[1].problems):
                best = (parsed, result)
        rounds.append(list(result.problems))
        if not result.problems:
            return Planned(parsed, result, rounds)
        messages.append({"role": "assistant", "content": reply})
        messages.append({"role": "user", "content":
            "The checker found these problems. Fix every one and change as little else as possible:\n"
            + "\n".join(f"- {problem}" for problem in result.problems)})
    if best is None:
        return Planned(None, result, rounds)
    return Planned(*best, rounds, repair(best[0], request, markets, links))
