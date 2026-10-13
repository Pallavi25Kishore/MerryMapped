import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

import app.collect_market as collect_market
from dataclasses import replace

from app.agent.onboarding import Collected
from app.rules.decision import Basis, Decision
from app.db.connection import make_engine
from app.db.models import Fact, Market
from tests.test_db_save import fact

WEBSITE = "https://koeln-market.example/de/"
ARGS = [WEBSITE, "--name", "Pretend Cathedral Market", "--city", "Köln", "--country", "DE"]

FOUND = Collected(
    facts=[fact("opening_date", {"date": "2026-11-16"})],
    dropped=[(WEBSITE, fact("closing_date", {"date": "2025-12-23"}), "date 2025-12-23 is outside the 2026 season")],
    missing=["closing_date", "hours"],
    steps=[f"open_page {WEBSITE} (home page): read"],
    summary="stopped by the guardrails",
)


def test_report_shows_facts_dropped_facts_and_what_is_missing():
    text = collect_market.report(FOUND)

    assert 'opening_date: {"date": "2026-11-16"}' in text
    assert 'quote: "Mo 16.11.2026"' in text
    assert 'English: "Mon 16.11.2026"' in text
    assert 'closing_date: {"date": "2025-12-23"}\n    dropped: date 2025-12-23 is outside the 2026 season' in text
    assert "Missing: closing_date, hours (enter by hand)" in text


def test_report_says_when_nothing_is_missing():
    complete = Collected(facts=[], dropped=[], missing=[], steps=[], summary="done")

    assert collect_market.report(complete).endswith("Missing: nothing")


def test_the_command_collects_and_saves(tmp_path, monkeypatch, capsys):
    database = f"sqlite:///{tmp_path / 'merry.db'}"
    monkeypatch.setenv("DATABASE_URL", database)
    monkeypatch.setattr(collect_market, "onboard", lambda website: FOUND)
    collect_market.main(ARGS)

    assert "Saved 1 facts for Pretend Cathedral Market without a description." in capsys.readouterr().out
    with Session(make_engine(database)) as session:
        market = session.scalars(select(Market)).one()
        assert (market.name, market.city, market.country) == ("Pretend Cathedral Market", "Köln", "DE")
        assert [f.kind for f in session.scalars(select(Fact))] == ["opening_date"]


def test_a_wrong_country_is_refused(monkeypatch):
    monkeypatch.setattr(collect_market, "onboard", lambda website: pytest.fail("must not run"))
    with pytest.raises(SystemExit):
        collect_market.main([WEBSITE, "--name", "X", "--city", "Köln", "--country", "GE"])


def test_report_says_when_a_quote_was_not_kept():
    no_quote = fact("opening_date", {"date": "2026-11-16"}) | {
        "evidence_quote": None, "evidence_translation": None, "quote_not_kept": "The site's terms deny this"}
    text = collect_market.report(Collected(facts=[no_quote], dropped=[], missing=[], steps=[], summary="x"))

    assert "quote not kept: The site's terms deny this" in text
    assert "quote:" not in text


ALLOWED = Decision(True, "Admin-approved review (2026-10-20) allows this", Basis.SITE_TERMS, "Row 1")
DENIED = Decision(False, "Admin-approved review (2026-10-20) denies this", Basis.SITE_TERMS, "Row 6b")


def run_command(tmp_path, monkeypatch, found, writer):
    database = f"sqlite:///{tmp_path / 'merry.db'}"
    monkeypatch.setenv("DATABASE_URL", database)
    monkeypatch.setattr(collect_market, "onboard", lambda website: found)
    monkeypatch.setattr(collect_market, "write_description", writer)
    collect_market.main(ARGS)
    with Session(make_engine(database)) as session:
        return session.scalars(select(Market)).one().description


def test_the_description_is_written_and_saved_when_allowed(tmp_path, monkeypatch, capsys):
    found = replace(FOUND, description_allowed=ALLOWED, page_texts=["Seite"])
    saved = run_command(tmp_path, monkeypatch, found, lambda *args: "A market on Roncalliplatz.")

    out = capsys.readouterr().out
    assert "Description:\n  A market on Roncalliplatz." in out
    assert "with a description." in out
    assert saved == "A market on Roncalliplatz."


def test_no_description_when_the_review_denies_it(tmp_path, monkeypatch, capsys):
    found = replace(FOUND, description_allowed=DENIED)
    saved = run_command(tmp_path, monkeypatch, found, lambda *args: pytest.fail("must not be called"))

    assert "Description not written: Admin-approved review (2026-10-20) denies this" in capsys.readouterr().out
    assert saved is None
