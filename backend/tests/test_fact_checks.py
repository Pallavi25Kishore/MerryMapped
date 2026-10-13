import pytest

from app.reading.fact_checks import check_facts, fact_problem

PAGE = """Weihnachtsmarkt 2026
Der Markt ist vom 16.11. bis 6.1. geöffnet.
Öffnungszeiten: täglich 11 bis 22 Uhr.
Weihnachtsmarkt 2025: 17.11. bis 23.12."""

DATES = "Der Markt ist vom 16.11. bis 6.1. geöffnet."
HOURS = "Öffnungszeiten: täglich 11 bis 22 Uhr."
ALL_DAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]


def fact(kind="opening_date", value=None, quote=DATES, year_quote="Weihnachtsmarkt 2026"):
    return {
        "kind": kind,
        "value": {"date": "2026-11-16"} if value is None else value,
        "evidence_quote": quote,
        "evidence_translation": None,
        "year_quote": year_quote,
    }


def hours(**value):
    return fact("hours", {"days": ALL_DAYS, "opens": "11:00", "closes": "22:00", **value},
                quote=HOURS, year_quote=None)


def test_good_facts_pass():
    assert fact_problem(fact(), PAGE) is None
    assert fact_problem(hours(), PAGE) is None
    assert fact_problem(hours(closes="24:00"), PAGE) is None


def test_january_date_may_take_the_season_year():
    assert fact_problem(fact("closing_date", {"date": "2027-01-06"}), PAGE) is None


@pytest.mark.parametrize(
    ("bad_fact", "problem"),
    [
        (fact(quote="Der Markt öffnet am 16.11."), "evidence quote not found on the page"),
        (fact(quote="  "), "evidence quote not found on the page"),
        (fact("hours", {"opens": "11:00", "closes": "22:00"}, quote=HOURS, year_quote=None),
         "hours needs ['closes', 'days', 'opens'], got ['closes', 'opens']"),
        (fact(value={"date": "2026-11-16", "text": "Roncalliplatz"}),
         "opening_date needs ['date'], got ['date', 'text']"),
        (hours(days=[]), "a value field is empty"),
        (fact(value={"date": "2026-11-31"}), "date '2026-11-31' is not a real date"),
        (hours(closes="25:00"), "times must be HH:MM"),
        (hours(opens="22:00", closes="11:00"), "opening time is not before closing time"),
        (hours(**{"from": "2026-12-26", "until": "2026-12-01"}), "from is after until"),
        (fact(year_quote=None), "year is not stated on the page"),
        (fact(year_quote="Weihnachtsmarkt 2027"), "year is not stated on the page"),
        (fact(value={"date": "2025-11-17"}, year_quote="Weihnachtsmarkt 2025"),
         "date 2025-11-17 is outside the 2026 season"),
        (fact(value={"date": "2026-11-16"}, year_quote="Weihnachtsmarkt 2025"),
         "year quote does not state 2026"),
    ],
)
def test_bad_facts_are_caught(bad_fact, problem):
    assert fact_problem(bad_fact, PAGE) == problem


def test_long_quote_is_caught():
    long_line = "Öffnungszeiten: " + "täglich 11 bis 22 Uhr, " * 15
    assert fact_problem(hours() | {"evidence_quote": long_line}, PAGE + "\n" + long_line) == (
        "evidence quote is longer than 300 characters"
    )


def opening(day):
    return fact("opening_date", {"date": day})


def closing(day):
    return fact("closing_date", {"date": day})


def test_good_facts_are_kept_and_bad_ones_dropped_with_the_reason():
    invented = fact(quote="Der Markt öffnet am 16.11.")
    kept, dropped = check_facts([opening("2026-11-16"), closing("2027-01-06"), hours(), invented], PAGE)

    assert kept == [opening("2026-11-16"), closing("2027-01-06"), hours()]
    assert dropped == [(invented, "evidence quote not found on the page")]


def test_different_opening_dates_are_all_dropped():
    kept, dropped = check_facts([opening("2026-11-16"), opening("2026-11-17"), hours()], PAGE)

    assert kept == [hours()]
    assert [reason for _, reason in dropped] == ["the page gives different opening_dates"] * 2


def test_the_same_date_stated_twice_is_kept():
    kept, dropped = check_facts([opening("2026-11-16"), opening("2026-11-16")], PAGE)

    assert len(kept) == 2
    assert dropped == []


def test_opening_after_closing_drops_both():
    kept, dropped = check_facts([opening("2026-12-20"), closing("2026-11-20")], PAGE)

    assert kept == []
    assert [reason for _, reason in dropped] == ["opening date is after closing date"] * 2


def test_a_one_day_market_is_kept():
    kept, _ = check_facts([opening("2026-12-05"), closing("2026-12-05")], PAGE)

    assert len(kept) == 2
