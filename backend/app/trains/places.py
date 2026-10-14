import math
from collections import defaultdict
from dataclasses import replace

from app.trains.connections import simplify
from app.trains.reader import Run
from app.trains.stations import POSITIONS, STATIONS

SAME_PLACE_KM = 5  # stops with the same name closer than this are one station


def km_between(a: tuple[float, float], b: tuple[float, float]) -> float:
    """Rough distance in km between two (latitude, longitude) points: plenty for telling towns apart."""
    north = (a[0] - b[0]) * 111.2
    east = (a[1] - b[1]) * 111.2 * math.cos(math.radians((a[0] + b[0]) / 2))
    return math.hypot(north, east)


def tell_apart(runs: list[Run]) -> list[Run]:
    """Give same-named stations in different places different names.

    Stations are matched by name, but some names are used for places far apart (e.g. "Bruges"
    is Brugge in SNCB's feed and a town near Bordeaux in SNCF's). For a name used more than
    SAME_PLACE_KM apart, each place gets its position added to the name, e.g.
    "Bruges (44.89, -0.61)", except the place at one of our cities, which keeps its plain name."""
    ours = {simplify(name): POSITIONS[city] for city, names in STATIONS.items() for name in names}

    # Group every stop position by name, then into places: positions within SAME_PLACE_KM
    # of a place's first position belong to that place.
    places = defaultdict(list)  # simplified name -> [first position of each place]
    place_of = {}  # (simplified name, position) -> index of its place
    for run in runs:
        for stop in run.stops:
            key, here = simplify(stop.station), (stop.lat, stop.lon)
            if (key, here) in place_of:
                continue
            found = next((i for i, first in enumerate(places[key]) if km_between(first, here) < SAME_PLACE_KM), None)
            if found is None:
                places[key].append(here)
                found = len(places[key]) - 1
            place_of[(key, here)] = found

    def label(stop) -> str:
        key = simplify(stop.station)
        first = places[key][place_of[(key, (stop.lat, stop.lon))]]
        if key in ours:  # one of our cities' names: only the place at that city keeps it
            near = km_between(first, ours[key]) < SAME_PLACE_KM
        else:  # any other name: kept unless it is used for more than one place
            near = len(places[key]) == 1
        return stop.station if near else f"{stop.station} ({first[0]:.2f}, {first[1]:.2f})"

    labelled = []
    for run in runs:
        stops = tuple(replace(stop, station=label(stop)) for stop in run.stops)
        labelled.append(run if stops == run.stops else replace(run, stops=stops))
    return labelled
