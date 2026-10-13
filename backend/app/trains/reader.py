import csv
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

WEEKDAY_COLUMNS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
NO = "1"  # pickup_type / drop_off_type 1: boarding or getting off is not allowed


@dataclass(frozen=True)
class Stop:
    station: str  # the stop's name in the feed
    arrive: int  # minutes after midnight of the day the train starts (can pass 24:00)
    depart: int
    can_board: bool
    can_alight: bool


@dataclass(frozen=True)
class Run:
    """One train on one day."""
    feed: str
    trip_id: str
    day: date  # the day the train starts
    stops: tuple[Stop, ...]


def rows(path: Path):
    with path.open(encoding="utf-8-sig", newline="") as file:
        yield from csv.DictReader(file)


def minutes(hhmmss: str) -> int:
    hours, mins, _ = hhmmss.split(":")
    return int(hours) * 60 + int(mins)


def is_train(route_type: str) -> bool:
    """GTFS route types that are trains: 2 (rail) and the extended railway types 100-199.
    Everything else (buses, trams, ferries) is skipped: MerryMapped is trains only."""
    code = int(route_type)
    return code == 2 or 100 <= code <= 199


def services_by_day(folder: Path, days: set[date]) -> dict[str, set[date]]:
    """For each service_id, the asked-for days it runs on (calendar.txt, then calendar_dates.txt)."""
    running = defaultdict(set)
    if (folder / "calendar.txt").exists():
        for row in rows(folder / "calendar.txt"):
            start = datetime.strptime(row["start_date"], "%Y%m%d").date()
            end = datetime.strptime(row["end_date"], "%Y%m%d").date()
            for day in days:
                if start <= day <= end and row[WEEKDAY_COLUMNS[day.weekday()]] == "1":
                    running[row["service_id"]].add(day)
    if (folder / "calendar_dates.txt").exists():
        for row in rows(folder / "calendar_dates.txt"):
            day = datetime.strptime(row["date"], "%Y%m%d").date()
            if day not in days:
                continue
            if row["exception_type"] == "1":
                running[row["service_id"]].add(day)
            else:
                running[row["service_id"]].discard(day)
    return running


def read_feed(folder: Path, days: set[date], stations: set[str]) -> list[Run]:
    """Every train run on the given days that stops at one of the given stations."""
    names = {row["stop_id"]: row["stop_name"] for row in rows(folder / "stops.txt")}
    train_routes = {row["route_id"] for row in rows(folder / "routes.txt") if is_train(row["route_type"])}
    running = services_by_day(folder, days)
    trip_days = {}
    for row in rows(folder / "trips.txt"):
        if row["route_id"] in train_routes and running.get(row["service_id"]):
            trip_days[row["trip_id"]] = running[row["service_id"]]

    stop_lists = defaultdict(list)
    for row in rows(folder / "stop_times.txt"):
        if row["trip_id"] not in trip_days:
            continue
        stop = Stop(
            station=names[row["stop_id"]],
            arrive=minutes(row["arrival_time"]),
            depart=minutes(row["departure_time"]),
            can_board=row.get("pickup_type") != NO,
            can_alight=row.get("drop_off_type") != NO,
        )
        stop_lists[row["trip_id"]].append((int(row["stop_sequence"]), stop))

    runs = []
    for trip_id, numbered in stop_lists.items():
        stops = tuple(stop for _, stop in sorted(numbered, key=lambda pair: pair[0]))
        if not any(stop.station in stations for stop in stops):
            continue
        for day in sorted(trip_days[trip_id]):
            runs.append(Run(folder.name, trip_id, day, stops))
    return runs
