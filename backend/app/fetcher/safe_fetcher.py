from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

import httpx

from app.fetcher.robots import get_robots_txt, make_client, robots_url
from app.rules.decision import Decision
from app.rules.engine import FETCHES_PAGES, can, site_of
from app.rules.purposes import Purpose
from app.rules.site_review import REVIEWS_DIR, load_review


@dataclass(frozen=True)
class FetchResult:
    """What a fetch hands back: the engine's slip, and the page if it was downloaded."""

    decision: Decision
    status_code: int | None = None  # the site's answer (200, 404, ...); None if never downloaded
    content: bytes | None = None    # the page, in memory only; None unless the site answered 200


class SafeFetcher:
    """The only path to the web. Asks the rules engine before every download."""

    def __init__(self, client: httpx.Client | None = None, reviews_dir: Path = REVIEWS_DIR):
        self.client = client or make_client()
        self.reviews_dir = reviews_dir
        self.robots_cache: dict[str, str | None] = {}  # robots.txt per site, downloaded once

    def fetch(self, url: str, purpose: Purpose) -> FetchResult:
        """Download a page for a purpose, only if the rules engine says yes."""
        if purpose not in FETCHES_PAGES:
            raise ValueError(f"{purpose} does not download pages")

        robots_txt = self.robots_for(url)
        review = load_review(site_of(url), self.reviews_dir)
        decision = can(url, purpose, review, robots_txt)
        if not decision.allowed:
            return FetchResult(decision)

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
                self.robots_cache[site] = get_robots_txt(url, self.client)
        return self.robots_cache.get(site)
