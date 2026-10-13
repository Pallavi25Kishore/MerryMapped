from datetime import date

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.connection import make_engine
from app.db.models import Fact, Market, create_tables

WEBSITE = "https://koeln-market.example/de/"


@pytest.fixture
def session():
    engine = make_engine("sqlite://")
    create_tables(engine)
    with Session(engine) as session:
        yield session


def cologne():
    return Market(name="Pretend Cathedral Market", city="Köln", country="DE", website=WEBSITE)


def opening_fact(market):
    return Fact(
        market_id=market.id,
        kind="opening_date",
        value={"date": "2026-11-16"},
        evidence_quote="Der Markt öffnet am 16. November 2026.",
        evidence_translation="The market opens on 16 November 2026.",
        source_url="https://koeln-market.example/de/zeiten/",
        page_fingerprint="ab" * 32,
        checked_on=date(2026, 10, 20),
    )


def test_market_and_fact_are_saved_and_read_back(session):
    market = cologne()
    session.add(market)
    session.flush()
    session.add(opening_fact(market))
    session.commit()

    fact = session.scalars(select(Fact)).one()
    assert fact.market_id == market.id
    assert fact.value == {"date": "2026-11-16"}
    assert fact.checked_on == date(2026, 10, 20)


def test_the_same_website_cannot_be_added_twice(session):
    session.add(cologne())
    session.commit()
    session.add(cologne())
    with pytest.raises(IntegrityError):
        session.commit()


def test_a_new_fact_is_marked_checked(session):
    market = cologne()
    session.add(market)
    session.flush()
    session.add(opening_fact(market))
    session.commit()
    assert session.scalars(select(Fact)).one().status == "checked"
