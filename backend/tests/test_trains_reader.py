from datetime import date

from app.trains.reader import read_feed

# A tiny feed: one train A -> B -> C, one bus A -> C, and one train that never
# stops at a station we ask for.
FEED = {
    "stops.txt": "stop_id,stop_name\na,Alpha\nb,Beta\nc,Gamma\nx,Xi\ny,Ypsilon\n",
    "routes.txt": "route_id,route_type\ntrain,2\nfast,101\nbus,3\n",
    "calendar.txt": (
        "service_id,monday,tuesday,wednesday,thursday,friday,saturday,sunday,start_date,end_date\n"
        "weekdays,1,1,1,1,1,0,0,20261201,20261231\n"
    ),
    "calendar_dates.txt": "service_id,date,exception_type\nweekdays,20261225,2\nweekdays,20261219,1\n",
    "trips.txt": "route_id,service_id,trip_id\ntrain,weekdays,t1\nbus,weekdays,b1\nfast,weekdays,t2\n",
    "stop_times.txt": (
        "trip_id,arrival_time,departure_time,stop_id,stop_sequence,pickup_type,drop_off_type\n"
        "t1,23:50:00,23:55:00,b,2,0,0\n"  # listed out of order on purpose
        "t1,23:00:00,23:00:00,a,1,0,1\n"
        "t1,24:30:00,24:30:00,c,3,1,0\n"
        "b1,10:00:00,10:00:00,a,1,0,0\n"
        "b1,11:00:00,11:00:00,c,2,0,0\n"
        "t2,09:00:00,09:00:00,x,1,0,0\n"
        "t2,10:00:00,10:00:00,y,2,0,0\n"
    ),
}
STATIONS = {"Alpha", "Gamma"}


def make_feed(tmp_path):
    folder = tmp_path / "test_feed"
    folder.mkdir()
    for name, text in FEED.items():
        (folder / name).write_text(text)
    return folder


def test_keeps_trains_at_our_stations_and_skips_buses(tmp_path):
    runs = read_feed(make_feed(tmp_path), {date(2026, 12, 15)}, STATIONS)
    assert [(run.feed, run.trip_id, run.day) for run in runs] == [("test_feed", "t1", date(2026, 12, 15))]


def test_stops_are_in_order_with_times_past_midnight(tmp_path):
    [run] = read_feed(make_feed(tmp_path), {date(2026, 12, 15)}, STATIONS)
    assert [(stop.station, stop.arrive, stop.depart) for stop in run.stops] == [
        ("Alpha", 1380, 1380), ("Beta", 1430, 1435), ("Gamma", 1470, 1470)]


def test_boarding_and_getting_off_rules(tmp_path):
    [run] = read_feed(make_feed(tmp_path), {date(2026, 12, 15)}, STATIONS)
    alpha, beta, gamma = run.stops
    assert alpha.can_board and not alpha.can_alight
    assert beta.can_board and beta.can_alight
    assert not gamma.can_board and gamma.can_alight


def test_calendar_days_added_and_removed(tmp_path):
    days = {date(2026, 12, 19), date(2026, 12, 20), date(2026, 12, 24), date(2026, 12, 25)}
    runs = read_feed(make_feed(tmp_path), days, STATIONS)
    # 19th: a Saturday added by calendar_dates; 20th: Sunday; 24th: Thursday; 25th: removed.
    assert [run.day for run in runs] == [date(2026, 12, 19), date(2026, 12, 24)]
