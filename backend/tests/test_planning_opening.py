from datetime import date

from app.planning.opening import open_window


def fact(kind, **value):
    return {"kind": kind, "value": value}


MARKET = [
    fact("opening_date", date="2026-11-20"),
    fact("closing_date", date="2026-12-24"),
    fact("hours", days=["mon", "tue", "wed", "thu", "fri"], opens="11:00", closes="21:00"),
    fact("hours", days=["sat", "sun"], opens="10:00", closes="22:00"),
    fact("hours", days=["sat"], opens="10:00", closes="23:00", **{"from": "2026-12-19", "until": "2026-12-19"}),
    fact("closed_on", date="2026-11-22"),
    fact("special_hours", date="2026-12-24", opens="11:00", closes="14:00"),
]


def test_normal_hours_for_the_weekday():
    assert open_window(MARKET, date(2026, 12, 15)) == (660, 1260)  # Tuesday, 11:00-21:00
    assert open_window(MARKET, date(2026, 12, 13)) == (600, 1320)  # Sunday, 10:00-22:00


def test_hours_for_a_date_range_win_over_season_hours():
    assert open_window(MARKET, date(2026, 12, 19)) == (600, 1380)  # that Saturday, until 23:00


def test_special_hours_win():
    assert open_window(MARKET, date(2026, 12, 24)) == (660, 840)  # 11:00-14:00


def test_closed_day():
    assert open_window(MARKET, date(2026, 11, 22)) == "it is closed on 22 Nov"


def test_outside_the_season():
    assert open_window(MARKET, date(2026, 12, 26)) == "it is only open from 20 Nov to 24 Dec"


def test_no_hours_for_that_weekday():
    weekdays_only = [f for f in MARKET if f["value"].get("days") != ["sat", "sun"] and "from" not in f["value"]]
    assert open_window(weekdays_only, date(2026, 12, 13)) == "no opening hours are known for Sundays"


def test_unknown_season():
    assert open_window(MARKET[2:], date(2026, 12, 15)) == "its season dates are not known"


def test_closing_after_midnight_is_the_next_morning():
    late = [fact("opening_date", date="2026-12-01"), fact("closing_date", date="2026-12-31"),
            fact("hours", days=["fri"], opens="18:00", closes="01:00")]
    assert open_window(late, date(2026, 12, 18)) == (1080, 1500)  # 18:00 to 01:00 next day
