from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db.models import Fact, Market, create_tables
from app.main import app, get_session
from app.rules.site_review import SiteReview

client = TestClient(app, headers={"X-Access-Code": "pretend-code"})
ALLOW = {"answer": "allow", "because": "No terms restrict this."}
REVIEW = SiteReview(reviewed_on=date(2026, 10, 13), terms_urls=["https://koeln-market.example/impressum"],
                    automated_access=ALLOW, purposes={"collect_facts": ALLOW, "show_link": ALLOW})


@pytest.fixture
def session(monkeypatch):
    """A pretend database with one market: a checked fact from its own site and a hand-entered one
    from another site. Only the market's own site has a review."""
    engine = create_engine("sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False})
    create_tables(engine)
    with Session(engine) as session:
        session.add(Market(id=1, name="Köln market", city="Köln", country="DE", website="https://www.koeln-market.example/"))
        session.add(Fact(market_id=1, kind="opening_date", value={"date": "2026-11-20"},
                         evidence_quote="Der Markt öffnet am 20. November.", evidence_translation="The market opens on 20 November.",
                         source_url="https://www.koeln-market.example/zeiten", page_fingerprint="ab" * 32,
                         checked_on=date(2026, 10, 13)))
        session.add(Fact(market_id=1, kind="closing_date", value={"date": "2026-12-23"}, evidence_quote=None,
                         evidence_translation=None, source_url="https://city-news.example/markets",
                         checked_on=date(2026, 10, 13), status="entered by hand"))
        session.commit()
        monkeypatch.setattr("app.main.load_review", lambda site: REVIEW if site == "koeln-market.example" else None)
        app.dependency_overrides[get_session] = lambda: session
        yield session
    app.dependency_overrides.clear()


def test_sources_show_each_fact_with_its_proof_and_the_legal_decision(session):
    answer = client.get("/api/markets/1/sources").json()
    checked, by_hand = answer["facts"]
    assert checked == {"kind": "opening_date", "value": {"date": "2026-11-20"},
                       "page": "https://www.koeln-market.example/zeiten", "quote": "Der Markt öffnet am 20. November.",
                       "english": "The market opens on 20 November.", "checked_on": "2026-10-13", "status": "checked"}
    assert (by_hand["quote"], by_hand["status"]) == (None, "entered by hand")
    assert answer["legal"]["koeln-market.example"]["purposes"] == {"collect_facts": ALLOW, "show_link": ALLOW}
    assert answer["legal"]["city-news.example"] is None  # no review: shown as such


def test_an_unknown_market_is_not_found(session):
    assert client.get("/api/markets/99/sources").status_code == 404
