import json
import re
from datetime import date

from app.reading.draft_checks import tidy

MAX_QUOTE = 300
SEASON_START, SEASON_END = date(2026, 10, 15), date(2027, 1, 31)
SEASON_YEAR = 2026
TIME = re.compile(r"^(([01]\d|2[0-3]):[0-5]\d|24:00)$")

# The value fields each kind of fact must have (hours may also have from and until).
NEEDS = {
    "opening_date": {"date"},
    "closing_date": {"date"},
    "hours": {"days", "opens", "closes"},
    "closed_on": {"date"},
    "special_hours": {"date", "opens", "closes"},
    "address": {"text"},
}
MAY_ALSO = {"hours": {"from", "until"}}


def fact_problem(fact: dict, page_text: str) -> str | None:
    """Why one fact fails checks 1 to 6, or None if it passes."""
    page, quote, value, kind = tidy(page_text), fact["evidence_quote"], fact["value"], fact["kind"]

    # 1 and 2: the proof is really on the page, and short.
    if not tidy(quote) or tidy(quote) not in page:
        return "evidence quote not found on the page"
    if len(quote) > MAX_QUOTE:
        return f"evidence quote is longer than {MAX_QUOTE} characters"

    # 3: the right fields for this kind of fact.
    fields = set(value)
    if not NEEDS[kind] <= fields <= NEEDS[kind] | MAY_ALSO.get(kind, set()):
        return f"{kind} needs {sorted(NEEDS[kind])}, got {sorted(fields)}"
    if not all(value.get(field) for field in fields):
        return "a value field is empty"

    # 4: real dates and times.
    dates = {}
    for field in ("date", "from", "until"):
        if field in value:
            try:
                dates[field] = date.fromisoformat(value[field])
            except ValueError:
                return f"{field} {value[field]!r} is not a real date"
    if "opens" in value:
        if not TIME.match(value["opens"]) or not TIME.match(value["closes"]):
            return "times must be HH:MM"
        if value["opens"] >= value["closes"]:
            return "opening time is not before closing time"
    if "from" in dates and "until" in dates and dates["from"] > dates["until"]:
        return "from is after until"

    # 5 and 6: the year is stated on the page, and the dates are in the 2026 season.
    if dates:
        year_quote = fact["year_quote"] or ""
        if not tidy(year_quote) or tidy(year_quote) not in page:
            return "year is not stated on the page"
        for day in dates.values():
            if not SEASON_START <= day <= SEASON_END:
                return f"date {day} is outside the 2026 season"
            years = {str(day.year), str(SEASON_YEAR)} if day.month == 1 else {str(day.year)}
            if not any(year in year_quote for year in years):
                return f"year quote does not state {day.year}"
    return None


def check_facts(facts: list[dict], page_text: str) -> tuple[list[dict], list[tuple[dict, str]]]:
    """All checks on one page: the facts that passed, and the dropped facts with the reason for each."""
    kept, dropped = [], []
    for fact in facts:
        problem = fact_problem(fact, page_text)
        if problem:
            dropped.append((fact, problem))
        else:
            kept.append(fact)
    kept, contradicted = drop_contradictions(kept)
    return kept, dropped + contradicted


def drop_contradictions(facts: list[dict]) -> tuple[list[dict], list[tuple[dict, str]]]:
    """Checks 7 to 10 on facts that each passed checks 1 to 6, from one page or from several."""
    kept, dropped = list(facts), []

    # 8: two different opening dates (or closing dates): drop them all.
    for kind in ("opening_date", "closing_date"):
        same_kind = [fact for fact in kept if fact["kind"] == kind]
        if len({fact["value"]["date"] for fact in same_kind}) > 1:
            for fact in same_kind:
                kept.remove(fact)
                dropped.append((fact, f"different {kind}s were given"))

    # 7: the opening date is not after the closing date.
    opening = next((f for f in kept if f["kind"] == "opening_date"), None)
    closing = next((f for f in kept if f["kind"] == "closing_date"), None)
    if opening and closing and opening["value"]["date"] > closing["value"]["date"]:
        for fact in (opening, closing):
            kept.remove(fact)
            dropped.append((fact, "opening date is after closing date"))

    # 9: two hours facts for the same weekday in the same period, with different times.
    hours = [fact for fact in kept if fact["kind"] == "hours"]
    clashing = [
        fact for fact in hours
        if any(other is not fact and hours_clash(fact["value"], other["value"]) for other in hours)
    ]
    for fact in clashing:
        kept.remove(fact)
        dropped.append((fact, "different hours were given for the same days"))

    # 10: a date that is both closed and given special hours, or given two different special hours.
    for day in {fact["value"]["date"] for fact in kept if fact["kind"] in ("closed_on", "special_hours")}:
        on_day = [fact for fact in kept
                  if fact["kind"] in ("closed_on", "special_hours") and fact["value"]["date"] == day]
        if len({json.dumps(fact["value"], sort_keys=True) for fact in on_day}) > 1:
            for fact in on_day:
                kept.remove(fact)
                dropped.append((fact, f"different hours were given for {day}"))

    return kept, dropped


def hours_clash(a: dict, b: dict) -> bool:
    """Same weekday, overlapping dates, different times."""
    same_day = set(a["days"]) & set(b["days"])
    a_from, a_until = a.get("from", str(SEASON_START)), a.get("until", str(SEASON_END))
    b_from, b_until = b.get("from", str(SEASON_START)), b.get("until", str(SEASON_END))
    overlap = a_from <= b_until and b_from <= a_until
    return bool(same_day) and overlap and (a["opens"], a["closes"]) != (b["opens"], b["closes"])
