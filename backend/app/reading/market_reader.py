import json
from pathlib import Path

import anthropic

from app.settings import MARKET_READER_MODEL

MARKET_READER_PROMPT = Path(__file__).resolve().parents[2] / "prompts" / "market_reader.md"

KINDS = ["opening_date", "closing_date", "hours", "closed_on", "special_hours", "address", "detail", "tag"]
WEEKDAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
TAGS = [
    "old-town", "cathedral", "castle", "riverside", "park-or-forest", "underground",      # setting
    "medieval", "light-show", "traditional", "modern-design", "sustainable",              # theme
    "artisan", "food-focused", "regional-food", "wine", "vegan-options", "live-music",    # on offer
    "stage-programme", "ice-rink", "rides", "nativity",
    "family", "accessible",                                                               # who it suits
    "paid-entry",                                                                         # practical
]

# The shape Claude's answer must have. "value" has every possible field; Claude fills the ones
# that apply to the kind of fact and sets the rest to null.
NULLABLE_TEXT = {"type": ["string", "null"]}
VALUE_FIELDS = {
    "date": NULLABLE_TEXT,
    "days": {"type": ["array", "null"], "items": {"type": "string", "enum": WEEKDAYS}},
    "opens": NULLABLE_TEXT,
    "closes": NULLABLE_TEXT,
    "from": NULLABLE_TEXT,
    "until": NULLABLE_TEXT,
    "text": NULLABLE_TEXT,
    "tag": {"type": ["string", "null"], "enum": [*TAGS, None]},
}
FACT = {
    "type": "object",
    "properties": {
        "kind": {"type": "string", "enum": KINDS},
        "value": {
            "type": "object",
            "properties": VALUE_FIELDS,
            "required": list(VALUE_FIELDS),
            "additionalProperties": False,
        },
        "evidence_quote": {"type": "string"},
        "evidence_translation": NULLABLE_TEXT,
        "year_quote": NULLABLE_TEXT,
    },
    "required": ["kind", "value", "evidence_quote", "evidence_translation", "year_quote"],
    "additionalProperties": False,
}
FACTS_SCHEMA = {
    "type": "object",
    "properties": {"facts": {"type": "array", "items": FACT}},
    "required": ["facts"],
    "additionalProperties": False,
}


def read_page(url: str, text: str, client=None, model: str = MARKET_READER_MODEL) -> list[dict]:
    """Ask Claude for the facts one cleaned market page states; nothing is checked here yet."""
    client = client or anthropic.Anthropic()
    response = client.messages.create(
        model=model,
        max_tokens=4000,
        system=MARKET_READER_PROMPT.read_text(encoding="utf-8"),
        output_config={"format": {"type": "json_schema", "schema": FACTS_SCHEMA}},
        messages=[{"role": "user", "content": page_message(url, text)}],
    )
    reply = next(block.text for block in response.content if block.type == "text")
    facts = json.loads(reply)["facts"]
    return [{**fact, "value": tidy_value(fact["value"])} for fact in facts]


def page_message(url: str, text: str) -> str:
    """The page, wrapped and labelled so it can't be mistaken for instructions."""
    return f'Write down the facts this page states.\n\n<market_page url="{url}">\n{text}\n</market_page>'


def tidy_value(value: dict) -> dict:
    """Drop the fields Claude set to null: {"date": "2026-11-16", "days": None, ...} -> {"date": ...}."""
    return {field: content for field, content in value.items() if content is not None}
