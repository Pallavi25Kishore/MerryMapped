from dataclasses import dataclass
from datetime import date

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.agent.onboarding import Collected
from app.db.models import Fact, Market


@dataclass(frozen=True)
class MarketDetails:
    """What the admin types in: the market's name, city, country and website."""

    name: str
    city: str
    country: str  # "DE", "BE" or "FR"
    website: str


def save_market(session: Session, details: MarketDetails, collected: Collected, today: date) -> Market:
    """Find or create the market, and replace its facts with the newly checked ones. The caller commits."""
    market = session.scalars(select(Market).where(Market.website == details.website)).one_or_none()
    if market is None:
        market = Market(website=details.website)
        session.add(market)
    market.name, market.city, market.country = details.name, details.city, details.country
    session.flush()  # the database gives a new market its id

    session.execute(delete(Fact).where(Fact.market_id == market.id))
    session.add_all(
        Fact(
            market_id=market.id,
            kind=fact["kind"],
            value=fact["value"],
            evidence_quote=fact["evidence_quote"],
            evidence_translation=fact["evidence_translation"],
            source_url=fact["source_url"],
            page_fingerprint=fact["page_fingerprint"],
            checked_on=today,
        )
        for fact in collected.facts
    )
    return market
