from datetime import date

import httpx
import pytest

from app.draft_review import DraftStopped, draft_site_review
from app.fetcher.robots import make_client
from app.fetcher.safe_fetcher import SafeFetcher
from app.fetcher.visit_log import VisitLog
from app.rules.site_review import load_review
from tests.test_terms_reader import GOOD_FORM, PretendClaude

START = "https://koeln-market.example/"
SITE = "koeln-market.example"

START_PAGE = b"""<html><body>
<h1>Weihnachtsmarkt am Dom</h1>
<a href="/programm">Programm</a>
<footer><a href="/agb">AGB</a></footer>
</body></html>"""

START_PAGE_WITHOUT_TERMS = b"""<html><body>
<h1>Weihnachtsmarkt am Dom</h1>
<a href="/programm">Programm</a>
</body></html>"""

AGB_PAGE = b"""<html><body><h1>AGB</h1>
<p>Die Bearbeitung der Inhalte ist untersagt.</p>
</body></html>"""

NO_TERMS_FORM = {
    "automated_access": {"answer": "allow", "because": "Row 1: No terms of use found"},
    "purposes": {
        name: {"answer": "allow", "because": "Row 1: No terms of use found"}
        for name in ("collect_facts", "keep_evidence", "write_summary", "show_link")
    },
}


class PretendSite:
    """A pretend website: each path answers with (status, content type, body)."""

    def __init__(self, pages, robots_text=""):
        self.pages = pages
        self.robots_text = robots_text
        self.requested = []

    def answer(self, request):
        self.requested.append(request.url.path)
        if request.url.path == "/robots.txt":
            return httpx.Response(200 if self.robots_text else 404, text=self.robots_text)
        status, content_type, body = self.pages.get(request.url.path, (404, "text/html", b""))
        return httpx.Response(status, headers={"Content-Type": content_type}, content=body)


def run(tmp_path, site, claude):
    """Run the whole flow against a pretend site and a pretend Claude, in temporary folders."""
    reviews = tmp_path / "site_reviews"
    fetcher = SafeFetcher(
        client=make_client(transport=httpx.MockTransport(site.answer)),
        reviews_dir=reviews,
        log=VisitLog(tmp_path / "visits.jsonl"),
        clock=lambda: 0.0,
        sleep=lambda seconds: None,
    )
    return draft_site_review(START, fetcher=fetcher, client=claude, reviews_dir=reviews,
                             today=date(2026, 10, 20))


def test_full_flow_writes_a_review(tmp_path):
    site = PretendSite({"/": (200, "text/html", START_PAGE), "/agb": (200, "text/html", AGB_PAGE)})
    claude = PretendClaude(GOOD_FORM)
    run(tmp_path, site, claude)

    review = load_review(SITE, reviews_dir=tmp_path / "site_reviews")
    assert [str(url) for url in review.terms_urls] == ["https://koeln-market.example/agb"]
    assert "Die Bearbeitung der Inhalte ist untersagt." in claude.requests[0]["messages"][0]["content"]


def test_no_terms_links_uses_the_start_page(tmp_path):
    site = PretendSite({"/": (200, "text/html", START_PAGE_WITHOUT_TERMS)})
    claude = PretendClaude(NO_TERMS_FORM)
    run(tmp_path, site, claude)

    review = load_review(SITE, reviews_dir=tmp_path / "site_reviews")
    assert [str(url) for url in review.terms_urls] == [START]
    assert "general rule 5" in claude.requests[0]["messages"][0]["content"]


def test_terms_page_blocked_by_robots_stops_before_the_ai(tmp_path):
    site = PretendSite(
        {"/": (200, "text/html", START_PAGE), "/agb": (200, "text/html", AGB_PAGE)},
        robots_text="User-agent: *\nDisallow: /agb\n",
    )
    claude = PretendClaude(GOOD_FORM)

    with pytest.raises(DraftStopped, match="robots.txt"):
        run(tmp_path, site, claude)
    assert claude.requests == []
    assert not (tmp_path / "site_reviews" / f"{SITE}.yaml").exists()


def test_pdf_terms_page_stops_before_the_ai(tmp_path):
    site = PretendSite({
        "/": (200, "text/html", START_PAGE),
        "/agb": (200, "application/pdf", b"%PDF-1.7 pretend terms"),
    })
    claude = PretendClaude(GOOD_FORM)

    with pytest.raises(DraftStopped, match="PDF"):
        run(tmp_path, site, claude)
    assert claude.requests == []
    assert not (tmp_path / "site_reviews" / f"{SITE}.yaml").exists()


def test_existing_review_stops_before_any_download(tmp_path):
    reviews = tmp_path / "site_reviews"
    reviews.mkdir()
    (reviews / f"{SITE}.yaml").write_text("# an approved review\n", encoding="utf-8")
    site = PretendSite({"/": (200, "text/html", START_PAGE)})

    with pytest.raises(DraftStopped, match="already has a review"):
        run(tmp_path, site, PretendClaude())
    assert site.requested == []


def test_unreadable_start_page_stops(tmp_path):
    site = PretendSite({})  # every page answers 404

    with pytest.raises(DraftStopped, match="the site answered 404"):
        run(tmp_path, site, PretendClaude())


def test_the_review_notes_what_robots_txt_said(tmp_path):
    site = PretendSite({"/": (200, "text/html", START_PAGE), "/agb": (200, "text/html", AGB_PAGE)})
    path = run(tmp_path, site, PretendClaude(GOOD_FORM))

    assert "#   no robots.txt, so no restrictions." in path.read_text(encoding="utf-8")


def test_a_site_whose_robots_txt_blocks_us_gets_a_link_only_review(tmp_path):
    site = PretendSite({"/": (200, "text/html", START_PAGE)},
                       robots_text="User-agent: GPTBot\nDisallow: /\n")
    claude = PretendClaude(GOOD_FORM)
    path = run(tmp_path, site, claude)

    review = load_review(SITE, reviews_dir=tmp_path / "site_reviews")
    assert review.automated_access.answer == "deny"
    assert review.purposes.collect_facts.answer == "deny"
    assert review.purposes.show_link.answer == "allow"
    assert [str(url) for url in review.terms_urls] == ["https://koeln-market.example/robots.txt"]
    assert "Written by code" in path.read_text(encoding="utf-8")
    assert claude.requests == []          # no AI was asked
    assert site.requested == ["/robots.txt"]  # the page itself was never downloaded


class UnreachableRobots(PretendSite):
    """A site whose robots.txt answers with a server error."""

    def answer(self, request):
        if request.url.path == "/robots.txt":
            self.requested.append(request.url.path)
            return httpx.Response(503)
        return super().answer(request)


def test_an_unreachable_robots_txt_stops_without_a_review(tmp_path):
    site = UnreachableRobots({"/": (200, "text/html", START_PAGE)})

    with pytest.raises(DraftStopped, match="robots.txt could not be checked"):
        run(tmp_path, site, PretendClaude(GOOD_FORM))
    assert not (tmp_path / "site_reviews" / f"{SITE}.yaml").exists()


def test_the_link_only_review_spells_out_every_answer(tmp_path):
    site = PretendSite({"/": (200, "text/html", START_PAGE)}, robots_text="User-agent: GPTBot\nDisallow: /\n")
    text = run(tmp_path, site, PretendClaude(GOOD_FORM)).read_text(encoding="utf-8")

    assert "&id" not in text and "*id" not in text
