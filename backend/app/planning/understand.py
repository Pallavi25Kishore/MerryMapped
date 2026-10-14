import json
from dataclasses import dataclass, field, fields
from datetime import date
from pathlib import Path

import anthropic

from app.planning.plan import Settings, TripRequest
from app.reading.market_reader import TAGS
from app.settings import REQUEST_READER_MODEL
from app.trains.build_links import TRIP_DAYS
from app.trains.stations import STATIONS

REQUEST_PROMPT = Path(__file__).resolve().parents[2] / "prompts" / "request_reader.md"
FIRST_DAY, LAST_DAY = TRIP_DAYS[0], TRIP_DAYS[-1]
OUTSIDE_DATES = ("MerryMapped is a December holiday planner: trips can only be planned between "
                 f"{FIRST_DAY:%d} and {LAST_DAY:%d %B}.")

# Sensible ranges for each setting; a value outside is reset to the default, with a note.
SETTING_RANGES = {
    "earliest_train": (5 * 60, 14 * 60),
    "min_market_minutes": (30, 6 * 60),
    "max_travel_minutes": (60, 12 * 60),
    "max_markets_per_day": (1, 4),
}


@dataclass(frozen=True)
class Form:
    """What the traveller filled in on the website (each field optional) and what they typed.
    settings holds only the settings they changed, by Settings field name (times in minutes)."""
    text: str = ""
    first_day: date | None = None
    last_day: date | None = None
    start_city: str | None = None
    end_city: str | None = None
    tags: tuple[str, ...] = ()
    settings: dict = field(default_factory=dict)


@dataclass
class Understood:
    """The request to plan (None until the dates are usable), notes for the confirm screen, and
    what MerryMapped cannot do."""
    request: TripRequest | None
    notes: list[str]
    not_covered: list[str]


def nullable(schema: dict) -> dict:
    return {"anyOf": [schema, {"type": "null"}]}


def request_schema() -> dict:
    city = nullable({"type": "string", "enum": list(STATIONS)})
    properties = {
        "first_day": nullable({"type": "string"}), "last_day": nullable({"type": "string"}),
        "start_city": city, "end_city": city,
        "earliest_train": nullable({"type": "string"}),
        "min_market_minutes": nullable({"type": "integer"}),
        "max_travel_minutes": nullable({"type": "integer"}),
        "max_markets_per_day": nullable({"type": "integer"}),
        "day_trips": nullable({"type": "boolean"}),
        "tags": {"type": "array", "items": {"type": "string", "enum": list(TAGS)}},
        "wishes": {"type": "array", "items": {"type": "string"}},
        "not_covered": {"type": "array", "items": {"type": "string"}},
    }
    return {"type": "object", "properties": properties, "required": list(properties), "additionalProperties": False}


def request_message(text: str) -> str:
    tags = "\n".join(f"- {tag}: {meaning}" for tag, meaning in TAGS.items())
    return (f"Cities: {', '.join(STATIONS)}\n\nTags:\n{tags}\n\n"
            f"<traveller_text>\n{text}\n</traveller_text>")


def read_text(text: str, client=None, model: str = REQUEST_READER_MODEL) -> dict:
    """What the AI read from the typed text, in the request format."""
    client = client or anthropic.Anthropic()
    response = client.messages.create(
        model=model, max_tokens=2000, system=REQUEST_PROMPT.read_text(encoding="utf-8"),
        output_config={"format": {"type": "json_schema", "schema": request_schema()}},
        messages=[{"role": "user", "content": request_message(text)}],
    )
    return json.loads(next(block.text for block in response.content if block.type == "text"))


def to_date(value: str | None) -> date | None:
    try:
        return date.fromisoformat(value) if value else None
    except ValueError:
        return None


def to_minutes(value: str | None) -> int | None:
    try:
        hours, mins = value.split(":")
        return int(hours) * 60 + int(mins)
    except (AttributeError, ValueError):
        return None


def merge(form: Form, read: dict) -> Understood:
    """Combine the form and the text: filled-in form fields win, the text fills the empty ones.
    Differences, unusable values and missing dates become notes."""
    notes = []

    def pick(label, from_form, from_text, show=str):
        if from_form is not None and from_text is not None and from_form != from_text:
            notes.append(f"You typed {show(from_text)} for the {label}, but the form says {show(from_form)}; "
                         "the form is used.")
        return from_form if from_form is not None else from_text

    first_day = pick("first day", form.first_day, to_date(read["first_day"]), lambda d: f"{d:%d %b}")
    last_day = pick("last day", form.last_day, to_date(read["last_day"]), lambda d: f"{d:%d %b}")
    start_city = pick("start city", form.start_city, read["start_city"])
    end_city = pick("end city", form.end_city, read["end_city"])

    chosen = {}
    for setting in fields(Settings):
        from_text = read.get(setting.name)
        if setting.name == "earliest_train":
            from_text = to_minutes(from_text)
        show = (lambda m: f"{m // 60:02}:{m % 60:02}") if setting.name == "earliest_train" else str
        value = pick(setting.name.replace("_", " "), form.settings.get(setting.name), from_text, show)
        low_high = SETTING_RANGES.get(setting.name)
        if value is not None and low_high and not low_high[0] <= value <= low_high[1]:
            notes.append(f"{setting.name.replace('_', ' ')} of {show(value)} is not sensible; the default is used.")
            value = None
        if value is not None:
            chosen[setting.name] = value
    settings = Settings(**chosen)

    tags = tuple(tag for tag in (form.tags or tuple(read["tags"])) if tag in TAGS)
    wishes = "; ".join(read["wishes"])
    not_covered = list(read["not_covered"])

    if first_day is None or last_day is None:
        notes.append(f"Please choose your dates, between {FIRST_DAY:%d} and {LAST_DAY:%d %B}.")
        return Understood(None, notes, not_covered)
    if not FIRST_DAY <= first_day <= last_day <= LAST_DAY:
        notes.append(OUTSIDE_DATES)
        return Understood(None, notes, not_covered)
    for city in (start_city, end_city):
        if city is not None and city not in STATIONS:
            notes.append(f"{city} is not one of our cities; it is left out.")
    start_city = start_city if start_city in STATIONS else None
    end_city = end_city if end_city in STATIONS else None
    return Understood(TripRequest(first_day, last_day, settings, wishes, tags, start_city, end_city),
                      notes, not_covered)


def understand(form: Form, client=None) -> Understood:
    """Read the typed text (if any) and merge it with the form."""
    empty = {"first_day": None, "last_day": None, "start_city": None, "end_city": None,
             "tags": [], "wishes": [], "not_covered": []}
    read = read_text(form.text, client) if form.text.strip() else empty
    return merge(form, read)
