import time
from dataclasses import replace
from pathlib import Path
from urllib.parse import urljoin, urlparse

import httpx
from protego import Protego

from app.fetcher.result import FetchResult
from app.fetcher.robots import get_robots_txt, make_client, robots_url
from app.fetcher.visit_log import VisitLog, fingerprint
from app.rules.engine import BOT_NAME, FETCHES_PAGES, can, site_of
from app.rules.purposes import Purpose
from app.rules.site_review import REVIEWS_DIR, load_review

# Seconds between requests to the same site, unless robots.txt asks for longer.
DEFAULT_DELAY = 5.0

MAX_BYTES = 10 * 1024 * 1024  # 10 MB
MAX_REDIRECTS = 5
ACCEPTED_TYPES = {"text/html", "application/xhtml+xml", "application/pdf"}


class SafeFetcher:
    """The only path to the web. Asks the rules engine before every download."""

    def __init__(self, client: httpx.Client | None = None, reviews_dir: Path = REVIEWS_DIR,
                 log: VisitLog | None = None, clock=time.monotonic, sleep=time.sleep):
        self.client = client or make_client()
        self.reviews_dir = reviews_dir
        self.log = log or VisitLog()
        self.robots_cache: dict[str, str | None] = {}  # robots.txt per site, downloaded once
        self.clock = clock
        self.sleep = sleep
        self.last_visit: dict[str, float] = {}  # when we last requested anything from each site

    def fetch(self, url: str, purpose: Purpose, redirects_left: int = MAX_REDIRECTS) -> FetchResult:
        """Download a page for a purpose, only if the rules engine says yes. Logs every attempt."""
        if purpose not in FETCHES_PAGES:
            raise ValueError(f"{purpose} does not download pages")

        result, next_url = self.fetch_once(url, purpose)
        if next_url is not None and redirects_left == 0:
            result, next_url = replace(result, problem="Too many redirects"), None
        self.log.record(result)

        if next_url is not None:
            return self.fetch(next_url, purpose, redirects_left - 1)  # a brand-new request
        return result

    def fetch_once(self, url: str, purpose: Purpose) -> tuple[FetchResult, str | None]:
        """One request: ask the engine, then download. Also returns the redirect address, if any."""
        robots_txt = self.robots_for(url)
        review = load_review(site_of(url), self.reviews_dir)
        decision = can(url, purpose, review, robots_txt)
        if not decision.allowed:
            return FetchResult(decision, url, purpose), None

        self.wait_turn(url)
        try:
            with self.client.stream("GET", url) as response:
                status = response.status_code
                next_url = urljoin(url, response.headers["location"]) if response.is_redirect else None
                content, problem = (None, None)
                if next_url is None and status == 200:
                    content, problem = read_limited(response)
        except httpx.HTTPError:
            return FetchResult(decision, url, purpose, problem="The site did not answer"), None

        if next_url is not None:
            return FetchResult(decision, url, purpose, status, problem=f"Redirected to {next_url}"), next_url

        page_hash = fingerprint(content) if content is not None else None
        return FetchResult(decision, url, purpose, status, content, problem, page_hash), None

    def robots_for(self, url: str) -> str | None:
        """The robots.txt for a page's site: downloaded on first use, then remembered."""
        site = urlparse(url).netloc
        if site not in self.robots_cache:
            # Reading robots.txt is always allowed, but it is still asked and logged like any download.
            address = robots_url(url)
            decision = can(address, Purpose.READ_TERMS)
            problem, page_hash = None, None
            if decision.allowed:
                self.wait_turn(url)
                robots_txt = get_robots_txt(url, self.client)
                self.robots_cache[site] = robots_txt
                if robots_txt is None:
                    problem = "robots.txt could not be fetched"
                elif robots_txt == "":
                    problem = "No robots.txt"
                else:
                    page_hash = fingerprint(robots_txt.encode("utf-8"))
            self.log.record(FetchResult(decision, address, Purpose.READ_TERMS,
                                        problem=problem, fingerprint=page_hash))
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
