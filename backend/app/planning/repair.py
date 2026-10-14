from dataclasses import dataclass, field, replace
from datetime import date

from app.planning.checker import CheckResult, MarketInfo, check, hhmm
from app.planning.plan import Plan, TripRequest, Visit
from app.planning.trains import Links
from app.planning.understand import SETTING_RANGES

# Settings a tip may relax, in the order tried, with the step: earlier trains first, less time
# at each market last.
STEPS = {"earliest_train": -30, "max_travel_minutes": 30, "max_markets_per_day": 1, "min_market_minutes": -30}


@dataclass(frozen=True)
class Removed:
    """A market taken out of the plan, the checker's reason, and a tip if one setting would fit it in."""
    day: date
    market_id: int
    reason: str
    tip: str | None = None


@dataclass
class Repaired:
    """The plan with only what breaks the rules removed, its check, and what was removed. Any
    problems left are ones removing markets cannot fix (such as no train within the settings):
    their days stay in the plan, marked, with a tip in day_tips if one setting would fix them."""
    plan: Plan
    result: CheckResult
    removed: list[Removed]
    day_tips: dict[date, str] = field(default_factory=dict)


def label(day: date) -> str:
    return f"{day:%a %d %b}"


def repair(plan: Plan, request: TripRequest, markets: dict[int, MarketInfo], links: Links) -> Repaired:
    """Start from the plan without markets, then add its markets back in order, keeping each one
    only if the plan gains no problem with it. A day that has a problem of its own keeps none of
    its markets: they cannot be checked."""
    days = [replace(day, visits=()) for day in plan.days]
    result = check(Plan(tuple(days)), request, markets, links)
    if any(not problem.startswith(tuple(label(day.day) for day in days)) for problem in result.problems):
        return Repaired(plan, check(plan, request, markets, links), [])  # the dates are wrong: nothing to keep

    removed = []
    for i, day in enumerate(plan.days):
        own = [p for p in result.problems if p.startswith(label(day.day) + ":")]
        for visit in day.visits:
            if own:
                removed.append(Removed(day.day, visit.market_id, "this day's travel has a problem of its own, "
                                                                 "so its markets could not be checked"))
                continue
            days[i] = replace(days[i], visits=days[i].visits + (visit,))
            tried = check(Plan(tuple(days)), request, markets, links)
            new = [p for p in tried.problems if p not in result.problems]
            if new:
                days[i] = replace(days[i], visits=days[i].visits[:-1])
                removed.append(Removed(day.day, visit.market_id, "; ".join(p.split(": ", 1)[1] for p in new)))
            else:
                result = tried

    fixed = Plan(tuple(days))
    marked = {day.day for day in days if any(p.startswith(label(day.day) + ":") for p in result.problems)}
    day_tips = {}
    for day in marked:
        if found := tip(fixed, day, None, request, markets, links):
            day_tips[day] = found
    removed = [r if r.day in marked else replace(r, tip=tip(fixed, r.day, r.market_id, request, markets, links))
               for r in removed]
    return Repaired(fixed, result, removed, day_tips)


def phrase(setting: str, value: int) -> str:
    if setting == "earliest_train":
        return f"allowing trains from {hhmm(value)}"
    if setting == "max_travel_minutes":
        return f"allowing up to {value // 60} h {value % 60:02} min of travel a day"
    if setting == "max_markets_per_day":
        return f"allowing {value} markets a day"
    return f"spending at least {value // 60} h {value % 60:02} min at each market"


def tip(plan: Plan, day: date, market_id: int | None, request: TripRequest,
        markets: dict[int, MarketInfo], links: Links) -> str | None:
    """The smallest change to one setting that lets the day pass with the market added back
    (or, with no market, lets a marked day pass), as a sentence; None if no single setting does."""
    if market_id is not None:
        plan = Plan(tuple(replace(d, visits=d.visits + (Visit(market_id),)) if d.day == day else d
                          for d in plan.days))
    for setting, step in STEPS.items():
        low, high = SETTING_RANGES[setting]
        value = getattr(request.settings, setting) + step
        while low <= value <= high:
            trial = replace(request, settings=replace(request.settings, **{setting: value}))
            if not any(p.startswith(label(day) + ":") for p in check(plan, trial, markets, links).problems):
                return phrase(setting, value) + (" would fit it in." if market_id else " would make this day work.")
            value += step
    return None
