from dataclasses import dataclass, replace
from datetime import date

from app.planning.checker import CheckResult, MarketInfo, check
from app.planning.plan import Plan, TripRequest
from app.planning.trains import Links


@dataclass(frozen=True)
class Removed:
    """A market taken out of the plan, and the checker's reason."""
    day: date
    market_id: int
    reason: str


@dataclass
class Repaired:
    """The plan with only what breaks the rules removed, its check, and what was removed. Any
    problems left are ones removing markets cannot fix (such as no train within the settings):
    their days stay in the plan, marked."""
    plan: Plan
    result: CheckResult
    removed: list[Removed]


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
    return Repaired(Plan(tuple(days)), result, removed)
