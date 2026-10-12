import time
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urljoin, urlparse

import httpx
from protego import Protego

from app.fetcher.robots import get_robots_txt, make_client, robots_url
from app.rules.decision import Decision
from app.rules.engine import BOT_NAME, FETCHES_PAGES, can, site_of
from app.rules.purposes import Purpose
from app.rules.site_review import REVIEWS_DIR, load_review

# Seconds between requests to the same site, unless robots.txt asks for longer.
DEFAULT_DELAY = 5.0

MAX_BYTES = 10 * 1024 * 1024  # 10 MB
MAX_REDIRECTS = 5
ACCEPTED_TYPES = {"text/html", "application/xhtml+xml", "application/pdf"}


@dataclass(frozen=True)
class FetchResult:
    """What a fetch hands back: the engine's slip, and the page if it was downloaded."""

    decision: Decision
    url: str                        # the address this result is for (after any redirects)
    status_code: int | None = None  # the site's answer (200, 404, ...); None if never downloaded
    content: bytes | None = None    # the page, in memory only; None unless it passed every check
    problem: str | None = None      # why there is no page, even though the engine said yes


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

    def fetch(self, url: str, purpose: Purpose, redirects_left: int = MAX_REDIRECTS) -> FetchResult:
        """Download a page for a purpose, only if the rules engine says yes."""
        if purpose not in FETCHES_PAGES:
            raise ValueError(f"{purpose} does not download pages")

        robots_txt = self.robots_for(url)
        review = load_review(site_of(url), self.reviews_dir)
        decision = can(url, purpose, review, robots_txt)
        if not decision.allowed:
            return FetchResult(decision, url)

        self.wait_turn(url)
        try:
            with self.client.stream("GET", url) as response:
                status = response.status_code
                next_url = urljoin(url, response.headers["location"]) if response.is_redirect else None
                content, problem = (None, None)
                if next_url is None and status == 200:
                    content, problem = read_limited(response)
        except httpx.HTTPError:
            return FetchResult(decision, url, problem="The site did not answer")

        if next_url is not None:
            if redirects_left == 0:
                return FetchResult(decision, url, status, problem="Too many redirects")
            return self.fetch(next_url, purpose, redirects_left - 1)  # a brand-new request

        return FetchResult(decision, url, status, content, problem)

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


def read_limited(response: httpx.Response) -> tuple[bytes | None, str | None]:
    """Read a page only if it is a web page or PDF, stopping if it grows past 10 MB."""
    content_type = response.headers.get("content-type", "").split(";")[0].strip().lower()
    if content_type not in ACCEPTED_TYPES:
        return None, f"Not a web page or PDF ({content_type or 'unknown type'})"

    declared = response.headers.get("content-length", "")
    if declared.isdigit() and int(declared) > MAX_BYTES:
        return None, "Larger than 10 MB"

    chunks, size = [], 0
    for chunk in response.iter_bytes():
        size += len(chunk)
        if size > MAX_BYTES:
            return None, "Larger than 10 MB"
        chunks.append(chunk)
    return b"".join(chunks), None
