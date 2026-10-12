import time
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

import httpx
from protego import Protego

from app.fetcher.robots import get_robots_txt, make_client, robots_url
from app.rules.decision import Decision
from app.rules.engine import BOT_NAME, FETCHES_PAGES, can, site_of
from app.rules.purposes import Purpose
from app.rules.site_review import REVIEWS_DIR, load_review

# Seconds between requests to the same site, unless robots.txt asks for longer.
DEFAULT_DELAY = 5.0


@dataclass(frozen=True)
class FetchResult:
    """What a fetch hands back: the engine's slip, and the page if it was downloaded."""

    decision: Decision
    status_code: int | None = None  # the site's answer (200, 404, ...); None if never downloaded
    content: bytes | None = None    # the page, in memory only; None unless the site answered 200


class SafeFetcher:
    """The only path to the web. Asks the rules engine before every download."""

    def __init__(self, client: httpx.Client | None = None, reviews_dir: Path = REVIEWS_DIR,
                 clock=time.monotonic, sleep=time.sleep):
        self.client = client or make_client()
        self.reviews_dir = reviews_dir
        self.robots_cache: dict[str, str | None] = {}  # robots.txt per site, downloaded once
        self.clock = clock
        self.sleep = sleep
        self.last_visit: dict[str, float] = {}  # when we last requested anything from each site

    def fetch(self, url: str, purpose: Purpose) -> FetchResult:
        """Download a page for a purpose, only if the rules engine says yes."""
        if purpose not in FETCHES_PAGES:
            raise ValueError(f"{purpose} does not download pages")

        robots_txt = self.robots_for(url)
        review = load_review(site_of(url), self.reviews_dir)
        decision = can(url, purpose, review, robots_txt)
        if not decision.allowed:
            return FetchResult(decision)

        self.wait_turn(url)
        try:
            response = self.client.get(url)
        except httpx.HTTPError:
            return FetchResult(decision)  # allowed, but the site didn't answer

        content = response.content if response.status_code == 200 else None
        return FetchResult(decision, response.status_code, content)

    def robots_for(self, url: str) -> str | None:
        """The robots.txt for a page's site: downloaded on first use, then remembered."""
        site = urlparse(url).netloc
        if site not in self.robots_cache:
            # Reading robots.txt is always allowed, but it is still asked like any download.
            if can(robots_url(url), Purpose.READ_TERMS).allowed:
                self.wait_turn(url)
                self.robots_cache[site] = get_robots_txt(url, self.client)
        return self.robots_cache.get(site)

    def wait_turn(self, url: str) -> None:
        """Wait until enough time has passed since our last request to this site."""
        site = urlparse(url).netloc
        if site in self.last_visit:
            waited = self.clock() - self.last_visit[site]
            delay = self.delay_for(site)
            if waited < delay:
                self.sleep(delay - waited)
        self.last_visit[site] = self.clock()

    def delay_for(self, site: str) -> float:
        """Our default delay, or the site's Crawl-delay if it asks for longer."""
        robots_txt = self.robots_cache.get(site)
        crawl_delay = Protego.parse(robots_txt).crawl_delay(BOT_NAME) if robots_txt else None
        return max(DEFAULT_DELAY, crawl_delay or 0)
