import httpx
import pytest

from app.fetcher.robots import make_client
from app.fetcher.safe_fetcher import SafeFetcher
from app.rules.decision import Basis
from app.rules.purposes import Purpose

PAGE = "https://weihnachtsmarkt-koeln.de/markt/termine"
PAGE_HTML = b"<html><body>Opening: 20 Nov to 23 Dec</body></html>"

REVIEW_ALLOWING_FACTS = """\
reviewed_on: 2026-10-20
terms_urls:
  - https://weihnachtsmarkt-koeln.de/nutzungsbedingungen
automated_access:
  answer: allow
  because: "No clause restricts bots"
purposes:
  collect_facts:
    answer: allow
    because: "No clause restricts collecting facts"
"""


class PretendSite:
    """A pretend website that records every address requested."""

    def __init__(self, robots_status=404, robots_text="", page_status=200, unreachable=False):
        self.robots_status = robots_status
        self.robots_text = robots_text
        self.page_status = page_status
        self.unreachable = unreachable
        self.requested = []

    def answer(self, request):
        self.requested.append(request.url.path)
        if request.url.path == "/robots.txt":
            return httpx.Response(self.robots_status, text=self.robots_text)
        if self.unreachable:
            raise httpx.ConnectError("site unreachable")
        return httpx.Response(self.page_status, content=PAGE_HTML)


class PretendClock:
    """A pretend stopwatch: waiting just writes down how long and jumps forward."""

    def __init__(self):
        self.now = 0.0
        self.waits = []

    def time(self):
        return self.now

    def sleep(self, seconds):
        self.waits.append(seconds)
        self.now += seconds


def make_fetcher(site, tmp_path, review=None, clock=None):
    """A fetcher wired to a pretend site and clock, with review files in a temporary folder."""
    if review is not None:
        (tmp_path / "weihnachtsmarkt-koeln.de.yaml").write_text(review, encoding="utf-8")
    client = make_client(transport=httpx.MockTransport(site.answer))
    clock = clock or PretendClock()
    return SafeFetcher(client=client, reviews_dir=tmp_path, clock=clock.time, sleep=clock.sleep)


def test_allowed_page_is_downloaded(tmp_path):
    site = PretendSite()
    result = make_fetcher(site, tmp_path, REVIEW_ALLOWING_FACTS).fetch(PAGE, Purpose.COLLECT_FACTS)

    assert result.decision.allowed is True
    assert result.status_code == 200
    assert result.content == PAGE_HTML


def test_unreviewed_site_page_is_never_requested(tmp_path):
    site = PretendSite()
    result = make_fetcher(site, tmp_path).fetch(PAGE, Purpose.COLLECT_FACTS)

    assert result.decision.allowed is False
    assert result.content is None
    assert site.requested == ["/robots.txt"]


def test_robots_block_page_is_never_requested(tmp_path):
    site = PretendSite(robots_status=200, robots_text="User-agent: *\nDisallow: /markt\n")
    result = make_fetcher(site, tmp_path, REVIEW_ALLOWING_FACTS).fetch(PAGE, Purpose.COLLECT_FACTS)

    assert result.decision.allowed is False
    assert result.decision.basis == Basis.ROBOTS_TXT
    assert site.requested == ["/robots.txt"]


def test_terms_can_be_read_on_a_new_site(tmp_path):
    site = PretendSite()
    terms = "https://weihnachtsmarkt-koeln.de/nutzungsbedingungen"
    result = make_fetcher(site, tmp_path).fetch(terms, Purpose.READ_TERMS)

    assert result.decision.allowed is True
    assert result.status_code == 200


def test_robots_txt_is_downloaded_once_per_site(tmp_path):
    site = PretendSite()
    fetcher = make_fetcher(site, tmp_path, REVIEW_ALLOWING_FACTS)
    fetcher.fetch(PAGE, Purpose.COLLECT_FACTS)
    fetcher.fetch("https://weihnachtsmarkt-koeln.de/markt/anfahrt", Purpose.COLLECT_FACTS)

    assert site.requested.count("/robots.txt") == 1


def test_links_do_not_download(tmp_path):
    with pytest.raises(ValueError):
        make_fetcher(PretendSite(), tmp_path).fetch(PAGE, Purpose.SHOW_LINK)


def test_page_not_found(tmp_path):
    site = PretendSite(page_status=404)
    result = make_fetcher(site, tmp_path, REVIEW_ALLOWING_FACTS).fetch(PAGE, Purpose.COLLECT_FACTS)

    assert result.decision.allowed is True
    assert result.status_code == 404
    assert result.content is None


def test_site_does_not_answer(tmp_path):
    site = PretendSite(unreachable=True)
    result = make_fetcher(site, tmp_path, REVIEW_ALLOWING_FACTS).fetch(PAGE, Purpose.COLLECT_FACTS)

    assert result.decision.allowed is True
    assert result.status_code is None
    assert result.content is None


# Speed limit

def test_waits_the_default_delay_between_requests(tmp_path):
    clock = PretendClock()
    make_fetcher(PretendSite(), tmp_path, REVIEW_ALLOWING_FACTS, clock).fetch(PAGE, Purpose.COLLECT_FACTS)

    assert clock.waits == [5.0]  # nothing before robots.txt (first visit), 5 s before the page


def test_follows_a_longer_crawl_delay(tmp_path):
    clock = PretendClock()
    site = PretendSite(robots_status=200, robots_text="User-agent: *\nCrawl-delay: 10\n")
    make_fetcher(site, tmp_path, REVIEW_ALLOWING_FACTS, clock).fetch(PAGE, Purpose.COLLECT_FACTS)

    assert clock.waits == [10.0]


def test_keeps_the_default_when_crawl_delay_is_shorter(tmp_path):
    clock = PretendClock()
    site = PretendSite(robots_status=200, robots_text="User-agent: *\nCrawl-delay: 1\n")
    make_fetcher(site, tmp_path, REVIEW_ALLOWING_FACTS, clock).fetch(PAGE, Purpose.COLLECT_FACTS)

    assert clock.waits == [5.0]


def test_no_extra_wait_when_time_has_passed(tmp_path):
    clock = PretendClock()
    fetcher = make_fetcher(PretendSite(), tmp_path, REVIEW_ALLOWING_FACTS, clock)
    fetcher.fetch(PAGE, Purpose.COLLECT_FACTS)
    clock.now += 60
    fetcher.fetch("https://weihnachtsmarkt-koeln.de/markt/anfahrt", Purpose.COLLECT_FACTS)

    assert clock.waits == [5.0]  # only the first page waited


def test_different_sites_do_not_wait_for_each_other(tmp_path):
    clock = PretendClock()
    fetcher = make_fetcher(PretendSite(), tmp_path, clock=clock)
    fetcher.fetch("https://weihnachtsmarkt-koeln.de/agb", Purpose.READ_TERMS)
    fetcher.fetch("https://christkindlesmarkt.de/agb", Purpose.READ_TERMS)

    # Each site: robots.txt with no wait (first visit), then 5 s before its terms page.
    assert clock.waits == [5.0, 5.0]


def test_refused_page_costs_no_wait(tmp_path):
    clock = PretendClock()
    make_fetcher(PretendSite(), tmp_path, clock=clock).fetch(PAGE, Purpose.COLLECT_FACTS)

    assert clock.waits == []
