from sqlalchemy import text

from app.db.connection import database_url, make_engine


def test_database_url_names_the_psycopg_driver(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pw@db.example/merry?sslmode=require")
    assert database_url() == "postgresql+psycopg://user:pw@db.example/merry?sslmode=require"


def test_make_engine_uses_the_given_url_instead_of_neon():
    engine = make_engine("sqlite://")
    with engine.connect() as conn:
        assert conn.execute(text("SELECT 1")).scalar() == 1
