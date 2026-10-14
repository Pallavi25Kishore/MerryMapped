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
OUTSIDE_DATES = (f"MerryMapped plans trips between {FIRST_DAY:%-d} and {LAST_DAY:%-d %B}, the most magical stretch "
                 "of the season. Please pick dates in that window.")

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
    settings holds only the settings they changed, by Settings field name (times in minutes).
    There is no tag picker: tags come only from what they typed."""
    text: str = ""
    first_day: date | None = None
    last_day: date | None = None
    start_city: str | None = None
    end_city: str | None = None
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


def hhmm(minutes: int) -> str:
    return f"{minutes // 60:02}:{minutes % 60:02}"


def duration(minutes: int) -> str:
    hours, mins = divmod(minutes, 60)
    return f"{hours} h {mins} min" if hours and mins else f"{hours} h" if hours else f"{mins} min"


# How each choice is described to the traveller: in full (what they mentioned), briefly (what the
# website says), and where on the website it was chosen. Notes are written for travellers: warm,
# plain, and saying what we did and how to change it.
DESCRIBE = {
    "first_day": (lambda d: f"{d:%a %-d %b} as your first day", lambda d: f"{d:%a %-d %b}", "the calendar"),
    "last_day": (lambda d: f"{d:%a %-d %b} as your last day", lambda d: f"{d:%a %-d %b}", "the calendar"),
    "start_city": (lambda c: f"starting in {c}", str, "the map"),
    "end_city": (lambda c: f"finishing in {c}", str, "the map"),
    "earliest_train": (lambda m: f"trains from {hhmm(m)}", hhmm, "Your pace"),
    "min_market_minutes": (lambda m: f"{duration(m)} at each market", duration, "Your pace"),
    "max_travel_minutes": (lambda m: f"{duration(m)} of train travel a day", duration, "Your pace"),
    "max_markets_per_day": (lambda n: f"{n} {'market' if n == 1 else 'markets'} a day", str, "Your pace"),
    "day_trips": (lambda on: "day trips" if on else "no day trips", lambda on: "on" if on else "off", "Your pace"),
}

# What we can plan for each setting, said kindly when a typed value is outside it.
OUT_OF_RANGE = {
    "earliest_train": lambda low, high, kept: (f"We can plan trains leaving between {hhmm(low)} and {hhmm(high)}, "
                                               f"so we've kept your earliest train at {hhmm(kept)}."),
    "min_market_minutes": lambda low, high, kept: (f"We can plan between {duration(low)} and {duration(high)} at each "
                                                   f"market, so we've kept it at {duration(kept)}."),
    "max_travel_minutes": lambda low, high, kept: (f"We can plan between {duration(low)} and {duration(high)} of train "
                                                   f"travel a day, so we've kept it at {duration(kept)}."),
    "max_markets_per_day": lambda low, high, kept: (f"We can plan {low} to {high} markets a day, so we've kept it at "
                                                    f"{kept}."),
}


def merge(form: Form, read: dict) -> Understood:
    """Combine the form and the text: filled-in form fields win, the text fills the empty ones.
    Differences, unusable values and missing dates become notes."""
    notes = []

    def pick(field, from_form, from_text):
        if from_form is not None and from_text is not None and from_form != from_text:
            in_full, briefly, where = DESCRIBE[field]
            notes.append(f"You mentioned {in_full(from_text)}, and {where} says {briefly(from_form)}. "
                         f"We've gone with {where}, and you can change it there anytime.")
        return from_form if from_form is not None else from_text

    first_day = pick("first_day", form.first_day, to_date(read["first_day"]))
    last_day = pick("last_day", form.last_day, to_date(read["last_day"]))
    start_city = pick("start_city", form.start_city, read["start_city"])
    end_city = pick("end_city", form.end_city, read["end_city"])

    chosen = {}
    for setting in fields(Settings):
        from_text = read.get(setting.name)
        if setting.name == "earliest_train":
            from_text = to_minutes(from_text)
        value = pick(setting.name, form.settings.get(setting.name), from_text)
        low_high = SETTING_RANGES.get(setting.name)
        if value is not None and low_high and not low_high[0] <= value <= low_high[1]:
            notes.append(OUT_OF_RANGE[setting.name](*low_high, setting.default))
            value = None
        if value is not None:
            chosen[setting.name] = value
    settings = Settings(**chosen)

    tags = tuple(tag for tag in read["tags"] if tag in TAGS)
    wishes = "; ".join(read["wishes"])
    not_covered = list(read["not_covered"])

    if first_day is None or last_day is None:
        notes.append(f"Please pick your dates on the calendar: any days from {FIRST_DAY:%-d} to {LAST_DAY:%-d %B} "
                     "work beautifully.")
        return Understood(None, notes, not_covered)
    if not FIRST_DAY <= first_day <= last_day <= LAST_DAY:
        notes.append(OUTSIDE_DATES)
        return Understood(None, notes, not_covered)
    for city in (start_city, end_city):
        if city is not None and city not in STATIONS:
            notes.append(f"{city} isn't on our map yet, so we've planned without it.")
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
