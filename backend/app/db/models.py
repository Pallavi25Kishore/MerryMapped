from datetime import date

from sqlalchemy import JSON, ForeignKey, UniqueConstraint
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
    description: Mapped[str | None]  # written from checked facts only; None if not allowed or failed


class Fact(Base):
    __tablename__ = "facts"

    id: Mapped[int] = mapped_column(primary_key=True)
    market_id: Mapped[int] = mapped_column(ForeignKey("markets.id"))
    kind: Mapped[str]  # opening_date, closing_date, hours, closed_on, special_hours, address, detail or tag
    value: Mapped[dict] = mapped_column(JSON)
    evidence_quote: Mapped[str | None]  # None when the site's review doesn't allow keeping quotes
    evidence_translation: Mapped[str | None]
    source_url: Mapped[str]
    page_fingerprint: Mapped[str | None]  # None for facts entered by hand (no page downloaded)
    checked_on: Mapped[date]
    status: Mapped[str] = mapped_column(default="checked")


class TrainLink(Base):
    """The good train journeys from one city to another on one day, worked out from the
    timetable files (or entered by hand). Times are minutes after midnight of `day`."""
    __tablename__ = "train_links"
    __table_args__ = (UniqueConstraint("from_city", "to_city", "day"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    from_city: Mapped[str]  # as in the markets table (or "Brussels", where the hand-entered leg joins)
    to_city: Mapped[str]
    day: Mapped[date]
    journeys: Mapped[list] = mapped_column(JSON)  # each journey: a list of legs (stations, times, feed)
    fastest_minutes: Mapped[int | None]  # None when there is no good journey that day
    fewest_changes: Mapped[int | None]
    trips_per_day: Mapped[int]
    first_departure: Mapped[int | None]
    last_departure: Mapped[int | None]
    source: Mapped[str]  # "timetable", "estimate" or "entered by hand"
    based_on_day: Mapped[date | None]  # for an estimate: the same weekday it was worked out from
    checked_on: Mapped[date]


def create_tables(engine) -> None:
    Base.metadata.create_all(engine)
