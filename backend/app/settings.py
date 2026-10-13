from pathlib import Path

from dotenv import load_dotenv

# backend/.env holds secrets such as ANTHROPIC_API_KEY. It is git-ignored.
load_dotenv(Path(__file__).resolve().parents[1] / ".env")

# The Claude model that drafts site reviews.
TERMS_READER_MODEL = "claude-sonnet-5-5"

# The Claude model that reads market pages for facts.
MARKET_READER_MODEL = "claude-sonnet-5-5"

# The Claude model that navigates a market's site (the onboarding agent).
ONBOARDING_AGENT_MODEL = "claude-sonnet-5-5"

# The Claude model that writes each market's description from its checked facts.
DESCRIPTION_WRITER_MODEL = "claude-sonnet-5-5"

# The Claude model that checks each fact against its own quote (the verification layer).
FACT_VERIFIER_MODEL = "claude-sonnet-5-5"
