from datetime import date

import pytest

from app.reading.fact_checks import (
    check_facts,
    drop_contradictions,
    fact_problem,
    quote_states_date,
    quote_states_time,
)

PAGE = """Weihnachtsmarkt 2026
Auf dem Roncalliplatz
vor dem Kölner Dom
Über 140 festlich geschmückte Stände mit Kunsthandwerk und Geschenken, aber auch mit Gastronomie und jeder Menge sozialem Engagement.
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
    midnight = "Freitags 11 Uhr bis Mitternacht."
    late = fact("hours", {"days": ["fri"], "opens": "11:00", "closes": "24:00"}, quote=midnight, year_quote=None)
    assert fact_problem(late, PAGE + "\n" + midnight) is None


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
        (fact(value={"date": "2025-11-17"}, quote="Weihnachtsmarkt 2025: 17.11. bis 23.12.",
              year_quote="Weihnachtsmarkt 2025"),
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


def stated(day):
    """A quote that states the day, e.g. 'Termin: 16.11.2026' for 2026-11-16."""
    year, month, dom = day.split("-")
    return f"Termin: {int(dom)}.{int(month)}.{year}"


def opening(day):
    return fact("opening_date", {"date": day}, quote=stated(day), year_quote=stated(day))


def closing(day):
    return fact("closing_date", {"date": day}, quote=stated(day), year_quote=stated(day))


def page_with(*facts):
    return PAGE + "\n" + "\n".join(f["evidence_quote"] for f in facts)


def test_good_facts_are_kept_and_bad_ones_dropped_with_the_reason():
    invented = fact(quote="Der Markt öffnet am 16.11.")
    facts = [opening("2026-11-16"), closing("2027-01-06"), hours(), invented]
    kept, dropped = check_facts(facts, page_with(*facts[:2]))

    assert kept == [opening("2026-11-16"), closing("2027-01-06"), hours()]
    assert dropped == [(invented, "evidence quote not found on the page")]


def test_different_opening_dates_are_all_dropped():
    facts = [opening("2026-11-16"), opening("2026-11-17"), hours()]
    kept, dropped = check_facts(facts, page_with(*facts[:2]))

    assert kept == [hours()]
    assert [reason for _, reason in dropped] == ["different opening_dates were given"] * 2


def test_the_same_date_stated_twice_is_kept():
    kept, dropped = check_facts([opening("2026-11-16"), opening("2026-11-16")], page_with(opening("2026-11-16")))

    assert len(kept) == 2
    assert dropped == []


def test_opening_after_closing_drops_both():
    facts = [opening("2026-12-20"), closing("2026-11-20")]
    kept, dropped = check_facts(facts, page_with(*facts))

    assert kept == []
    assert [reason for _, reason in dropped] == ["opening date is after closing date"] * 2


def test_a_one_day_market_is_kept():
    facts = [opening("2026-12-05"), closing("2026-12-05")]
    kept, _ = check_facts(facts, page_with(*facts))

    assert len(kept) == 2


def test_hours_clashing_on_the_same_day_are_dropped():
    mon_thu = hours(days=["mon", "tue", "wed", "thu"])
    mon_fri = hours(days=["mon", "tue", "wed", "thu", "fri"], opens="12:00", closes="20:00")
    kept, dropped = drop_contradictions([mon_thu, mon_fri])

    assert kept == []
    assert [reason for _, reason in dropped] == ["different hours were given for the same days"] * 2


def test_the_same_hours_stated_twice_are_kept():
    kept, dropped = drop_contradictions([hours(), hours()])

    assert len(kept) == 2
    assert dropped == []


def test_different_hours_in_separate_periods_are_kept():
    before = hours(until="2026-12-23")
    after = hours(opens="12:00", closes="18:00", **{"from": "2026-12-26"})
    kept, dropped = drop_contradictions([before, after])

    assert kept == [before, after]
    assert dropped == []


def test_different_days_with_different_hours_are_kept():
    weekdays = hours(days=["mon", "tue", "wed", "thu"])
    weekend = hours(days=["fri", "sat"], closes="23:00")
    kept, _ = drop_contradictions([weekdays, weekend])

    assert kept == [weekdays, weekend]


def test_a_closed_day_inside_the_season_is_not_a_contradiction():
    facts = [opening("2026-12-15"), closing("2026-12-25"), fact("closed_on", {"date": "2026-12-24"})]
    kept, dropped = drop_contradictions(facts)

    assert kept == facts
    assert dropped == []


def test_closed_and_special_hours_on_the_same_date_are_dropped():
    closed = fact("closed_on", {"date": "2026-12-24"})
    short_day = fact("special_hours", {"date": "2026-12-24", "opens": "11:00", "closes": "14:00"})
    christmas = fact("closed_on", {"date": "2026-12-25"})
    kept, dropped = drop_contradictions([closed, short_day, christmas])

    assert kept == [christmas]
    assert [reason for _, reason in dropped] == ["different hours were given for 2026-12-24"] * 2


def test_the_same_closed_day_stated_twice_is_kept():
    closed = fact("closed_on", {"date": "2026-12-24"})
    kept, dropped = drop_contradictions([closed, closed])

    assert len(kept) == 2
    assert dropped == []


def address(text):
    return fact("address", {"text": text}, quote="Auf dem Roncalliplatz", year_quote=None)


def test_an_address_spread_over_two_lines_passes():
    assert fact_problem(address("Roncalliplatz vor dem Kölner Dom"), PAGE) is None


def test_an_address_not_on_the_page_is_caught():
    assert fact_problem(address("Roncalliplatz 1, 50667 Köln"), PAGE) == (
        "address is not written on the page as given"
    )


STALLS = "Über 140 festlich geschmückte Stände"


def detail(text, quote=STALLS):
    return fact("detail", {"text": text}, quote=quote, year_quote=None)


def test_good_details_and_tags_pass():
    assert fact_problem(detail("over 140 stalls"), PAGE) is None
    assert fact_problem(fact("tag", {"tag": "artisan"}, quote="Kunsthandwerk", year_quote=None), PAGE) is None


def test_a_whole_descriptive_sentence_is_too_long_as_proof():
    sentence = next(line for line in PAGE.splitlines() if line.startswith(STALLS))
    assert fact_problem(detail("over 140 stalls", quote=sentence), PAGE) == (
        "evidence quote for a detail is longer than 100 characters"
    )


def test_a_long_detail_is_caught():
    assert fact_problem(detail("over 140 festively decorated stalls " * 3), PAGE) == (
        "detail is longer than 80 characters"
    )


def test_a_tag_needs_the_tag_field():
    assert fact_problem(fact("tag", {"text": "artisan"}, quote="Kunsthandwerk", year_quote=None), PAGE) == (
        "tag needs ['tag'], got ['text']"
    )


@pytest.mark.parametrize(
    ("quote", "day"),
    [("Mo 16.11.2026", "2026-11-16"), ("vom 16. bis 23. Dezember 2026", "2026-12-16"),
     ("27. November bis 24. Dezember 2026", "2026-12-24"), ("le 5 décembre 2026", "2026-12-05")],
)
def test_common_ways_of_writing_a_date_pass(quote, day):
    assert quote_states_date(quote, date.fromisoformat(day))


@pytest.mark.parametrize(
    ("quote", "hhmm"),
    [("So-Mi 11-21 Uhr", "21:00"), ("11h00–21h00", "21:00"), ("11 a.m. to 9 p.m.", "21:00"),
     ("bis Mitternacht", "24:00"), ("10.30 bis 20 Uhr", "10:30")],
)
def test_common_ways_of_writing_a_time_pass(quote, hhmm):
    assert quote_states_time(quote, hhmm)


def test_a_date_the_quote_does_not_state_is_caught():
    page = PAGE + "\nMo 16.11.2026\nAm Totensonntag geschlossen."
    wrong_day = fact(value={"date": "2026-11-17"}, quote="Mo 16.11.2026", year_quote="Mo 16.11.2026")
    worked_out = fact("closed_on", {"date": "2026-11-22"}, quote="Am Totensonntag geschlossen.")

    assert fact_problem(wrong_day, page) == "the quote does not state 2026-11-17"
    assert fact_problem(worked_out, page) == "the quote does not state 2026-11-22"


def test_hours_the_quote_does_not_state_are_caught():
    assert fact_problem(hours(closes="21:00"), PAGE) == "the quote does not state 11:00–21:00"
