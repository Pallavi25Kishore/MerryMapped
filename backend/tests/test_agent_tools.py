import httpx

from app.agent.tools import AgentTools
from app.fetcher.robots import make_client
from app.fetcher.safe_fetcher import SafeFetcher
from app.fetcher.visit_log import VisitLog, fingerprint
from tests.test_draft_review import PretendSite
from tests.test_market_reader import OPENING, PretendClaude

START = "https://koeln-market.example/"

HOME = """<html><body>
<h1>Weihnachtsmarkt 2026</h1>
<p>Der Markt ist vom 16.11. bis 23.12. geöffnet.</p>
<a href="/zeiten">Öffnungszeiten</a>
<a href="https://other-market.example/">Partner</a>
</body></html>""".encode()

REVIEW = """reviewed_on: 2026-10-20
terms_urls:
- https://koeln-market.example/impressum
automated_access:
  answer: allow
  because: 'Row 1: terms reviewed, no clause restricts bots'
purposes:
  collect_facts:
    answer: allow
    because: 'Row 1: terms reviewed, no clause restricts collecting facts'
  keep_evidence:
    answer: allow
    because: 'Row 1: terms reviewed, no clause restricts quoting'
  write_summary:
    answer: allow
    because: 'Row 1: terms reviewed, no clause restricts summaries'
"""

REVIEW_WITHOUT_QUOTES = REVIEW.replace("""  keep_evidence:
    answer: allow
    because: 'Row 1: terms reviewed, no clause restricts quoting'""", """  keep_evidence:
    answer: deny
    because: 'Row 7: "Auszüge dürfen nicht übernommen werden"'""")


def tools(tmp_path, site, reviewed=True, max_pages=10, review=REVIEW):
    reviews = tmp_path / "site_reviews"
    reviews.mkdir()
    if reviewed:
        (reviews / "koeln-market.example.yaml").write_text(review, encoding="utf-8")
    fetcher = SafeFetcher(
        client=make_client(transport=httpx.MockTransport(site.answer)),
        reviews_dir=reviews,
        log=VisitLog(tmp_path / "visits.jsonl"),
        clock=lambda: 0.0,
        sleep=lambda seconds: None,
    )
    return AgentTools(START, fetcher=fetcher, client=PretendClaude({"facts": [OPENING]}), max_pages=max_pages)


def home_site():
    return PretendSite({"/": (200, "text/html", HOME), "/zeiten": (200, "text/html", HOME)})


def test_a_good_page_returns_facts_links_and_what_is_missing(tmp_path):
    agent = tools(tmp_path, home_site())
    outcome = agent.open_page(START, "home page")

    assert outcome["status"] == "read"
    assert outcome["facts_found"] == [{"kind": "opening_date", "value": {"date": "2026-11-16"}}]
    assert outcome["still_missing"] == ["closing_date", "hours", "address"]
    assert outcome["links"] == [{"text": "Öffnungszeiten", "url": "https://koeln-market.example/zeiten"}]
    assert outcome["pages_left"] == 9
    assert agent.facts[0]["source_url"] == START
    assert agent.facts[0]["page_fingerprint"] == fingerprint(HOME)


def test_another_site_is_refused_without_a_download(tmp_path):
    site = home_site()
    outcome = tools(tmp_path, site).open_page("https://other-market.example/", "partner")

    assert outcome == {"status": "refused", "why": "only pages on koeln-market.example may be opened"}
    assert site.requested == []


def test_a_page_is_opened_only_once(tmp_path):
    agent = tools(tmp_path, home_site())
    agent.open_page(START, "home page")

    assert agent.open_page(START, "again") == {"status": "refused", "why": "this page was already opened"}


def test_no_page_beyond_the_budget(tmp_path):
    agent = tools(tmp_path, home_site(), max_pages=1)
    agent.open_page(START, "home page")
    outcome = agent.open_page("https://koeln-market.example/zeiten", "hours")

    assert outcome == {"status": "refused", "why": "no pages left"}


def test_a_page_the_engine_refuses_could_not_be_opened(tmp_path):
    outcome = tools(tmp_path, home_site(), reviewed=False).open_page(START, "home page")

    assert outcome["status"] == "could not open"
    assert "review" in outcome["why"].lower()


def test_quotes_are_kept_when_the_review_allows_it(tmp_path):
    agent = tools(tmp_path, home_site())
    agent.open_page(START, "home page")

    assert agent.facts[0]["evidence_quote"] == OPENING["evidence_quote"]


def test_quotes_are_removed_when_the_review_denies_it(tmp_path):
    agent = tools(tmp_path, home_site(), review=REVIEW_WITHOUT_QUOTES)
    outcome = agent.open_page(START, "home page")

    assert outcome["facts_found"] == [{"kind": "opening_date", "value": {"date": "2026-11-16"}}]
    fact = agent.facts[0]
    assert (fact["evidence_quote"], fact["evidence_translation"]) == (None, None)
    assert fact["quote_not_kept"] == "Admin-approved review (2026-10-20) denies this"
    assert fact["source_url"] == START


def test_page_text_is_kept_and_the_description_decision_recorded(tmp_path):
    agent = tools(tmp_path, home_site())
    agent.open_page(START, "home page")

    assert "Der Markt ist vom 16.11. bis 23.12. geöffnet." in agent.page_texts[0]
    assert agent.description_allowed.allowed
