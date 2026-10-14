from datetime import date, timedelta
from itertools import permutations

from app.planning.checker import MarketInfo, hhmm
from app.planning.opening import open_window
from app.planning.plan import Settings, TripRequest
from app.planning.trains import Links, Train, pick_train
from app.reading.market_reader import TAGS
from app.trains.stations import STATIONS


def trip_days(request: TripRequest) -> list[date]:
    return [request.first_day + timedelta(days=n) for n in range((request.last_day - request.first_day).days + 1)]


def duration(minutes: int) -> str:
    return f"{minutes // 60} h {minutes % 60:02} min"


def settings_text(settings: Settings) -> str:
    return "; ".join([
        f"earliest train {hhmm(settings.earliest_train)}",
        f"at least {duration(settings.min_market_minutes)} at each market",
        f"at most {duration(settings.max_travel_minutes)} of travel a day",
        f"up to {settings.max_markets_per_day} markets a day",
        "day trips allowed" if settings.day_trips else "no day trips",
    ])


def trip_text(request: TripRequest) -> str:
    """The request: dates, start and end city, settings, wishes and picked tags."""
    days = trip_days(request)
    lines = [
        f"Dates: {request.first_day:%a %d %b} to {request.last_day:%a %d %b} ({len(days)} days)",
        f"Start city: {request.start_city or 'any'}",
        f"End city: {request.end_city or 'any'}",
        f"Settings: {settings_text(request.settings)}",
        f"Wishes: {request.wishes or 'none given'}",
    ]
    if request.tags:
        lines.append("Picked tags: " + "; ".join(f"{tag} ({TAGS.get(tag, 'no meaning known')})" for tag in request.tags))
    return "\n".join(lines)


def market_text(market_id: int, market: MarketInfo, days: list[date]) -> str:
    """One market: name, city, description, tags, details, and its hours on each day of the trip."""
    values = lambda kind: [fact["value"] for fact in market.facts if fact["kind"] == kind]
    hours = []
    for day in days:
        opening = open_window(market.facts, day)
        hours.append(f"{day:%d %b} " + (f"{hhmm(opening[0])}-{hhmm(opening[1])}" if isinstance(opening, tuple) else "closed"))
    lines = [f"Market {market_id}: {market.name} ({market.city})",
             f"Description: {market.description or 'none'}",
             f"Tags: {', '.join(v['tag'] for v in values('tag')) or 'none'}",
             f"Details: {'; '.join(v['text'] for v in values('detail')) or 'none'}",
             f"Open: {'; '.join(hours)}"]
    return "\n".join(lines)


def travel_text(links: Links, days: list[date], settings: Settings) -> str:
    """One line per pair of our cities: how long the best train takes with the traveller's
    settings (over the trip's days), or that it is over their limit."""
    lines = []
    for from_city, to_city in permutations(STATIONS, 2):
        trains = [pick_train(links, from_city, to_city, day, settings.earliest_train, settings.max_travel_minutes)
                  for day in days]
        found = [train for train in trains if isinstance(train, Train)]
        if not found:
            lines.append(f"{from_city} -> {to_city}: over your limit (no train within your settings)")
            continue
        times = sorted(train.arrive - train.depart for train in found)
        took = duration(times[0]) if times[0] == times[-1] else f"{duration(times[0])} to {duration(times[-1])}"
        via = sorted({train.via for train in found if train.via})
        line = f"{from_city} -> {to_city}: {took}" + (f", via {', '.join(via)}" if via else "")
        missing = [day for day, train in zip(days, trains) if not isinstance(train, Train)]
        if missing:
            line += f"; no train within your settings on {', '.join(f'{d:%d %b}' for d in missing)}"
        lines.append(line)
    return "\n".join(lines)
