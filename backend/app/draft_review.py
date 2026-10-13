import sys
from datetime import date
from pathlib import Path

from app.fetcher.safe_fetcher import SafeFetcher
from app.reading.clean import clean_html
from app.fetcher.robots import robots_url
from app.reading.review_writer import write_blocked, write_draft
from app.reading.terms_finder import find_terms_pages
from app.reading.terms_reader import DraftFailed, TermsPage, draft_review
from app.rules.decision import Basis
from app.rules.engine import robots_note, site_of
from app.rules.purposes import Purpose
from app.rules.site_review import REVIEWS_DIR, review_path
from app.settings import TERMS_READER_MODEL


class DraftStopped(Exception):
    """Drafting stopped before calling the AI; the admin decides this site by hand."""


def draft_site_review(start_url: str, fetcher: SafeFetcher | None = None, client=None,
                      reviews_dir: Path = REVIEWS_DIR, today: date | None = None) -> Path:
    """Fetch a site's terms, have the AI draft its review, and save it for the admin to approve."""
    fetcher = fetcher or SafeFetcher()
    site = site_of(start_url)
    if review_path(site, reviews_dir).exists():
        raise DraftStopped(f"{site} already has a review; delete it first to re-draft")

    start = fetcher.fetch(start_url, Purpose.READ_TERMS)
    robots_txt = fetcher.robots_for(start_url)
    if blocked_by_robots(start, robots_txt):
        print(f"robots.txt blocks this site: {start.decision.reason}. Writing a link-only review.")
        return write_blocked(site, robots_url(start_url), start.decision.reason,
                             robots_note(start_url, robots_txt), reviews_dir, today)
    if start.content is None:
        raise DraftStopped(f"Start page could not be read: {why(start)}")
    links = find_terms_pages(clean_html(start.content, start.url), start.url)
    print(f"Terms pages found: {len(links)}")

    pages = []
    for url in links:
        print(f"Reading {url}")
        result = fetcher.fetch(url, Purpose.READ_TERMS)
        if result.content is None:
            raise DraftStopped(f"Terms page could not be read ({url}): {why(result)}")
        if result.content.startswith(b"%PDF"):
            raise DraftStopped(f"Terms page is a PDF, which can't be read yet ({url})")
        pages.append(TermsPage(result.url, clean_html(result.content, result.url).text))

    print("Asking the AI to draft the review")
    draft = draft_review(pages, client=client)
    terms_urls = [page.url for page in pages] or [start.url]
    robots = robots_note(start.url, fetcher.robots_for(start.url))
    return write_draft(site, draft, terms_urls, TERMS_READER_MODEL, reviews_dir, today, robots)


def blocked_by_robots(result, robots_txt: str | None) -> bool:
    """True if robots.txt was read and blocks the page; an unreachable robots.txt is only temporary."""
    refused = not result.decision.allowed and result.decision.basis == Basis.ROBOTS_TXT
    return refused and robots_txt is not None


def why(result) -> str:
    """The clearest reason a fetch gave no page."""
    if not result.decision.allowed:
        return result.decision.reason
    return result.problem or f"the site answered {result.status_code}"


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python -m app.draft_review <start page address>")
        sys.exit(2)
    try:
        path = draft_site_review(sys.argv[1])
    except (DraftStopped, DraftFailed) as stopped:
        print(f"Stopped: {stopped}")
        sys.exit(1)
    print(f"Draft written: {path}\nRead it, then approve it by committing it (or delete it to reject).")
