from dataclasses import asdict, fields
from datetime import date

from fastapi import FastAPI
from pydantic import BaseModel, Field

from app.planning.plan import Settings
from app.planning.understand import FIRST_DAY, LAST_DAY, SETTING_RANGES, Form, understand
from app.trains.stations import STATIONS

app = FastAPI(title="MerryMapped")


@app.get("/health")
def health():
    """Report that the backend is running."""
    return {"status": "ok"}


@app.get("/api/options")
def options():
    """What the trip form needs: the dates a trip can use, our cities, and each setting's default
    and allowed range (times in minutes after midnight, durations in minutes)."""
    settings = {}
    for setting in fields(Settings):
        settings[setting.name] = {"default": setting.default}
        if setting.name in SETTING_RANGES:
            settings[setting.name]["low"], settings[setting.name]["high"] = SETTING_RANGES[setting.name]
    return {"first_day": FIRST_DAY.isoformat(), "last_day": LAST_DAY.isoformat(),
            "cities": list(STATIONS), "settings": settings}


class SettingsIn(BaseModel):
    """The settings the traveller changed on the form; the rest stay empty."""
    earliest_train: int | None = None
    min_market_minutes: int | None = None
    max_travel_minutes: int | None = None
    max_markets_per_day: int | None = None
    day_trips: bool | None = None


class FormIn(BaseModel):
    """The trip form as the website sends it: every field optional, plus what was typed."""
    text: str = Field("", max_length=2000)  # enough for any trip wish; keeps the AI cost small
    first_day: date | None = None
    last_day: date | None = None
    start_city: str | None = None
    end_city: str | None = None
    settings: SettingsIn = SettingsIn()


@app.post("/api/understand")
def understand_form(form: FormIn):
    """The confirm screen: the request read from the form and the typed text (null until the dates
    are usable), notes on what was changed or is missing, and what MerryMapped cannot do."""
    understood = understand(Form(form.text, form.first_day, form.last_day, form.start_city, form.end_city,
                                 form.settings.model_dump(exclude_none=True)))
    request = understood.request
    return {
        "request": request and {
            "first_day": request.first_day.isoformat(), "last_day": request.last_day.isoformat(),
            "start_city": request.start_city, "end_city": request.end_city,
            "settings": asdict(request.settings),
            "wishes": [wish for wish in request.wishes.split("; ") if wish],
            "tags": list(request.tags),
        },
        "notes": understood.notes,
        "not_covered": understood.not_covered,
    }
