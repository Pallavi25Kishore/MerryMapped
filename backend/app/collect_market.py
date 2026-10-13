import argparse
import json
from datetime import date

from sqlalchemy.orm import Session

from app.agent.onboarding import Collected, onboard
from app.db.connection import make_engine
from app.db.models import create_tables
from app.db.save import MarketDetails, save_market


def report(collected: Collected) -> str:
    """The run report: what the agent did, what it found and dropped, and what is missing."""
    lines = ["Steps:", *(f"  {step}" for step in collected.steps),
             f"Agent's summary: {collected.summary}", "", f"Facts found ({len(collected.facts)}):"]
    for fact in collected.facts:
        lines.append(f"  {fact['kind']}: {json.dumps(fact['value'], ensure_ascii=False)}")
        lines.append(f'    quote: "{fact["evidence_quote"]}"')
        if fact["evidence_translation"]:
            lines.append(f'    English: "{fact["evidence_translation"]}"')
        lines.append(f"    page: {fact['source_url']}")
    lines += ["", f"Facts dropped ({len(collected.dropped)}):"]
    lines += [f"  {fact['kind']}: {reason} ({page})" for page, fact, reason in collected.dropped]
    missing = ", ".join(collected.missing) + " (enter by hand)" if collected.missing else "nothing"
    return "\n".join(lines + ["", f"Missing: {missing}"])


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Collect a market's 2026 facts and save them to the database.")
    parser.add_argument("website")
    parser.add_argument("--name", required=True)
    parser.add_argument("--city", required=True)
    parser.add_argument("--country", required=True, choices=["DE", "BE", "FR"])
    args = parser.parse_args(argv)

    collected = onboard(args.website)
    print(report(collected))

    engine = make_engine()
    create_tables(engine)
    details = MarketDetails(args.name, args.city, args.country, args.website)
    with Session(engine) as session, session.begin():  # all or nothing
        save_market(session, details, collected, date.today())
    print(f"\nSaved {len(collected.facts)} facts for {args.name}.")


if __name__ == "__main__":
    main()
