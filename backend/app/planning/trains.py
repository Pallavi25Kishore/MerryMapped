from dataclasses import dataclass
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import TrainLink
from app.trains.connections import MAX_WAIT, MIN_CHANGE

# (from city, to city, day) -> the saved journeys, each a list of legs (dicts with from, to,
# depart, arrive, feed, estimate, estimate_from).
Links = dict[tuple[str, str, date], list[list[dict]]]


@dataclass(frozen=True)
class Train:
    """The chosen journey for one travel: its legs, and the middle city if two saved journeys
    were joined."""
    legs: tuple[dict, ...]
    via: str | None = None

    @property
    def depart(self) -> int:
        return self.legs[0]["depart"]

    @property
    def arrive(self) -> int:
        return self.legs[-1]["arrive"]


def load_links(session: Session, days: list[date]) -> Links:
    """Every saved journey on these days, for looking up without a query per travel."""
    rows = session.scalars(select(TrainLink).where(TrainLink.day.in_(days)))
    return {(row.from_city, row.to_city, row.day): row.journeys for row in rows}


def best(options: list[Train]) -> Train | None:
    """The train that arrives first; on a tie, fewer legs, then leaving later (less waiting)."""
    return min(options, key=lambda t: (t.arrive, len(t.legs), -t.depart), default=None)


def pick_train(links: Links, from_city: str, to_city: str, day: date,
               not_before: int, max_minutes: int) -> Train | str:
    """The journey from one city to another that arrives first, leaving at not_before or later
    and taking at most max_minutes. If no saved journey fits, two are joined through a middle
    city (with a change of MIN_CHANGE to MAX_WAIT minutes). Otherwise, a sentence saying why not."""
    def fits(train: Train) -> bool:
        return train.depart >= not_before and train.arrive - train.depart <= max_minutes

    direct = [Train(tuple(legs)) for legs in links.get((from_city, to_city, day), [])]
    chosen = best([train for train in direct if fits(train)])
    if chosen is not None:
        return chosen

    middles = {b for a, b, d in links if a == from_city and d == day and b != to_city}
    joined = []
    for middle in middles:
        for first in links.get((from_city, middle, day), []):
            for second in links.get((middle, to_city, day), []):
                if MIN_CHANGE <= second[0]["depart"] - first[-1]["arrive"] <= MAX_WAIT:
                    joined.append(Train(tuple(first + second), via=middle))
    chosen = best([train for train in joined if fits(train)])
    if chosen is not None:
        return chosen

    leaving = f"{not_before // 60:02}:{not_before % 60:02}"
    return (f"no train from {from_city} to {to_city} on {day:%d %b} leaves after {leaving} "
            f"and takes at most {max_minutes // 60} h {max_minutes % 60:02} min")
