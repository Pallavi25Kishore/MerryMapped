from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app, headers={"X-Access-Code": "pretend-code"})


def pretend_reader(monkeypatch, read):
    """Stand in for the AI request reader, recording what it was given."""
    seen = []
    empty = {"first_day": None, "last_day": None, "start_city": None, "end_city": None, "earliest_train": None,
             "min_market_minutes": None, "max_travel_minutes": None, "max_markets_per_day": None,
             "day_trips": None, "tags": [], "wishes": [], "not_covered": []}
    monkeypatch.setattr("app.planning.understand.read_text", lambda text, client=None: seen.append(text) or {**empty, **read})
    return seen


def test_form_and_text_become_the_confirm_screen(monkeypatch):
    seen = pretend_reader(monkeypatch, {"last_day": "2026-12-20", "earliest_train": "10:00",
                                        "tags": ["old-town"], "wishes": ["old towns", "mulled wine"],
                                        "not_covered": ["Vienna"]})
    response = client.post("/api/understand", json={
        "text": "old towns and mulled wine, no early trains, maybe Vienna",
        "first_day": "2026-12-15", "start_city": "Köln", "settings": {"max_markets_per_day": 1}})
    assert response.status_code == 200
    answer = response.json()
    assert seen == ["old towns and mulled wine, no early trains, maybe Vienna"]
    assert answer["request"] == {
        "first_day": "2026-12-15", "last_day": "2026-12-20", "start_city": "Köln", "end_city": None,
        "settings": {"earliest_train": 600, "min_market_minutes": 120, "max_travel_minutes": 360,
                     "max_markets_per_day": 1, "day_trips": False},
        "wishes": ["old towns", "mulled wine"], "tags": ["old-town"]}
    assert answer["not_covered"] == ["Vienna"]


def test_without_dates_there_is_no_request_yet_and_no_ai_call_for_empty_text(monkeypatch):
    seen = pretend_reader(monkeypatch, {})
    answer = client.post("/api/understand", json={"start_city": "Köln"}).json()
    assert seen == []
    assert answer["request"] is None
    assert answer["notes"] == ["Please pick your dates on the calendar: any days from 15 to 31 December work "
                               "beautifully."]


def test_a_badly_formed_date_is_refused():
    assert client.post("/api/understand", json={"first_day": "15th"}).status_code == 422


def test_a_very_long_text_is_refused_before_any_ai_call(monkeypatch):
    seen = pretend_reader(monkeypatch, {})
    assert client.post("/api/understand", json={"text": "x" * 2001}).status_code == 422
    assert seen == []
