from datetime import date

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.connection import make_engine
from app.db.models import TrainLink, create_tables
from app.trains.build_links import day_to_read, link_row, replace_links
from app.trains.connections import Journey, Leg

COVERED = (date(2026, 10, 10), date(2026, 11, 9))  # a Saturday to a Monday
TODAY = date(2026, 10, 13)


def test_a_covered_day_uses_its_own_timetable():
    assert day_to_read(date(2026, 10, 24), COVERED) == (date(2026, 10, 24), "timetable")


def test_an_uncovered_day_is_estimated_from_the_latest_same_weekday():
    # Sat 19 Dec -> the last covered Saturday, 7 Nov; Mon 21 Dec -> Mon 9 Nov (the last day itself).
    assert day_to_read(date(2026, 12, 19), COVERED) == (date(2026, 11, 7), "estimate")
    assert day_to_read(date(2026, 12, 21), COVERED) == (date(2026, 11, 9), "estimate")


def test_no_same_weekday_covered_stops():
    with pytest.raises(SystemExit):
        day_to_read(date(2026, 12, 16), (date(2026, 11, 9), date(2026, 11, 10)))  # Mon-Tue only


def leg(trip_id, depart, arrive, start="A", end="B"):
    return Leg("feed_a", trip_id, date(2026, 11, 7), start, end, depart, arrive)


def test_link_row_sums_up_the_journeys():
    direct = Journey((leg("d", 600, 800),))
    changing = Journey((leg("c1", 480, 540, end="X"), leg("c2", 555, 650, start="X")))
    row = link_row("Köln", "Strasbourg", date(2026, 12, 19), [changing, direct], "estimate",
                   date(2026, 11, 7), TODAY)
    assert (row.trips_per_day, row.fastest_minutes, row.fewest_changes) == (2, 170, 0)
    assert (row.first_departure, row.last_departure) == (480, 600)
    assert row.based_on_day == date(2026, 11, 7)
    assert row.journeys[0][1] == {"from": "X", "to": "B", "depart": 555, "arrive": 650, "feed": "feed_a"}


def test_link_row_with_no_journey():
    row = link_row("A", "B", date(2026, 12, 19), [], "timetable", date(2026, 12, 19), TODAY)
    assert (row.trips_per_day, row.fastest_minutes, row.first_departure, row.based_on_day) == (0, None, None, None)


def test_replace_links_keeps_hand_entered_rows():
    engine = make_engine("sqlite://")
    create_tables(engine)
    day = date(2026, 12, 19)
    hand = link_row("Brussels", "Brugge", day, [], "entered by hand", day, TODAY)
    old = link_row("Köln", "Aachen", day, [], "estimate", date(2026, 11, 7), TODAY)
    with Session(engine) as session:
        session.add_all([hand, old])
        session.commit()
        new = link_row("Köln", "Aachen", day, [Journey((leg("t", 480, 520),))], "timetable", day, TODAY)
        replace_links(session, day, [new])
        session.commit()
        rows = session.scalars(select(TrainLink).order_by(TrainLink.from_city)).all()
        assert [(r.from_city, r.source) for r in rows] == [("Brussels", "entered by hand"), ("Köln", "timetable")]
