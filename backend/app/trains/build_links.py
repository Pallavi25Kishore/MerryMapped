from datetime import date, datetime, timedelta
from itertools import permutations
from pathlib import Path

from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.db.connection import make_engine
from app.db.models import TrainLink, create_tables
from app.trains.connections import Journey, journeys
from app.trains.download import GTFS_DIR, date_range
from app.trains.feeds import FEEDS
from app.trains.reader import Run, read_feed
from app.trains.stations import STATIONS

# The days of the trip.
TRIP_DAYS = [date(2026, 12, 15) + timedelta(days=n) for n in range(17)]  # 15-31 December


def coverage(gtfs_dir: Path = GTFS_DIR) -> tuple[date, date]:
    """The days every downloaded feed covers: from the latest first day to the earliest last day."""
    ranges = []
    for feed in FEEDS:
        days = date_range(gtfs_dir / feed.name)
        if days is None:
            raise SystemExit(f"No timetable for {feed.name}: run python -m app.trains.download first.")
        ranges.append([datetime.strptime(day, "%Y%m%d").date() for day in days])
    return max(first for first, _ in ranges), min(last for _, last in ranges)


def day_to_read(day: date, covered: tuple[date, date]) -> tuple[date, str]:
    """Which day's timetable to use, and whether that is the real one ("timetable") or the latest
    covered day with the same weekday ("estimate")."""
    first, last = covered
    if first <= day <= last:
        return day, "timetable"
    same_weekday = last - timedelta(days=(last.weekday() - day.weekday()) % 7)
    if same_weekday < first:
        raise SystemExit(f"The timetables cover no {day:%A}: cannot estimate {day}.")
    return same_weekday, "estimate"


def as_json(journey: Journey) -> list[dict]:
    return [{"from": leg.from_station, "to": leg.to_station, "depart": leg.depart,
             "arrive": leg.arrive, "feed": leg.feed} for leg in journey.legs]


def link_row(from_city: str, to_city: str, day: date, found: list[Journey], source: str,
             read_day: date, today: date) -> TrainLink:
    """One train_links row: the journeys found and a short summary of them."""
    return TrainLink(
        from_city=from_city,
        to_city=to_city,
        day=day,
        journeys=[as_json(journey) for journey in found],
        fastest_minutes=min((j.arrive - j.depart for j in found), default=None),
        fewest_changes=min((j.changes for j in found), default=None),
        trips_per_day=len(found),
        first_departure=min((j.depart for j in found), default=None),
        last_departure=max((j.depart for j in found), default=None),
        source=source,
        based_on_day=read_day if source == "estimate" else None,
        checked_on=today,
    )


def replace_links(session: Session, day: date, rows: list[TrainLink]) -> None:
    """Replace the day's rows worked out from timetables. Hand-entered rows are kept.
    The caller commits."""
    session.execute(delete(TrainLink).where(TrainLink.day == day,
                                            TrainLink.source != "entered by hand"),
                    execution_options={"synchronize_session": "fetch"})
    session.add_all(rows)


def read_all_feeds(day: date, gtfs_dir: Path = GTFS_DIR) -> list[Run]:
    return [run for feed in FEEDS for run in read_feed(gtfs_dir / feed.name, {day})]


def main() -> None:
    covered = coverage()
    print(f"Every feed covers {covered[0]} to {covered[1]}.")
    engine = make_engine()
    create_tables(engine)
    today = date.today()
    found_for = {}  # (day read, from city, to city) -> journeys: estimates share a day read
    for day in TRIP_DAYS:
        read_day, source = day_to_read(day, covered)
        runs = None
        rows = []
        for from_city, to_city in permutations(STATIONS, 2):
            key = (read_day, from_city, to_city)
            if key not in found_for:
                runs = runs if runs is not None else read_all_feeds(read_day)
                found_for[key] = journeys(runs, set(STATIONS[from_city]), set(STATIONS[to_city]))
            rows.append(link_row(from_city, to_city, day, found_for[key], source, read_day, today))
        with Session(engine) as session:
            replace_links(session, day, rows)
            session.commit()
        none = [f"{row.from_city} -> {row.to_city}" for row in rows if row.trips_per_day == 0]
        based = f" from {read_day:%a %d %b}" if source == "estimate" else ""
        print(f"{day:%a %d %b}: {source}{based}, {len(rows)} pairs saved, no journey: {', '.join(none) or 'none'}")


if __name__ == "__main__":
    main()
