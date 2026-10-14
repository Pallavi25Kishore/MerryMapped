from dataclasses import dataclass, replace
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
from app.trains.places import tell_apart
from app.trains.reader import Run, read_feed
from app.trains.stations import STATIONS

# The days of the trip.
TRIP_DAYS = [date(2026, 12, 15) + timedelta(days=n) for n in range(17)]  # 15-31 December


def coverage(feed_name: str, gtfs_dir: Path = GTFS_DIR) -> tuple[date, date]:
    """The first and last day the downloaded feed covers."""
    days = date_range(gtfs_dir / feed_name)
    if days is None:
        raise SystemExit(f"No timetable for {feed_name}: run python -m app.trains.download first.")
    first, last = (datetime.strptime(day, "%Y%m%d").date() for day in days)
    return first, last


def day_to_read(day: date, covered: tuple[date, date]) -> tuple[date, str]:
    """Which day of a feed to use: the day itself ("timetable") if the feed covers it, otherwise
    the latest covered day with the same weekday ("estimate")."""
    first, last = covered
    if first <= day <= last:
        return day, "timetable"
    same_weekday = last - timedelta(days=(last.weekday() - day.weekday()) % 7)
    if same_weekday < first:
        raise SystemExit(f"The timetables cover no {day:%A}: cannot estimate {day}.")
    return same_weekday, "estimate"


@dataclass
class DayRuns:
    """All trains for one trip day. Feeds that don't cover the day lend the trains of their
    latest same weekday, relabelled to the trip day so they connect with the real ones."""
    runs: list[Run]
    lent_from: dict[str, date]  # feed name -> the day its lent trains come from


def read_day(day: date, gtfs_dir: Path = GTFS_DIR) -> DayRuns:
    runs, lent_from = [], {}
    for feed in FEEDS:
        use_day, source = day_to_read(day, coverage(feed.name, gtfs_dir))
        feed_runs = read_feed(gtfs_dir / feed.name, {use_day})
        if source == "estimate":
            lent_from[feed.name] = use_day
            feed_runs = [replace(run, day=day) for run in feed_runs]
        runs += feed_runs
    return DayRuns(tell_apart(runs), lent_from)


def as_json(journey: Journey, lent_from: dict[str, date]) -> list[dict]:
    return [{"from": leg.from_station, "to": leg.to_station, "depart": leg.depart,
             "arrive": leg.arrive, "feed": leg.feed, "estimate": leg.feed in lent_from,
             "estimate_from": lent_from[leg.feed].isoformat() if leg.feed in lent_from else None}
            for leg in journey.legs]


def link_row(from_city: str, to_city: str, day: date, found: list[Journey],
             lent_from: dict[str, date], today: date) -> TrainLink:
    """One train_links row: the journeys found and a short summary of them. The row is an
    estimate if any of its journeys uses a lent train, or if none was found while some
    trains were lent (then "no journey" is only an estimate too). based_on_day is the
    earliest day the lent trains it uses come from."""
    used = {lent_from[leg.feed] for journey in found for leg in journey.legs if leg.feed in lent_from}
    if not found:
        used = set(lent_from.values())
    return TrainLink(
        from_city=from_city,
        to_city=to_city,
        day=day,
        journeys=[as_json(journey, lent_from) for journey in found],
        fastest_minutes=min((j.arrive - j.depart for j in found), default=None),
        fewest_changes=min((j.changes for j in found), default=None),
        trips_per_day=len(found),
        first_departure=min((j.depart for j in found), default=None),
        last_departure=max((j.depart for j in found), default=None),
        source="estimate" if used else "timetable",
        based_on_day=min(used, default=None),
        checked_on=today,
    )


def replace_links(session: Session, day: date, rows: list[TrainLink]) -> None:
    """Replace the day's rows worked out from timetables. Hand-entered rows are kept.
    The caller commits."""
    session.execute(delete(TrainLink).where(TrainLink.day == day,
                                            TrainLink.source != "entered by hand"),
                    execution_options={"synchronize_session": "fetch"})
    session.add_all(rows)


def main() -> None:
    for feed in FEEDS:
        first, last = coverage(feed.name)
        print(f"{feed.name} covers {first} to {last}.")
    engine = make_engine()
    create_tables(engine)
    today = date.today()
    for day in TRIP_DAYS:
        trains = read_day(day)
        rows = [link_row(from_city, to_city, day,
                         journeys(trains.runs, set(STATIONS[from_city]), set(STATIONS[to_city])),
                         trains.lent_from, today)
                for from_city, to_city in permutations(STATIONS, 2)]
        # Read the rows before saving: once committed, their values are expired.
        estimates = sum(row.source == "estimate" for row in rows)
        none = [f"{row.from_city} -> {row.to_city}" for row in rows if row.trips_per_day == 0]
        with Session(engine) as session:
            replace_links(session, day, rows)
            session.commit()
        lent = ", ".join(f"{feed} from {lent_day:%a %d %b}" for feed, lent_day in sorted(trains.lent_from.items()))
        lent = f" (lent: {lent})" if lent else ""
        print(f"{day:%a %d %b}: {len(rows)} pairs saved, {estimates} estimates{lent}, "
              f"no journey: {', '.join(none) or 'none'}")


if __name__ == "__main__":
    main()
