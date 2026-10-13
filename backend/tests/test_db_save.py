from datetime import date

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agent.onboarding import Collected
from app.db.connection import make_engine
from app.db.models import Fact, Market, create_tables
from app.db.save import MarketDetails, save_market

COLOGNE = MarketDetails(name="Pretend Cathedral Market", city="Köln", country="DE",
                        website="https://koeln-market.example/de/")
AACHEN = MarketDetails(name="Pretend Aachen Market", city="Aachen", country="DE",
                       website="https://aachen-market.example/")


def fact(kind, value, page="https://koeln-market.example/de/"):
    return {"kind": kind, "value": value, "evidence_quote": "Mo 16.11.2026",
            "evidence_translation": "Mon 16.11.2026", "year_quote": "Mo 16.11.2026",
            "source_url": page, "page_fingerprint": "ab" * 32}


def collected(*facts):
    return Collected(facts=list(facts), dropped=[], missing=[], steps=[], summary="test")


@pytest.fixture
def engine():
    engine = make_engine("sqlite://")
    create_tables(engine)
    return engine


def save(engine, details, found, today=date(2026, 10, 20)):
    with Session(engine) as session, session.begin():
        save_market(session, details, found, today)


def facts_of(engine, details):
    with Session(engine) as session:
        market = session.scalars(select(Market).where(Market.website == details.website)).one()
        return market.name, session.scalars(select(Fact).where(Fact.market_id == market.id)).all()


def test_a_new_market_and_its_facts_are_saved(engine):
    save(engine, COLOGNE, collected(fact("opening_date", {"date": "2026-11-16"})))

    name, facts = facts_of(engine, COLOGNE)
    assert name == "Pretend Cathedral Market"
    assert [(f.kind, f.value, f.status) for f in facts] == [("opening_date", {"date": "2026-11-16"}, "checked")]
    assert facts[0].source_url == "https://koeln-market.example/de/"
    assert facts[0].page_fingerprint == "ab" * 32
    assert facts[0].checked_on == date(2026, 10, 20)


def test_running_again_replaces_the_facts_and_keeps_one_market(engine):
    save(engine, COLOGNE, collected(fact("opening_date", {"date": "2026-11-16"})))
    renamed = MarketDetails(**{**COLOGNE.__dict__, "name": "Weihnachtsmarkt am Dom"})
    save(engine, renamed, collected(fact("opening_date", {"date": "2026-11-17"})), today=date(2026, 11, 1))

    name, facts = facts_of(engine, COLOGNE)
    assert name == "Weihnachtsmarkt am Dom"
    assert [(f.value, f.checked_on) for f in facts] == [({"date": "2026-11-17"}, date(2026, 11, 1))]
    with Session(engine) as session:
        assert len(session.scalars(select(Market)).all()) == 1


def test_another_markets_facts_are_untouched(engine):
    save(engine, AACHEN, collected(fact("hours", {"days": ["sat"], "opens": "11:00", "closes": "21:00"},
                                        page="https://aachen-market.example/")))
    save(engine, COLOGNE, collected(fact("opening_date", {"date": "2026-11-16"})))
    save(engine, COLOGNE, collected())

    assert [f.kind for f in facts_of(engine, AACHEN)[1]] == ["hours"]
    assert facts_of(engine, COLOGNE)[1] == []


def test_a_fact_without_its_quote_is_saved(engine):
    no_quote = fact("opening_date", {"date": "2026-11-16"}) | {
        "evidence_quote": None, "evidence_translation": None, "quote_not_kept": "The site's terms deny this"}
    save(engine, COLOGNE, collected(no_quote))

    saved = facts_of(engine, COLOGNE)[1][0]
    assert (saved.evidence_quote, saved.evidence_translation) == (None, None)
    assert saved.source_url == "https://koeln-market.example/de/"
