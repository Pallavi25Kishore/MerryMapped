import os
import secrets
from dataclasses import asdict, fields
from datetime import date, datetime, timezone
from functools import cache

from fastapi import APIRouter, Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.connection import make_engine
from app.db.models import Fact, Market, Trip, create_tables
from app.planning.checker import load_markets
from app.planning.itinerary import build_itinerary
from app.planning.plan import Settings, TripRequest
from app.planning.planner import plan_trip, trip_days
from app.planning.trains import load_links
from app.planning.understand import FIRST_DAY, LAST_DAY, SETTING_RANGES, Form, merge, understand
from app.planning.wishes import review_wishes
from app.rules.engine import site_of
from app.rules.site_review import load_review
from app.trains.stations import STATIONS

app = FastAPI(title="MerryMapped")


def require_access(x_access_code: str = Header("")) -> None:
    """Every /api request must carry the access code from backend/.env in the X-Access-Code
    header. With no code set, everything is refused rather than left open."""
    code = os.environ.get("ACCESS_CODE", "")
    if not code or not secrets.compare_digest(x_access_code.encode(), code.encode()):
        raise HTTPException(status_code=401, detail="Not allowed: a valid access code is needed.")


api = APIRouter(prefix="/api", dependencies=[Depends(require_access)])


@cache
def engine():
    """The database engine, made on first use; new tables (such as trips) are created then."""
    made = make_engine()
    create_tables(made)
    return made


def get_session():
    with Session(engine()) as session:
        yield session


def request_json(request: TripRequest) -> dict:
    return {"first_day": request.first_day.isoformat(), "last_day": request.last_day.isoformat(),
            "start_city": request.start_city, "end_city": request.end_city,
            "settings": asdict(request.settings),
            "wishes": [wish for wish in request.wishes.split("; ") if wish], "tags": list(request.tags)}


@app.get("/health")
def health():
    """Report that the backend is running."""
    return {"status": "ok"}


@api.get("/options")
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


@api.post("/understand")
def understand_form(form: FormIn):
    """The confirm screen: the request read from the form and the typed text (null until the dates
    are usable), notes on what was changed or is missing, and what MerryMapped cannot do."""
    understood = understand(Form(form.text, form.first_day, form.last_day, form.start_city, form.end_city,
                                 form.settings.model_dump(exclude_none=True)))
    return {"request": understood.request and request_json(understood.request),
            "notes": understood.notes, "not_covered": understood.not_covered}


COULD_NOT_PLAN = "The planner could not make a plan; please try again."


class PlanIn(BaseModel):
    """The request as confirmed on the confirm screen."""
    first_day: date
    last_day: date
    start_city: str | None = None
    end_city: str | None = None
    settings: SettingsIn = SettingsIn()
    wishes: list[str] = Field([], max_length=20)
    tags: list[str] = []
    not_covered: list[str] = Field([], max_length=20)


@api.post("/plan")
def plan(confirmed: PlanIn, session: Session = Depends(get_session)):
    """Plan the confirmed trip: check it again, plan and check (repairing what cannot be fixed),
    review the wishes, then save the trip and return it with its itinerary."""
    form = Form("", confirmed.first_day, confirmed.last_day, confirmed.start_city, confirmed.end_city,
                confirmed.settings.model_dump(exclude_none=True))
    read = {"first_day": None, "last_day": None, "start_city": None, "end_city": None,
            "tags": confirmed.tags, "wishes": confirmed.wishes, "not_covered": confirmed.not_covered}
    understood = merge(form, read)
    if understood.request is None or understood.notes:
        raise HTTPException(status_code=422, detail=understood.notes)
    request = understood.request

    markets = load_markets(session)
    planned = plan_trip(request, markets, load_links(session, trip_days(request)))
    fixed = planned.repaired
    if planned.plan is None:
        raise HTTPException(status_code=502, detail=COULD_NOT_PLAN)
    final_plan, result = (fixed.plan, fixed.result) if fixed else (planned.plan, planned.result)
    days = tuple(f"{day.day:%a %d %b}:" for day in final_plan.days)
    if any(not problem.startswith(days) for problem in result.problems):  # such as wrong dates: not one day's problem
        raise HTTPException(status_code=502, detail=COULD_NOT_PLAN)
    notes = review_wishes(request, final_plan, markets, understood.not_covered)
    itinerary = build_itinerary(final_plan, result, markets, fixed.removed if fixed else [],
                                fixed.day_tips if fixed else {}, notes)

    trip = Trip(id=secrets.token_urlsafe(12), created_at=datetime.now(timezone.utc).replace(tzinfo=None),  # UTC
                request=request_json(request), itinerary=itinerary)
    session.add(trip)
    session.commit()
    return trip_json(trip)


def trip_json(trip: Trip) -> dict:
    return {"trip_id": trip.id, "created_at": trip.created_at.isoformat(), "request": trip.request,
            "itinerary": trip.itinerary}


def find_trip(session: Session, trip_id: str) -> Trip:
    trip = session.get(Trip, trip_id)
    if trip is None:
        raise HTTPException(status_code=404, detail="No trip with this id.")
    return trip


@api.get("/trips")
def my_trips(session: Session = Depends(get_session)):
    """My trips, newest first: each trip's id, when it was planned, its dates and the cities slept in."""
    trips = session.scalars(select(Trip).order_by(Trip.created_at.desc()))
    return [{"trip_id": trip.id, "created_at": trip.created_at.isoformat(),
             "first_day": trip.request["first_day"], "last_day": trip.request["last_day"],
             "cities": list(dict.fromkeys(day["sleep_in"] for day in trip.itinerary["days"]))} for trip in trips]


@api.get("/trips/{trip_id}")
def open_trip(trip_id: str, session: Session = Depends(get_session)):
    """A saved trip, as /plan returned it."""
    return trip_json(find_trip(session, trip_id))


@api.delete("/trips/{trip_id}")
def delete_trip(trip_id: str, session: Session = Depends(get_session)):
    """Delete a trip completely and return a receipt. Nothing of the trip is kept, not even the receipt."""
    trip = find_trip(session, trip_id)
    planned = trip.created_at.isoformat()
    session.delete(trip)
    session.commit()
    return {"trip_id": trip_id, "planned_at": planned,
            "deleted_at": datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),  # UTC
            "deleted": "the trip's request and itinerary", "kept": "nothing"}



@api.get("/markets/{market_id}/sources")
def market_sources(market_id: int, session: Session = Depends(get_session)):
    """"Why can I see this?": every fact we show for a market with its proof (the page, the quote
    and its English, the date checked, and whether it was checked from the page or entered by
    hand), and the legal decision for each site the facts come from (the approved site review)."""
    market = session.get(Market, market_id)
    if market is None:
        raise HTTPException(status_code=404, detail="No market with this id.")
    facts = session.scalars(select(Fact).where(Fact.market_id == market_id).order_by(Fact.id)).all()
    sites = dict.fromkeys([site_of(market.website)] + [site_of(fact.source_url) for fact in facts])
    legal = {}
    for site in sites:
        review = load_review(site)
        legal[site] = review and {
            "reviewed_on": review.reviewed_on.isoformat(), "terms_pages": [str(url) for url in review.terms_urls],
            "automated_access": review.automated_access.model_dump(),
            "purposes": {name: answer.model_dump() for name, answer in review.purposes if answer}}
    return {"market_id": market.id, "name": market.name, "website": market.website,
            "facts": [{"kind": f.kind, "value": f.value, "page": f.source_url, "quote": f.evidence_quote,
                       "english": f.evidence_translation, "checked_on": f.checked_on.isoformat(),
                       "status": f.status} for f in facts],
            "legal": legal}


app.include_router(api)  # after every /api address is defined
