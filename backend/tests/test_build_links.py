from datetime import date

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.connection import make_engine
from app.db.models import TrainLink, create_tables
from app.trains import build_links
from app.trains.build_links import day_to_read, link_row, read_day, replace_links
from app.trains.connections import Journey, Leg
from app.trains.feeds import Feed

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


def leg(trip_id, depart, arrive, start="A", end="B", feed="feed_a"):
    return Leg(feed, trip_id, date(2026, 12, 19), start, end, depart, arrive)


def test_link_row_sums_up_the_journeys():
    direct = Journey((leg("d", 600, 800),))
    changing = Journey((leg("c1", 480, 540, end="X"), leg("c2", 555, 650, start="X")))
    row = link_row("Köln", "Strasbourg", date(2026, 12, 19), [changing, direct], {}, TODAY)
    assert (row.trips_per_day, row.fastest_minutes, row.fewest_changes) == (2, 170, 0)
    assert (row.first_departure, row.last_departure) == (480, 600)
    assert (row.source, row.based_on_day) == ("timetable", None)
    assert row.journeys[0][1] == {"from": "X", "to": "B", "depart": 555, "arrive": 650,
                                  "feed": "feed_a", "estimate": False, "estimate_from": None}


def test_link_row_is_an_estimate_only_if_a_journey_uses_a_lent_train():
    journey = Journey((leg("t", 480, 520),))
    lent = link_row("A", "B", date(2026, 12, 19), [journey], {"feed_a": date(2026, 11, 7)}, TODAY)
    assert (lent.source, lent.based_on_day) == ("estimate", date(2026, 11, 7))
    assert lent.journeys[0][0]["estimate_from"] == "2026-11-07"
    real = link_row("A", "B", date(2026, 12, 19), [journey], {"other_feed": date(2026, 11, 7)}, TODAY)
    assert (real.source, real.based_on_day) == ("timetable", None)


def test_each_leg_keeps_its_own_lent_day_and_the_row_shows_the_earliest():
    journey = Journey((leg("be", 480, 540, end="X", feed="sncb"), leg("de", 555, 650, start="X", feed="german")))
    lent_from = {"sncb": date(2026, 12, 12), "german": date(2026, 11, 7)}
    row = link_row("Brugge", "Köln", date(2026, 12, 19), [journey], lent_from, TODAY)
    assert [l["estimate_from"] for l in row.journeys[0]] == ["2026-12-12", "2026-11-07"]
    assert row.based_on_day == date(2026, 11, 7)


def test_link_row_with_no_journey():
    row = link_row("A", "B", date(2026, 12, 19), [], {}, TODAY)
    assert (row.trips_per_day, row.fastest_minutes, row.first_departure) == (0, None, None)
    assert (row.source, row.based_on_day) == ("timetable", None)


def test_no_journey_is_an_estimate_when_trains_were_lent():
    row = link_row("A", "B", date(2026, 12, 19), [], {"feed_a": date(2026, 11, 7), "feed_b": date(2026, 12, 12)}, TODAY)
    assert (row.source, row.based_on_day) == ("estimate", date(2026, 11, 7))


def write_feed(folder, start, end):
    folder.mkdir(parents=True)
    files = {
        "stops.txt": "stop_id,stop_name,stop_lat,stop_lon\na,A,50.1,5.1\nb,B,50.2,5.2\n",
        "routes.txt": "route_id,route_type\nr,2\n",
        "calendar.txt": ("service_id,monday,tuesday,wednesday,thursday,friday,saturday,sunday,start_date,end_date\n"
                         f"s,1,1,1,1,1,1,1,{start},{end}\n"),
        "trips.txt": "route_id,service_id,trip_id\nr,s,t\n",
        "stop_times.txt": "trip_id,arrival_time,departure_time,stop_id,stop_sequence\nt,08:00:00,08:00:00,a,1\nt,09:00:00,09:00:00,b,2\n",
    }
    for name, text in files.items():
        (folder / name).write_text(text)


def test_read_day_uses_real_trains_where_it_can_and_lends_the_rest(tmp_path, monkeypatch):
    write_feed(tmp_path / "real", "20261013", "20270109")
    write_feed(tmp_path / "short", "20261010", "20261109")
    monkeypatch.setattr(build_links, "FEEDS", [Feed("real", "", "", ""), Feed("short", "", "", "")])
    trains = read_day(date(2026, 12, 19), tmp_path)
    assert trains.lent_from == {"short": date(2026, 11, 7)}
    # Lent trains are relabelled to the trip day, so they connect with the real ones.
    assert {(run.feed, run.day) for run in trains.runs} == {("real", date(2026, 12, 19)), ("short", date(2026, 12, 19))}


def test_replace_links_keeps_hand_entered_rows():
    engine = make_engine("sqlite://")
    create_tables(engine)
    day = date(2026, 12, 19)
    hand = link_row("Brussels", "Brugge", day, [], {}, TODAY)
    hand.source = "entered by hand"
    old = link_row("Köln", "Aachen", day, [], {}, TODAY)
    with Session(engine) as session:
        session.add_all([hand, old])
        session.commit()
        new = link_row("Köln", "Aachen", day, [Journey((leg("t", 480, 520),))], {}, TODAY)
        replace_links(session, day, [new])
        session.commit()
        rows = session.scalars(select(TrainLink).order_by(TrainLink.from_city)).all()
        assert [(r.from_city, r.trips_per_day) for r in rows] == [("Brussels", 0), ("Köln", 1)]
        assert rows[0].source == "entered by hand"
