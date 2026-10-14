import json
from datetime import date
from types import SimpleNamespace

from app.planning.plan import Settings
from app.planning.understand import OUTSIDE_DATES, Form, merge, understand


def read(**values):
    """What the AI read from the text: nothing, apart from the given values."""
    empty = {"first_day": None, "last_day": None, "start_city": None, "end_city": None,
             "earliest_train": None, "min_market_minutes": None, "max_travel_minutes": None,
             "max_markets_per_day": None, "day_trips": None, "tags": [], "wishes": [], "not_covered": []}
    return {**empty, **values}


def test_the_text_fills_empty_fields():
    understood = merge(Form(), read(first_day="2026-12-15", last_day="2026-12-20", start_city="Köln",
                                    earliest_train="10:00", day_trips=True, tags=["medieval"],
                                    wishes=["mulled wine", "not too touristy"]))
    request = understood.request
    assert (request.first_day, request.last_day, request.start_city) == (date(2026, 12, 15), date(2026, 12, 20), "Köln")
    assert request.settings == Settings(earliest_train=600, day_trips=True)
    assert (request.tags, request.wishes) == (("medieval",), "mulled wine; not too touristy")
    assert understood.notes == []


def test_filled_in_form_fields_win_and_the_difference_is_noted():
    form = Form(first_day=date(2026, 12, 16), last_day=date(2026, 12, 20), settings={"max_markets_per_day": 1})
    understood = merge(form, read(first_day="2026-12-15", last_day="2026-12-20", max_markets_per_day=2))
    assert understood.request.first_day == date(2026, 12, 16)
    assert understood.request.settings.max_markets_per_day == 1
    assert understood.notes == [
        "You mentioned Tue 15 Dec as your first day, and the calendar says Wed 16 Dec. "
        "We've gone with the calendar, and you can change it there anytime.",
        "You mentioned 2 markets a day, and Your pace says 1. "
        "We've gone with Your pace, and you can change it there anytime."]


def test_only_15_to_31_december():
    understood = merge(Form(), read(first_day="2026-12-10", last_day="2026-12-14"))
    assert understood.request is None
    assert understood.notes == [OUTSIDE_DATES]
    assert OUTSIDE_DATES == ("MerryMapped plans trips between 15 and 31 December, the most magical stretch of "
                             "the season. Please pick dates in that window.")


def test_missing_dates_are_asked_for():
    understood = merge(Form(), read(wishes=["castles"]))
    assert understood.request is None
    assert understood.notes == ["Please pick your dates on the calendar: any days from 15 to 31 December work "
                                "beautifully."]


def test_a_setting_we_cannot_plan_is_kept_at_the_default_kindly():
    understood = merge(Form(first_day=date(2026, 12, 15), last_day=date(2026, 12, 16)), read(earliest_train="03:00"))
    assert understood.request.settings.earliest_train == Settings().earliest_train
    assert understood.notes == ["We can plan trains leaving between 05:00 and 14:00, so we've kept your earliest "
                                "train at 08:00."]


def test_notes_describe_times_and_places_in_plain_words():
    form = Form(first_day=date(2026, 12, 15), last_day=date(2026, 12, 16), start_city="Köln",
                settings={"min_market_minutes": 120})
    understood = merge(form, read(start_city="Aachen", min_market_minutes=90, end_city=None))
    assert understood.notes == [
        "You mentioned starting in Aachen, and the map says Köln. "
        "We've gone with the map, and you can change it there anytime.",
        "You mentioned 1 h 30 min at each market, and Your pace says 2 h. "
        "We've gone with Your pace, and you can change it there anytime."]


def test_what_we_cannot_do_is_passed_on():
    understood = merge(Form(first_day=date(2026, 12, 15), last_day=date(2026, 12, 16)),
                       read(not_covered=["Vienna is not one of our cities"]))
    assert understood.not_covered == ["Vienna is not one of our cities"]


class PretendClaude:
    def __init__(self, answer):
        self.answer, self.requests, self.messages = answer, [], self

    def create(self, **request):
        self.requests.append(request)
        return SimpleNamespace(content=[SimpleNamespace(type="text", text=json.dumps(self.answer))])


def test_understand_sends_the_text_with_our_cities_and_tags():
    claude = PretendClaude(read(first_day="2026-12-15", last_day="2026-12-17"))
    understood = understand(Form(text="Three days from the 15th"), client=claude)
    assert understood.request.last_day == date(2026, 12, 17)
    message = claude.requests[0]["messages"][0]["content"]
    assert "<traveller_text>\nThree days from the 15th\n</traveller_text>" in message
    assert "Brugge" in message and "medieval:" in message


def test_no_text_means_no_ai_call():
    understood = understand(Form(first_day=date(2026, 12, 15), last_day=date(2026, 12, 16)), client=None)
    assert understood.request is not None
