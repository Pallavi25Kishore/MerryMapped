import pytest


@pytest.fixture(autouse=True)
def access_code(monkeypatch):
    """Every test runs with a pretend access code, never the real one from backend/.env."""
    monkeypatch.setenv("ACCESS_CODE", "pretend-code")
