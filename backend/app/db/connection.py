import os

from sqlalchemy import create_engine

import app.settings  # noqa: F401  (loads backend/.env)


def database_url() -> str:
    # Neon gives "postgresql://..."; "+psycopg" tells SQLAlchemy which driver to use.
    return os.environ["DATABASE_URL"].replace("postgresql://", "postgresql+psycopg://", 1)


def make_engine(url: str | None = None):
    return create_engine(url or database_url())
