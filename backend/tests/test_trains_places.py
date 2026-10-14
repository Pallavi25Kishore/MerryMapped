from datetime import date

from app.trains.connections import journeys
from app.trains.places import tell_apart
from app.trains.reader import Run, Stop

DAY = date(2026, 12, 19)
BRUSSELS = (50.836, 4.336)
BRUGGE = (51.197, 3.217)
NEAR_BORDEAUX = (44.887, -0.609)


def stop(station, time, position):
    return Stop(station, time, time, True, True, *position)


def run(trip_id, *stops, feed="feed_a"):
    return Run(feed, trip_id, DAY, tuple(stops))


def names(runs):
    return [[stop.station for stop in r.stops] for r in runs]


def test_only_the_bruges_at_brugge_keeps_its_name():
    runs = tell_apart([
        run("be", stop("Bruxelles-Midi", 480, BRUSSELS), stop("Bruges", 540, BRUGGE), feed="sncb"),
        run("fr", stop("Bordeaux", 480, (44.826, -0.556)), stop("Bruges", 495, NEAR_BORDEAUX), feed="sncf"),
    ])
    assert names(runs) == [["Bruxelles-Midi", "Bruges"], ["Bordeaux", "Bruges (44.89, -0.61)"]]


def test_a_lone_bruges_far_from_brugge_is_still_renamed():
    runs = tell_apart([run("fr", stop("Bordeaux", 480, (44.826, -0.556)), stop("Bruges", 495, NEAR_BORDEAUX))])
    assert names(runs)[0][1] == "Bruges (44.89, -0.61)"


def test_other_names_used_for_two_places_are_both_renamed():
    runs = tell_apart([
        run("de", stop("Melle", 480, (52.20, 8.34))),
        run("be", stop("Melle", 480, (51.00, 3.80))),
    ])
    assert names(runs) == [["Melle (52.20, 8.34)"], ["Melle (51.00, 3.80)"]]


def test_the_same_station_in_two_feeds_is_left_alone():
    runs = [
        run("a", stop("Karlsruhe Hbf", 480, (48.9935, 8.4019)), feed="germany_long_distance"),
        run("b", stop("Karlsruhe Hbf", 500, (48.9933, 8.4010)), feed="sncf"),
    ]
    assert tell_apart(runs) == runs


def test_a_train_to_the_other_bruges_is_not_a_trip_to_brugge():
    runs = tell_apart([
        run("fake", stop("Bruxelles-Midi", 480, BRUSSELS), stop("Bruges", 600, NEAR_BORDEAUX)),
        run("real", stop("Bruxelles-Midi", 500, BRUSSELS), stop("Bruges", 560, BRUGGE)),
    ])
    found = journeys(runs, {"Bruxelles-Midi"}, {"Brugge", "Bruges"})
    assert [j.legs[0].trip_id for j in found] == ["real"]
