import json
from datetime import date
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db.models import Fact, Market, TrainLink, Trip, create_tables
from app.main import app, get_session
from app.planning import planner

client = TestClient(app, headers={"X-Access-Code": "pretend-code"})
D1, D2 = date(2026, 12, 23), date(2026, 12, 24)
HOURS = {"days": ["mon", "tue", "wed", "thu", "fri", "sat", "sun"], "opens": "11:00", "closes": "21:00"}


class PretendClaude:
    def __init__(self, *answers):
        self.answers = list(answers)
        self.messages = self

    def create(self, **request):
        return SimpleNamespace(content=[SimpleNamespace(type="text", text=json.dumps(self.answers.pop(0)))])


@pytest.fixture
def session(monkeypatch):
    """A pretend database with two markets and one train, used by the API instead of Neon."""
    # One in-memory database for every connection: the API runs in another thread than the test.
    engine = create_engine("sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False})
    create_tables(engine)
    with Session(engine) as session:
        for market_id, name, city in [(1, "Köln market", "Köln"), (2, "Aachen market", "Aachen")]:
            session.add(Market(id=market_id, name=name, city=city, country="DE", website=f"https://{city.lower()}-market.example/"))
            for kind, value in [("opening_date", {"date": "2026-11-20"}), ("closing_date", {"date": "2026-12-24"}),
                                ("hours", HOURS)]:
                session.add(Fact(market_id=market_id, kind=kind, value=value, source_url="https://a.example/",
                                 checked_on=D1))
        session.add(TrainLink(from_city="Köln", to_city="Aachen", day=D2, trips_per_day=1, source="timetable",
                              checked_on=D1, journeys=[[{"from": "Köln Hbf", "to": "Aachen Hbf", "depart": 500,
                                                         "arrive": 540, "feed": "f", "estimate": False,
                                                         "estimate_from": None}]]))
        session.commit()
        app.dependency_overrides[get_session] = lambda: session
        yield session
    app.dependency_overrides.clear()


def pretend_planner(monkeypatch, *answers):
    real = planner.plan_trip
    monkeypatch.setattr("app.main.plan_trip", lambda request, markets, links: real(
        request, markets, links, client=PretendClaude(*answers)))


def day(when, visits, sleep_in, travel=None):
    return {"date": when, "travel": travel, "visits": [{"market_id": m, "why": "why"} for m in visits],
            "sleep_in": sleep_in, "travel_back": None}


GOOD = {"days": [day("2026-12-23", [1], "Köln"), day("2026-12-24", [2], "Aachen", {"from": "Köln", "to": "Aachen"})]}
CONFIRMED = {"first_day": "2026-12-23", "last_day": "2026-12-24", "start_city": "Köln"}


def test_a_trip_is_planned_saved_and_returned(session, monkeypatch):
    pretend_planner(monkeypatch, GOOD)
    response = client.post("/api/plan", json=CONFIRMED)
    assert response.status_code == 200
    answer = response.json()
    days = answer["itinerary"]["days"]
    assert [d["visits"][0]["name"] for d in days] == ["Köln market", "Aachen market"]
    assert days[1]["travel"]["train"]["depart"] == "08:20"
    saved = session.get(Trip, answer["trip_id"])
    assert saved.itinerary == answer["itinerary"] and saved.request["start_city"] == "Köln"
    assert len(answer["trip_id"]) >= 16


def test_a_plan_left_with_problems_is_repaired_before_saving(session, monkeypatch):
    repeat = {"days": [day("2026-12-23", [1], "Köln"),
                       day("2026-12-24", [2, 2], "Aachen", {"from": "Köln", "to": "Aachen"})]}
    pretend_planner(monkeypatch, *[repeat] * (planner.MAX_FIX_ROUNDS + 1))
    days = client.post("/api/plan", json=CONFIRMED).json()["itinerary"]["days"]
    assert [v["market_id"] for v in days[1]["visits"]] == [2]
    assert "never visit a market twice" in days[1]["left_out"][0]["reason"]


def test_a_request_that_breaks_the_rules_is_refused_before_planning(session, monkeypatch):
    pretend_planner(monkeypatch)  # no answers: any planner call would fail
    response = client.post("/api/plan", json={**CONFIRMED, "settings": {"max_markets_per_day": 9}})
    assert response.status_code == 422
    assert response.json()["detail"][0] == "We can plan 1 to 4 markets a day, so we've kept it at 2."
    assert session.scalars(select(Trip)).all() == []


def test_no_usable_plan_means_try_again_and_nothing_saved(session, monkeypatch):
    one_day = {"days": [day("2026-12-23", [1], "Köln")]}
    pretend_planner(monkeypatch, *[one_day] * (planner.MAX_FIX_ROUNDS + 1))
    response = client.post("/api/plan", json=CONFIRMED)
    assert response.status_code == 502
    assert session.scalars(select(Trip)).all() == []
