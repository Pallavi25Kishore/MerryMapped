from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_the_right_code_is_let_in():
    assert client.get("/api/options", headers={"X-Access-Code": "pretend-code"}).status_code == 200


def test_a_missing_or_wrong_code_is_refused():
    assert client.get("/api/options").status_code == 401
    assert client.get("/api/options", headers={"X-Access-Code": "guess"}).status_code == 401


def test_with_no_code_set_everything_is_refused(monkeypatch):
    monkeypatch.delenv("ACCESS_CODE")
    assert client.get("/api/options", headers={"X-Access-Code": ""}).status_code == 401


def test_a_wrong_code_is_refused_before_any_ai_call(monkeypatch):
    calls = []
    monkeypatch.setattr("app.planning.understand.read_text", lambda *a, **k: calls.append(a))
    assert client.post("/api/understand", json={"text": "old towns"}).status_code == 401
    assert calls == []


def test_health_stays_open():
    assert client.get("/health").status_code == 200
