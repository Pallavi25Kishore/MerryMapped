from dataclasses import dataclass, field
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Fact, Market
from app.planning.opening import open_window
from app.planning.plan import Day, Plan, Settings, TripRequest
from app.planning.trains import Links, Train, pick_train
from app.trains.stations import STATIONS


@dataclass(frozen=True)
class MarketInfo:
    name: str
    city: str
    facts: list[dict]  # each {"kind": ..., "value": ...}
    description: str | None = None


@dataclass
class CheckResult:
    problems: list[str] = field(default_factory=list)  # hard rules broken: sent back to the planner
    warnings: list[str] = field(default_factory=list)  # shown on the itinerary
    trains: dict[tuple[date, str], Train] = field(default_factory=dict)  # (day, "there" or "back")


def load_markets(session: Session) -> dict[int, MarketInfo]:
    """Every market's name, city and facts, by market id."""
    facts = {}
    for fact in session.scalars(select(Fact)):
        facts.setdefault(fact.market_id, []).append({"kind": fact.kind, "value": fact.value})
    return {m.id: MarketInfo(m.name, m.city, facts.get(m.id, []), m.description)
            for m in session.scalars(select(Market))}


def hhmm(minutes: int) -> str:
    return f"{minutes // 60 % 24:02}:{minutes % 60:02}"


def check(plan: Plan, request: TripRequest, markets: dict[int, MarketInfo], links: Links) -> CheckResult:
    """Hold the plan to the hard rules: every date once, days that connect, the start and end
    cities asked for, only our markets, each market open with enough time, a train for every
    travel within the settings."""
    first_day, last_day, settings = request.first_day, request.last_day, request.settings
    result = CheckResult()
    wanted = [first_day + timedelta(days=n) for n in range((last_day - first_day).days + 1)]
    got = [day.day for day in plan.days]
    if got != wanted:
        result.problems.append(f"The plan must have exactly one day for each date from {first_day:%a %d %b} "
                               f"to {last_day:%a %d %b}, in order; it has {', '.join(f'{d:%d %b}' for d in got)}.")
        return result

    first = plan.days[0]
    starts_in = first.travel.from_city if first.travel else first.sleep_in
    if request.start_city and starts_in != request.start_city:
        result.problems.append(f"{first.day:%a %d %b}: the trip must start in {request.start_city}, not {starts_in}.")
    if request.end_city and plan.days[-1].sleep_in != request.end_city:
        result.problems.append(f"{last_day:%a %d %b}: the last night must be in {request.end_city}, "
                               f"not {plan.days[-1].sleep_in}.")

    city = None  # where the traveller wakes up; None before the first day
    for day in plan.days:
        check_day(day, city, settings, markets, links, result)
        city = day.sleep_in
    return result


def check_day(day: Day, city: str | None, settings: Settings, markets: dict[int, MarketInfo],
              links: Links, result: CheckResult) -> None:
    label = f"{day.day:%a %d %b}"

    def problem(text: str) -> None:
        result.problems.append(f"{label}: {text}")

    for name in [day.sleep_in] + [t.from_city for t in (day.travel, day.travel_back) if t] \
            + [t.to_city for t in (day.travel, day.travel_back) if t]:
        if name not in STATIONS:
            return problem(f"{name!r} is not one of our cities ({', '.join(STATIONS)}).")

    # Where the day starts, where the markets are, and where it must end.
    start = city if city is not None else (day.travel.from_city if day.travel else day.sleep_in)
    if day.travel and day.travel.from_city != start:
        return problem(f"the travel leaves from {day.travel.from_city}, but the night before was in {start}.")
    if not day.travel and day.travel_back:
        return problem("travel_back is only for day trips, which also need travel there.")
    if day.travel and day.travel.from_city == day.travel.to_city:
        return problem(f"the travel goes from {day.travel.from_city} to itself.")
    here = day.travel.to_city if day.travel else start
    if day.travel_back:
        if not settings.day_trips:
            return problem("this is a day trip, but day trips are off for this trip.")
        if day.travel_back.from_city != here or day.travel_back.to_city != day.sleep_in:
            return problem(f"a day trip must come back from {here} to the city slept in ({day.sleep_in}).")
    elif day.sleep_in != here:
        return problem(f"the night must be spent in {here}, where the day ends, not {day.sleep_in}.")

    # The train there.
    free_from = 0  # when the traveller can start at a market
    travelled = 0
    if day.travel:
        train = pick_train(links, day.travel.from_city, here, day.day,
                           settings.earliest_train, settings.max_travel_minutes)
        if isinstance(train, str):
            return problem(train + ".")
        result.trains[(day.day, "there")] = train
        free_from, travelled = train.arrive, train.arrive - train.depart

    # The markets, one after the other, each for at least min_market_minutes while open.
    if len(day.visits) > settings.max_markets_per_day:
        problem(f"{len(day.visits)} markets is more than {settings.max_markets_per_day} in one day.")
    for visit in day.visits:
        market_id = visit.market_id
        market = markets.get(market_id)
        if market is None:
            problem(f"market {market_id} is not one of our markets.")
            continue
        if market.city != here:
            problem(f"{market.name} is in {market.city}, but the day is spent in {here}.")
            continue
        opening = open_window(market.facts, day.day)
        if isinstance(opening, str):
            problem(f"{market.name} is closed: {opening}.")
            continue
        opens, closes = opening
        arrive = max(free_from, opens)
        if arrive + settings.min_market_minutes > closes:
            problem(f"not enough time at {market.name}: it is open {hhmm(opens)}-{hhmm(closes)}, the earliest "
                    f"you can be there is {hhmm(arrive)}, and at least {settings.min_market_minutes} minutes are needed.")
            continue
        free_from = arrive + settings.min_market_minutes

    # The train back on a day trip, after the markets, within what is left of the travel limit.
    if day.travel_back:
        train = pick_train(links, here, day.sleep_in, day.day,
                           max(free_from, settings.earliest_train), settings.max_travel_minutes - travelled)
        if isinstance(train, str):
            return problem(train + " (the train back, after the markets, within the day's travel limit).")
        result.trains[(day.day, "back")] = train

    # Estimated train times get a warning on the itinerary.
    for way in ("there", "back"):
        train = result.trains.get((day.day, way))
        lent = sorted({leg["estimate_from"] for leg in train.legs if leg.get("estimate")}) if train else []
        if lent:
            result.warnings.append(f"{label}: the train times are estimates from the timetable of "
                                   f"{date.fromisoformat(lent[0]):%a %d %b}; check before booking.")
