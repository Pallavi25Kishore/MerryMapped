from datetime import date

from app.planning.trains import Train, pick_train

DAY = date(2026, 12, 19)


def leg(start, end, depart, arrive):
    return {"from": start, "to": end, "depart": depart, "arrive": arrive, "feed": "f",
            "estimate": False, "estimate_from": None}


LINKS = {
    ("A", "B", DAY): [
        [leg("A", "B", 420, 480)],  # 07:00, too early
        [leg("A", "B", 500, 600)],  # 08:20 -> 10:00
        [leg("A", "B", 530, 590)],  # 08:50 -> 09:50: arrives first
        [leg("A", "B", 900, 1300)],  # takes 6 h 40
    ],
    ("A", "M", DAY): [[leg("A", "M", 500, 560)]],  # -> 09:20 at M
    ("M", "C", DAY): [[leg("M", "C", 565, 600)],  # change too short (5 min)
                      [leg("M", "C", 580, 640)]],  # 20 min change -> 10:40
}


def test_picks_the_train_that_arrives_first_among_those_allowed():
    train = pick_train(LINKS, "A", "B", DAY, not_before=480, max_minutes=360)
    assert (train.depart, train.arrive, train.via) == (530, 590, None)


def test_respects_the_earliest_time_and_the_travel_limit():
    train = pick_train(LINKS, "A", "B", DAY, not_before=600, max_minutes=360)
    assert isinstance(train, str) and "leaves after 10:00" in train


def test_joins_two_journeys_through_a_middle_city():
    train = pick_train(LINKS, "A", "C", DAY, not_before=480, max_minutes=360)
    assert isinstance(train, Train)
    assert (train.via, train.depart, train.arrive) == ("M", 500, 640)
    assert [l["to"] for l in train.legs] == ["M", "C"]


def test_says_why_when_nothing_works():
    assert pick_train(LINKS, "B", "A", DAY, 480, 360) == (
        "no train from B to A on 19 Dec leaves after 08:00 and takes at most 6 h 00 min")


def test_other_days_are_not_used():
    assert isinstance(pick_train(LINKS, "A", "B", date(2026, 12, 20), 480, 360), str)
