from datetime import date

from sqlalchemy import JSON, ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Market(Base):
    __tablename__ = "markets"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    city: Mapped[str]
    country: Mapped[str]  # "DE", "BE" or "FR"
    website: Mapped[str] = mapped_column(unique=True)


class Fact(Base):
    __tablename__ = "facts"

    id: Mapped[int] = mapped_column(primary_key=True)
    market_id: Mapped[int] = mapped_column(ForeignKey("markets.id"))
    kind: Mapped[str]  # opening_date, closing_date, hours, closed_on, special_hours, address, detail or tag
    value: Mapped[dict] = mapped_column(JSON)
    evidence_quote: Mapped[str | None]  # None when the site's review doesn't allow keeping quotes
    evidence_translation: Mapped[str | None]
    source_url: Mapped[str]
    page_fingerprint: Mapped[str]
    checked_on: Mapped[date]
    status: Mapped[str] = mapped_column(default="checked")


def create_tables(engine) -> None:
    Base.metadata.create_all(engine)
