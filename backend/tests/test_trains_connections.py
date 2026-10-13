from datetime import date

from app.trains.connections import Journey, Leg, direct_trains, journeys, keep_best
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


def route(journey):
    return [(leg.trip_id, leg.from_station, leg.to_station) for leg in journey.legs]


def test_one_change_at_a_station_we_never_listed():
    runs = [run("t1", stop("A", 480), stop("X", 540)), run("t2", stop("X", 560), stop("B", 600))]
    [journey] = journeys(runs, {"A"}, {"B"})
    assert route(journey) == [("t1", "A", "X"), ("t2", "X", "B")]
    assert journey.changes == 1


def test_change_needs_10_to_90_minutes():
    def found(wait):
        runs = [run("t1", stop("A", 480), stop("X", 540)), run("t2", stop("X", 540 + wait), stop("B", 700))]
        return journeys(runs, {"A"}, {"B"}) != []
    assert not found(9)
    assert found(10)
    assert found(90)
    assert not found(91)


def test_takes_the_train_that_arrives_first_not_the_one_that_leaves_first():
    runs = [
        run("t1", stop("A", 480), stop("X", 540)),
        run("slow", stop("X", 555), stop("B", 700)),
        run("fast", stop("X", 565), stop("B", 620)),
    ]
    [journey] = journeys(runs, {"A"}, {"B"})
    assert journey.legs[1].trip_id == "fast"


def test_two_changes_through_a_train_that_stops_at_neither_city():
    runs = [
        run("t1", stop("A", 480), stop("X", 520)),
        run("middle", stop("X", 535), stop("Y", 580)),
        run("t3", stop("Y", 595), stop("B", 610)),
    ]
    [journey] = journeys(runs, {"A"}, {"B"})
    assert route(journey) == [("t1", "A", "X"), ("middle", "X", "Y"), ("t3", "Y", "B")]


def test_staying_on_the_same_train_is_not_a_change():
    runs = [run("t1", stop("A", 480), stop("X", 540), stop("B", 600))]
    assert [j.changes for j in journeys(runs, {"A"}, {"B"})] == [0]


def leg(trip_id, depart, arrive):
    return Leg("feed_a", trip_id, DAY, "A", "B", depart, arrive)


def test_keep_best_drops_a_journey_that_leaves_earlier_and_arrives_later():
    early_slow = Journey((leg("early_slow", 480, 700),))
    later_fast = Journey((leg("later_fast", 500, 600),))
    assert keep_best([early_slow, later_fast]) == [later_fast]


def test_keep_best_keeps_fewer_changes_when_at_most_30_minutes_slower():
    direct = Journey((leg("direct", 480, 625),))
    changing = Journey((leg("c1", 480, 540), leg("c2", 550, 600)))
    assert sorted(keep_best([direct, changing]), key=lambda j: j.changes) == [direct, changing]


def test_keep_best_drops_fewer_changes_when_more_than_30_minutes_slower():
    direct = Journey((leg("direct", 480, 631),))
    changing = Journey((leg("c1", 480, 540), leg("c2", 550, 600)))
    assert keep_best([direct, changing]) == [changing]
