import json

import httpx
import pytest

from app.fetcher.robots import make_client
from app.fetcher.safe_fetcher import MAX_BYTES, SafeFetcher
from app.fetcher.visit_log import VisitLog, fingerprint
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

    def __init__(self, robots_status=404, robots_text="", page_status=200, unreachable=False,
                 content_type="text/html", body=PAGE_HTML, headers=None, redirects=None):
        self.robots_status = robots_status
        self.robots_text = robots_text
        self.page_status = page_status
        self.unreachable = unreachable
        self.content_type = content_type
        self.body = body
        self.headers = headers or {}
        self.redirects = redirects or {}  # path -> the address it has "moved" to
        self.requested = []               # paths requested
        self.requested_urls = []          # full addresses requested

    def answer(self, request):
        self.requested.append(request.url.path)
        self.requested_urls.append(str(request.url))
        if request.url.path == "/robots.txt":
            return httpx.Response(self.robots_status, text=self.robots_text)
        if self.unreachable:
            raise httpx.ConnectError("site unreachable")
        if request.url.path in self.redirects:
            return httpx.Response(301, headers={"Location": self.redirects[request.url.path]})
        headers = {"Content-Type": self.content_type, **self.headers}
        return httpx.Response(self.page_status, headers=headers, content=self.body)


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
    log = VisitLog(tmp_path / "visits.jsonl")  # never the real log
    return SafeFetcher(client=client, reviews_dir=tmp_path, log=log,
                       clock=clock.time, sleep=clock.sleep)


def read_log(tmp_path):
    lines = (tmp_path / "visits.jsonl").read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines]


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
    assert result.problem == "The site did not answer"


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


# Redirects: every new address gets a fresh engine check

def test_redirect_on_the_same_site_is_followed(tmp_path):
    site = PretendSite(redirects={"/markt/alt": PAGE})
    fetcher = make_fetcher(site, tmp_path, REVIEW_ALLOWING_FACTS)
    result = fetcher.fetch("https://weihnachtsmarkt-koeln.de/markt/alt", Purpose.COLLECT_FACTS)

    assert result.url == PAGE
    assert result.content == PAGE_HTML


def test_redirect_to_a_blocked_page_is_never_requested(tmp_path):
    site = PretendSite(
        robots_status=200,
        robots_text="User-agent: *\nDisallow: /markt/intern\n",
        redirects={"/markt/alt": "https://weihnachtsmarkt-koeln.de/markt/intern"},
    )
    fetcher = make_fetcher(site, tmp_path, REVIEW_ALLOWING_FACTS)
    result = fetcher.fetch("https://weihnachtsmarkt-koeln.de/markt/alt", Purpose.COLLECT_FACTS)

    assert result.decision.allowed is False
    assert result.decision.basis == Basis.ROBOTS_TXT
    assert "/markt/intern" not in site.requested


def test_redirect_to_another_site_needs_that_sites_review(tmp_path):
    site = PretendSite(redirects={"/markt/termine": "https://other-market.de/termine"})
    result = make_fetcher(site, tmp_path, REVIEW_ALLOWING_FACTS).fetch(PAGE, Purpose.COLLECT_FACTS)

    assert result.decision.allowed is False
    assert result.decision.basis == Basis.NOT_REVIEWED
    assert "https://other-market.de/robots.txt" in site.requested_urls
    assert "https://other-market.de/termine" not in site.requested_urls


def test_redirect_loop_stops(tmp_path):
    site = PretendSite(redirects={
        "/a": "https://weihnachtsmarkt-koeln.de/b",
        "/b": "https://weihnachtsmarkt-koeln.de/a",
    })
    fetcher = make_fetcher(site, tmp_path, REVIEW_ALLOWING_FACTS)
    result = fetcher.fetch("https://weihnachtsmarkt-koeln.de/a", Purpose.COLLECT_FACTS)

    assert result.content is None
    assert result.problem == "Too many redirects"


# Only web pages and PDFs, up to 10 MB

def test_image_is_refused(tmp_path):
    site = PretendSite(content_type="image/jpeg", body=b"\xff\xd8 pretend photo")
    result = make_fetcher(site, tmp_path, REVIEW_ALLOWING_FACTS).fetch(PAGE, Purpose.COLLECT_FACTS)

    assert result.content is None
    assert result.problem == "Not a web page or PDF (image/jpeg)"


def test_pdf_is_accepted(tmp_path):
    site = PretendSite(content_type="application/pdf", body=b"%PDF-1.7 pretend flyer")
    result = make_fetcher(site, tmp_path, REVIEW_ALLOWING_FACTS).fetch(PAGE, Purpose.COLLECT_FACTS)

    assert result.content == b"%PDF-1.7 pretend flyer"


def test_too_big_by_label_is_refused(tmp_path):
    site = PretendSite(headers={"Content-Length": str(MAX_BYTES + 1)})
    result = make_fetcher(site, tmp_path, REVIEW_ALLOWING_FACTS).fetch(PAGE, Purpose.COLLECT_FACTS)

    assert result.content is None
    assert result.problem == "Larger than 10 MB"


def test_too_big_without_label_stops_while_reading(tmp_path):
    one_mb = b"x" * (1024 * 1024)
    site = PretendSite(body=(one_mb for _ in range(11)))  # 11 MB in chunks, no size label
    result = make_fetcher(site, tmp_path, REVIEW_ALLOWING_FACTS).fetch(PAGE, Purpose.COLLECT_FACTS)

    assert result.content is None
    assert result.problem == "Larger than 10 MB"


# Fingerprint and visit log

def test_downloaded_page_has_its_fingerprint(tmp_path):
    result = make_fetcher(PretendSite(), tmp_path, REVIEW_ALLOWING_FACTS).fetch(PAGE, Purpose.COLLECT_FACTS)

    assert result.fingerprint == fingerprint(PAGE_HTML)


def test_refusal_is_logged(tmp_path):
    make_fetcher(PretendSite(), tmp_path).fetch(PAGE, Purpose.COLLECT_FACTS)

    robots_line, page_line = read_log(tmp_path)
    assert robots_line["url"] == "https://weihnachtsmarkt-koeln.de/robots.txt"
    assert robots_line["allowed"] is True
    assert robots_line["problem"] == "No robots.txt"
    assert page_line["url"] == PAGE
    assert page_line["allowed"] is False
    assert page_line["reason"] == "Nobody has reviewed this site's terms yet"
    assert page_line["status_code"] is None


def test_redirect_logs_each_hop(tmp_path):
    site = PretendSite(redirects={"/markt/alt": PAGE})
    make_fetcher(site, tmp_path, REVIEW_ALLOWING_FACTS).fetch(
        "https://weihnachtsmarkt-koeln.de/markt/alt", Purpose.COLLECT_FACTS)

    _, hop, final = read_log(tmp_path)
    assert hop["status_code"] == 301
    assert hop["problem"] == f"Redirected to {PAGE}"
    assert final["url"] == PAGE
    assert final["fingerprint"] == fingerprint(PAGE_HTML)


def test_log_never_contains_the_page(tmp_path):
    make_fetcher(PretendSite(), tmp_path, REVIEW_ALLOWING_FACTS).fetch(PAGE, Purpose.COLLECT_FACTS)

    log_text = (tmp_path / "visits.jsonl").read_text(encoding="utf-8")
    assert "Opening: 20 Nov to 23 Dec" not in log_text
