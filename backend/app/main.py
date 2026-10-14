from dataclasses import fields

from fastapi import FastAPI

from app.planning.plan import Settings
from app.planning.understand import FIRST_DAY, LAST_DAY, SETTING_RANGES
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
