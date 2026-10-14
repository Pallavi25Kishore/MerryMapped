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
    website: str | None = None


@dataclass
class CheckResult:
    problems: list[str] = field(default_factory=list)  # hard rules broken: sent back to the planner
    warnings: list[str] = field(default_factory=list)  # shown on the itinerary
    trains: dict[tuple[date, str], Train] = field(default_factory=dict)  # (day, "there" or "back")


def load_markets(session: Session) -> dict[int, MarketInfo]:
    """Every market's name, city, facts, description and website, by market id."""
    facts = {}
    for fact in session.scalars(select(Fact)):
        facts.setdefault(fact.market_id, []).append({"kind": fact.kind, "value": fact.value})
    return {m.id: MarketInfo(m.name, m.city, facts.get(m.id, []), m.description, m.website)
            for m in session.scalars(select(Market))}


def hhmm(minutes: int) -> str:
    return f"{minutes // 60 % 24:02}:{minutes % 60:02}"


def check(plan: Plan, request: TripRequest, markets: dict[int, MarketInfo], links: Links) -> CheckResult:
    """Hold the plan to the hard rules: every date once, days that connect, the start and end
    cities asked for, only our markets, each market open with enough time and visited once,
    a train for every travel within the settings."""
    first_day, last_day, settings = request.first_day, request.last_day, request.settings
    result = CheckResult()
    wanted = [first_day + timedelta(days=n) for n in range((last_day - first_day).days + 1)]
    got = [day.day for day in plan.days]
    if got != wanted:
        result.problems.append(f"The plan must have exactly one day for each date from {first_day.isoformat()} "
                               f"to {last_day.isoformat()}, in order; it has {', '.join(d.isoformat() for d in got)}.")
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

    check_repeats(plan, settings, markets, result)
    check_route(plan, request, result)
    return result


def check_route(plan: Plan, request: TripRequest, result: CheckResult) -> None:
    """The route moves onward: never sleep again in a city already left (changing trains there is
    fine). The one exception is the last night, in the end city the traveller asked for."""
    left = {}  # city -> the last day of the stay there
    previous = None
    for n, day in enumerate(plan.days):
        city = day.sleep_in
        last_night = n == len(plan.days) - 1
        if city in left and city != previous and not (last_night and city == request.end_city):
            result.problems.append(
                f"{day.day:%a %d %b}: coming back to {city}, where you stayed until {left[city]:%a %d %b}, makes the "
                "route double back. Plan onward instead, or stay longer where you are.")
        if previous is not None and city != previous:
            left.setdefault(previous, plan.days[n - 1].day)
        previous = city


MAX_DAYS_AT_A_MARKET = 2  # a second day only when genuinely needed


def check_repeats(plan: Plan, settings: Settings, markets: dict[int, MarketInfo], result: CheckResult) -> None:
    """New markets first. A market may be visited again only while staying on in its city since the
    first visit (never after leaving and coming back), only on a day when no market in that city that
    the trip never visits is open long enough, and on at most MAX_DAYS_AT_A_MARKET days while another
    market with days to spare is open that day (late in the season, the last open market can have as
    many days as needed). The same market twice on one day is never right."""
    visited = {visit.market_id for day in plan.days for visit in day.visits}
    first_visit = {}
    days_at = {}
    total_days = {}  # market -> how many days the whole plan gives it
    for day in plan.days:
        for market_id in {visit.market_id for visit in day.visits}:
            total_days[market_id] = total_days.get(market_id, 0) + 1

    def other_open_with_days_to_spare(market_id: int, when) -> bool:
        return any(other_id != market_id and total_days.get(other_id, 0) < MAX_DAYS_AT_A_MARKET
                   and isinstance(open_window(other.facts, when), tuple) for other_id, other in markets.items())

    for n, day in enumerate(plan.days):
        ids = [visit.market_id for visit in day.visits if visit.market_id in markets]
        for market_id in dict.fromkeys(ids):
            market = markets[market_id]
            if ids.count(market_id) > 1:
                result.problems.append(f"{day.day:%a %d %b}: {market.name} is planned twice on the same day; "
                                       "plan it once.")
            seen = first_visit.setdefault(market_id, day.day)
            days_at[market_id] = days_at.get(market_id, 0) + 1
            if seen == day.day:
                continue
            if days_at[market_id] > MAX_DAYS_AT_A_MARKET and other_open_with_days_to_spare(market_id, day.day):
                result.problems.append(
                    f"{day.day:%a %d %b}: {market.name} already has {MAX_DAYS_AT_A_MARKET} days. Spread the extra "
                    "days over other markets on the way, or plan a free day.")
                continue
            since = [d for d in plan.days[:n] if d.day >= seen]  # the days from the first visit until now
            if day.travel or any(d.sleep_in != market.city or d.travel_back for d in since):
                result.problems.append(
                    f"{day.day:%a %d %b}: {market.name} was already visited on {seen:%a %d %b}. Coming back to "
                    f"{market.city} for it later isn't allowed: plan a second day there only while staying on.")
                continue
            for other_id, other in markets.items():
                opening = open_window(other.facts, day.day)
                if (other_id not in visited and other.city == market.city and isinstance(opening, tuple)
                        and opening[1] - opening[0] >= settings.min_market_minutes):
                    result.problems.append(
                        f"{day.day:%a %d %b}: {market.name} was already visited on {seen:%a %d %b}, but {other.name} "
                        f"in {other.city} is open that day and not yet visited: plan the new market first.")
                    break

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
