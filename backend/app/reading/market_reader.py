import json
from pathlib import Path

import anthropic

from app.settings import MARKET_READER_MODEL

MARKET_READER_PROMPT = Path(__file__).resolve().parents[2] / "prompts" / "market_reader.md"

KINDS = ["opening_date", "closing_date", "hours", "closed_on", "special_hours", "address", "detail", "tag"]
WEEKDAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
# The fixed tags, each with what the page must show. The same list is in prompts/market_reader.md.
TAGS = {
    "old-town": "it is in a historic old town or square",
    "cathedral": "it is at a cathedral, minster or major church",
    "castle": "it is at or in a castle, palace or fortress",
    "riverside": "it is on a river, lake or harbour",
    "park-or-forest": "it is in a park, garden or forest",
    "underground": "it is in cellars, caves or vaults",
    "medieval": "a medieval theme: costumes, old crafts, period music",
    "light-show": "illuminations, light installations or a light canopy",
    "traditional": "it describes itself as traditional or historic",
    "modern-design": "it is modern, design-led or contemporary",
    "sustainable": "a sustainability focus or certification",
    "artisan": "handcrafts and makers",
    "food-focused": "food is a main draw",
    "regional-food": "regional specialities are named",
    "wine": "it is wine-focused, beyond mulled wine",
    "vegan-options": "vegan food is stated",
    "live-music": "concerts or regular live music",
    "stage-programme": "a stage with a daily programme",
    "ice-rink": "a skating rink",
    "rides": "a Ferris wheel, carousel or other rides",
    "nativity": "a nativity scene or living nativity",
    "family": "a children's programme or children's area",
    "accessible": "wheelchair access is stated",
    "paid-entry": "an entry fee is charged",
}

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
    "tag": {"anyOf": [{"type": "string", "enum": list(TAGS)}, {"type": "null"}]},
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
