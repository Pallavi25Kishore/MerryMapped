from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class Settings:
    """How the traveller likes their days. The website shows these with the defaults below,
    and the user can change them; the checker holds every plan to them.
    Times are minutes after midnight, durations are minutes."""
    earliest_train: int = 8 * 60  # no train leaves before 08:00
    min_market_minutes: int = 120  # at least 2 hours at each market, while it is open
    max_travel_minutes: int = 6 * 60  # at most 6 hours of train travel in one day
    max_markets_per_day: int = 2  # in the same city
    day_trips: bool = False  # on only when the user asks for day trips


@dataclass(frozen=True)
class Travel:
    """Going from one city to another on a day. The planner picks the cities; code picks the
    train from the train_links table."""
    from_city: str
    to_city: str


@dataclass(frozen=True)
class Visit:
    """A market visited on a day, with the planner's short reason for choosing it (from the
    market's checked details and tags, linked to the user's wishes)."""
    market_id: int
    why: str = ""


@dataclass(frozen=True)
class Day:
    """One day of the trip: the travel (if any), the markets visited (by id), and the city
    slept in that night. With travel, the markets are in the city travelled to. A day trip
    (only when Settings.day_trips is on) also has travel_back, from that city to sleep_in."""
    day: date
    travel: Travel | None
    visits: tuple[Visit, ...]
    sleep_in: str
    travel_back: Travel | None = None


@dataclass(frozen=True)
class Plan:
    """An itinerary: one Day per date of the trip, in order."""
    days: tuple[Day, ...]


@dataclass(frozen=True)
class TripRequest:
    """What the user asked for: the dates, their settings, their wishes in their own words,
    the tags found in their wishes, and optionally where the trip must start and end."""
    first_day: date
    last_day: date
    settings: Settings = Settings()
    wishes: str = ""
    tags: tuple[str, ...] = ()
    start_city: str | None = None  # the first day starts here (e.g. where the user arrives)
    end_city: str | None = None  # the last night is spent here
