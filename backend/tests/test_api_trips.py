from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db.models import Trip, create_tables
from app.main import app, get_session

client = TestClient(app, headers={"X-Access-Code": "pretend-code"})


def trip(trip_id, planned, cities):
    days = [{"date": f"2026-12-{15 + n}", "sleep_in": city} for n, city in enumerate(cities)]
    return Trip(id=trip_id, created_at=planned, itinerary={"days": days},
                request={"first_day": days[0]["date"], "last_day": days[-1]["date"]})


@pytest.fixture
def session():
    """A pretend database with two saved trips, used by the API instead of Neon."""
    engine = create_engine("sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False})
    create_tables(engine)
    with Session(engine) as session:
        session.add_all([trip("older-trip", datetime(2026, 10, 1, 9, 0), ["Köln", "Köln", "Aachen"]),
                         trip("newer-trip", datetime(2026, 10, 12, 18, 30), ["Colmar"])])
        session.commit()
        app.dependency_overrides[get_session] = lambda: session
        yield session
    app.dependency_overrides.clear()


def test_my_trips_lists_newest_first_with_dates_and_cities(session):
    trips = client.get("/api/trips").json()
    assert [t["trip_id"] for t in trips] == ["newer-trip", "older-trip"]
    assert trips[1] == {"trip_id": "older-trip", "created_at": "2026-10-01T09:00:00",
                        "first_day": "2026-12-15", "last_day": "2026-12-17", "cities": ["Köln", "Aachen"]}


def test_a_saved_trip_opens_again(session):
    answer = client.get("/api/trips/newer-trip").json()
    assert answer["itinerary"]["days"][0]["sleep_in"] == "Colmar"


def test_deleting_removes_the_trip_and_gives_a_receipt(session):
    receipt = client.delete("/api/trips/older-trip").json()
    assert (receipt["trip_id"], receipt["planned_at"], receipt["kept"]) == ("older-trip", "2026-10-01T09:00:00", "nothing")
    assert "deleted_at" in receipt
    assert [t.id for t in session.scalars(select(Trip))] == ["newer-trip"]
    assert client.get("/api/trips/older-trip").status_code == 404


def test_an_unknown_trip_is_not_found(session):
    assert client.get("/api/trips/no-such-trip").status_code == 404
    assert client.delete("/api/trips/no-such-trip").status_code == 404
