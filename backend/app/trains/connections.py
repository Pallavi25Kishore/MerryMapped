from dataclasses import dataclass
from datetime import date

from app.trains.reader import Run


@dataclass(frozen=True)
class Leg:
    """One train ridden from one station to another."""
    feed: str
    trip_id: str
    day: date
    from_station: str
    to_station: str
    depart: int  # minutes after midnight of `day` (can pass 24:00)
    arrive: int


def ride(run: Run, from_names: set[str], to_names: set[str]) -> Leg | None:
    """The leg on this run from a from-station (boarding allowed) to a later to-station
    (getting off allowed), or None if the run does not make that trip."""
    for i, start in enumerate(run.stops):
        if start.station in from_names and start.can_board:
            for end in run.stops[i + 1:]:
                if end.station in to_names and end.can_alight:
                    return Leg(run.feed, run.trip_id, run.day, start.station, end.station,
                               start.depart, end.arrive)
    return None


def direct_trains(runs: list[Run], from_names: set[str], to_names: set[str]) -> list[Leg]:
    """Every direct train between the two stations, by day and departure time.

    The same train can be in two feeds (e.g. a DB train in the Eurostar feed too):
    legs on the same day that leave and arrive at the same minute are kept once."""
    legs = {}
    for run in runs:
        leg = ride(run, from_names, to_names)
        if leg is not None:
            legs.setdefault((leg.day, leg.depart, leg.arrive), leg)
    return sorted(legs.values(), key=lambda leg: (leg.day, leg.depart))
