from datetime import date

WEEKDAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]


def minutes(hhmm: str) -> int:
    hours, mins = hhmm.split(":")
    return int(hours) * 60 + int(mins)


def window(value: dict) -> tuple[int, int]:
    """(opens, closes) in minutes after midnight; a closing time at or before the opening time
    is the next morning (e.g. 18:00 to 01:00)."""
    opens, closes = minutes(value["opens"]), minutes(value["closes"])
    return opens, closes + 24 * 60 if closes <= opens else closes


def open_window(facts: list[dict], day: date) -> tuple[int, int] | str:
    """When the market is open on this day, from its facts (each a dict with "kind" and "value"):
    an (opens, closes) window in minutes after midnight, or a sentence saying why it is closed."""
    def of_kind(kind):
        return [fact["value"] for fact in facts if fact["kind"] == kind]

    opening, closing = of_kind("opening_date"), of_kind("closing_date")
    if not opening or not closing:
        return "its season dates are not known"
    first, last = date.fromisoformat(opening[0]["date"]), date.fromisoformat(closing[0]["date"])
    if not first <= day <= last:
        return f"it is only open from {first:%d %b} to {last:%d %b}"

    for special in of_kind("special_hours"):
        if special["date"] == day.isoformat():
            return window(special)
    if any(closed["date"] == day.isoformat() for closed in of_kind("closed_on")):
        return f"it is closed on {day:%d %b}"

    weekday = WEEKDAYS[day.weekday()]
    matching = [hours for hours in of_kind("hours")
                if weekday in hours["days"]
                and hours.get("from", "0000") <= day.isoformat() <= hours.get("until", "9999")]
    if not matching:
        return f"no opening hours are known for {day:%A}s"
    # Hours limited to a date range are more specific than hours for the whole season.
    matching.sort(key=lambda hours: "from" not in hours and "until" not in hours)
    return window(matching[0])
