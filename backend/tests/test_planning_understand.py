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
        "You typed 15 Dec for the first day, but the form says 16 Dec; the form is used.",
        "You typed 2 for the max markets per day, but the form says 1; the form is used."]


def test_only_15_to_31_december():
    understood = merge(Form(), read(first_day="2026-12-10", last_day="2026-12-14"))
    assert understood.request is None
    assert understood.notes == [OUTSIDE_DATES]
    assert OUTSIDE_DATES == ("MerryMapped is a December holiday planner: trips can only be planned "
                             "between 15 and 31 December.")


def test_missing_dates_are_asked_for():
    understood = merge(Form(), read(wishes=["castles"]))
    assert understood.request is None
    assert understood.notes == ["Please choose your dates, between 15 and 31 December."]


def test_a_setting_that_is_not_sensible_is_reset_to_the_default():
    understood = merge(Form(first_day=date(2026, 12, 15), last_day=date(2026, 12, 16)), read(earliest_train="03:00"))
    assert understood.request.settings.earliest_train == Settings().earliest_train
    assert understood.notes == ["earliest train of 03:00 is not sensible; the default is used."]


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
