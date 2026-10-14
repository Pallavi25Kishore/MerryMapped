from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app, headers={"X-Access-Code": "pretend-code"})


def test_options_give_the_form_its_dates_cities_and_settings():
    response = client.get("/api/options")
    assert response.status_code == 200
    options = response.json()
    assert (options["first_day"], options["last_day"]) == ("2026-12-15", "2026-12-31")
    assert "Köln" in options["cities"] and len(options["cities"]) == 9
    assert options["settings"]["earliest_train"] == {"default": 480, "low": 300, "high": 840}
    assert options["settings"]["day_trips"] == {"default": False}
