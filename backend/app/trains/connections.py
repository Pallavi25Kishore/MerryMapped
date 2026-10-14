import re
import unicodedata
from bisect import bisect_left, bisect_right
from collections import defaultdict
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
    starts = {simplify(name) for name in from_names}
    ends = {simplify(name) for name in to_names}
    for i, start in enumerate(run.stops):
        if simplify(start.station) in starts and start.can_board:
            for end in run.stops[i + 1:]:
                if simplify(end.station) in ends and end.can_alight:
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


MIN_CHANGE = 10  # minutes to change trains: enough to cross a big station
MAX_WAIT = 90  # minutes: a longer wait at the change station is not a good connection
FEWER_CHANGES_WORTH = 30  # minutes: a trip with fewer changes is kept if it arrives at most this much later
MAX_CHANGES = 2


@dataclass(frozen=True)
class Journey:
    """A trip from A to B: one leg (direct) or more (one leg per train, up to two changes)."""
    legs: tuple[Leg, ...]

    @property
    def day(self) -> date:
        return self.legs[0].day

    @property
    def depart(self) -> int:
        return self.legs[0].depart

    @property
    def arrive(self) -> int:
        return self.legs[-1].arrive

    @property
    def changes(self) -> int:
        return len(self.legs) - 1


COUNTRY_TAG = re.compile(r"\s*\((?:DE|FR|BE|NL|LU|CH|AT|IT|GB|UK)\)\s*$")


def simplify(station: str) -> str:
    """A station name for matching across feeds: "Bruxelles-Midi" matches "Bruxelles Midi",
    "Köln Hbf (DE)" matches "Köln Hbf", and "Liège" matches "Liege"."""
    name = COUNTRY_TAG.sub("", station)
    name = "".join(ch for ch in unicodedata.normalize("NFKD", name) if not unicodedata.combining(ch))
    return "".join(ch for ch in name.lower() if ch not in " -().,")


def legs_onward(run: Run, i: int, skip: set[str]) -> list[Leg]:
    """Legs on this run from stop i to each later stop where you may get off (except skipped stations)."""
    start = run.stops[i]
    return [Leg(run.feed, run.trip_id, run.day, start.station, stop.station, start.depart, stop.arrive)
            for stop in run.stops[i + 1:]
            if stop.can_alight and simplify(stop.station) not in skip]


class Departures:
    """Legs grouped by (day, station), sorted by departure, so the legs leaving within the
    change window after an arrival are found quickly."""

    def __init__(self, legs: list[Leg]):
        groups = defaultdict(list)
        for leg in legs:
            groups[(leg.day, simplify(leg.from_station))].append(leg)
        self.legs = {key: sorted(group, key=lambda leg: leg.depart) for key, group in groups.items()}
        self.times = {key: [leg.depart for leg in group] for key, group in self.legs.items()}

    def after(self, arrival: Leg) -> list[Leg]:
        """Legs leaving the station `arrival` reaches, MIN_CHANGE to MAX_WAIT minutes after it arrives,
        on a different train."""
        key = (arrival.day, simplify(arrival.to_station))
        times = self.times.get(key, [])
        lo = bisect_left(times, arrival.arrive + MIN_CHANGE)
        hi = bisect_right(times, arrival.arrive + MAX_WAIT)
        return [leg for leg in self.legs.get(key, [])[lo:hi]
                if (leg.feed, leg.trip_id) != (arrival.feed, arrival.trip_id)]


def with_changes(runs: list[Run], from_names: set[str], to_names: set[str]) -> list[Journey]:
    """Journeys with one or two changes: train 1 from A to a station X, then either the train
    from X that reaches B earliest, or a middle train from X to a station Y and then the train
    from Y that reaches B earliest. Every change takes MIN_CHANGE to MAX_WAIT minutes."""
    starts = {simplify(name) for name in from_names}
    ends = {simplify(name) for name in to_names}
    skip = starts | ends

    # Every place you can board a train that later reaches B, with the leg from there to B.
    # Every place you can board any train, as a leg that goes only one stop: the middle train
    # is then ridden on from there with legs_onward, so its legs are made only when needed.
    to_b, boardings, runs_by_trip = [], [], {}
    for run in runs:
        runs_by_trip[(run.feed, run.trip_id, run.day)] = run
        keys = [simplify(stop.station) for stop in run.stops]
        last = next((j for j, stop in enumerate(run.stops) if keys[j] in ends and stop.can_alight), None)
        for i, stop in enumerate(run.stops[:-1]):
            if not stop.can_board or keys[i] in skip:
                continue
            if last is not None and i < last:
                to_b.append(Leg(run.feed, run.trip_id, run.day, stop.station, run.stops[last].station,
                                stop.depart, run.stops[last].arrive))
            boardings.append(Leg(run.feed, run.trip_id, run.day, stop.station, str(i), stop.depart, stop.depart))
    to_b, boardings = Departures(to_b), Departures(boardings)

    def earliest_to_b(arrival: Leg, *earlier: Leg) -> Leg | None:
        used = {(leg.feed, leg.trip_id) for leg in earlier}
        options = [leg for leg in to_b.after(arrival) if (leg.feed, leg.trip_id) not in used]
        return min(options, key=lambda leg: leg.arrive, default=None)

    found = []
    for run in runs:
        first = next((i for i, stop in enumerate(run.stops)
                      if simplify(stop.station) in starts and stop.can_board), None)
        if first is None:
            continue
        for leg1 in legs_onward(run, first, skip):
            last = earliest_to_b(leg1)
            if last is not None:
                found.append(Journey((leg1, last)))
            for boarding in boardings.after(leg1):
                middle_run = runs_by_trip[(boarding.feed, boarding.trip_id, boarding.day)]
                x = simplify(leg1.to_station)
                for leg2 in legs_onward(middle_run, int(boarding.to_station), skip | {x}):
                    last = earliest_to_b(leg2, leg1)
                    if last is not None:
                        found.append(Journey((leg1, leg2, last)))
    return found


def keep_best(journeys: list[Journey]) -> list[Journey]:
    """Drop journeys that are clearly worse. A journey is dropped if another journey on the same
    day leaves no earlier and either arrives no later with no more changes, or arrives more than
    FEWER_CHANGES_WORTH minutes earlier with more changes. Sorted by day and departure."""
    kept = []
    order = sorted(journeys, key=lambda j: (j.day, -j.depart, j.arrive, j.changes))
    best = {}  # (day, changes) -> earliest arrival among journeys leaving at this time or later
    for journey in order:
        arrivals = {c: best.get((journey.day, c), float("inf")) for c in range(MAX_CHANGES + 1)}
        beaten = (any(arrivals[c] <= journey.arrive for c in range(journey.changes + 1))
                  or any(arrivals[c] < journey.arrive - FEWER_CHANGES_WORTH
                         for c in range(journey.changes + 1, MAX_CHANGES + 1)))
        if not beaten:
            kept.append(journey)
        key = (journey.day, journey.changes)
        best[key] = min(best.get(key, float("inf")), journey.arrive)
    return sorted(kept, key=lambda j: (j.day, j.depart))


def journeys(runs: list[Run], from_names: set[str], to_names: set[str]) -> list[Journey]:
    """The good journeys from A to B: direct trains and trips with up to two changes,
    worse ones dropped."""
    direct = [Journey((leg,)) for leg in direct_trains(runs, from_names, to_names)]
    return keep_best(direct + with_changes(runs, from_names, to_names))
