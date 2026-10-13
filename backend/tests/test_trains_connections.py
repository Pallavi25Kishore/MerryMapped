from datetime import date

from app.trains.connections import direct_trains
from app.trains.reader import Run, Stop

DAY = date(2026, 12, 19)


def stop(station, time, board=True, alight=True):
    return Stop(station, time, time, board, alight)


def run(trip_id, *stops, feed="feed_a", day=DAY):
    return Run(feed, trip_id, day, tuple(stops))


def test_finds_trains_from_a_to_b_in_departure_order():
    runs = [
        run("late", stop("A", 600), stop("X", 630), stop("B", 660)),
        run("early", stop("A", 480), stop("B", 520)),
    ]
    legs = direct_trains(runs, {"A"}, {"B"})
    assert [(leg.trip_id, leg.depart, leg.arrive) for leg in legs] == [("early", 480, 520), ("late", 600, 660)]


def test_wrong_direction_is_not_a_train_from_a_to_b():
    assert direct_trains([run("t", stop("B", 480), stop("A", 520))], {"A"}, {"B"}) == []


def test_respects_boarding_and_getting_off_rules():
    runs = [
        run("no_boarding", stop("A", 480, board=False), stop("B", 520)),
        run("no_getting_off", stop("A", 480), stop("B", 520, alight=False)),
    ]
    assert direct_trains(runs, {"A"}, {"B"}) == []


def test_any_spelling_of_a_station_counts():
    runs = [run("t", stop("Bruxelles Midi", 480), stop("Köln Hbf", 590))]
    [leg] = direct_trains(runs, {"Bruxelles-Midi", "Bruxelles Midi"}, {"Köln Hbf"})
    assert leg.from_station == "Bruxelles Midi"


def test_same_train_in_two_feeds_is_kept_once():
    runs = [
        run("ice", stop("A", 480), stop("B", 590), feed="feed_a"),
        run("ice_copy", stop("A", 480), stop("B", 590), feed="feed_b"),
        run("other", stop("A", 480), stop("B", 600), feed="feed_b"),
    ]
    legs = direct_trains(runs, {"A"}, {"B"})
    assert [(leg.feed, leg.trip_id) for leg in legs] == [("feed_a", "ice"), ("feed_b", "other")]


def test_same_times_on_different_days_are_different_trains():
    runs = [
        run("t", stop("A", 480), stop("B", 520)),
        run("t", stop("A", 480), stop("B", 520), day=date(2026, 12, 20)),
    ]
    assert [leg.day for leg in direct_trains(runs, {"A"}, {"B"})] == [DAY, date(2026, 12, 20)]
