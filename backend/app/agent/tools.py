from app.draft_review import why
from app.fetcher.safe_fetcher import SafeFetcher
from app.reading.clean import CleanPage, clean_html
from app.reading.fact_checks import check_facts, drop_contradictions
from app.reading.market_reader import read_page
from app.rules.decision import Decision
from app.rules.engine import site_of
from app.rules.purposes import Purpose

MAX_PAGES = 10
MAX_LINKS = 80
MAX_LINK_TEXT = 80
REQUIRED = ["opening_date", "closing_date", "hours"]
TRY_HARD = ["address"]  # looked for on a few extra pages, but the search may end without it

# What Claude sees: the actions it may ask for, and the inputs each one takes.
TOOLS = [
    {
        "name": "open_page",
        "description": "Open one page of the market's site. Returns the facts found and dropped, "
                       "what is still missing, the page's links and the pages left.",
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "A link from an earlier result, or the start page"},
                "reason": {"type": "string", "description": "One line: why this page"},
            },
            "required": ["url", "reason"],
        },
    },
    {
        "name": "finish",
        "description": "End the search. Summarise what was found and what is missing.",
        "input_schema": {
            "type": "object",
            "properties": {"summary": {"type": "string"}},
            "required": ["summary"],
        },
    },
]


class AgentTools:
    """Carries out the agent's requests within the guardrails, and remembers the search so far."""

    def __init__(self, start_url: str, fetcher: SafeFetcher | None = None, client=None,
                 max_pages: int = MAX_PAGES):
        self.site = site_of(start_url)
        self.fetcher = fetcher or SafeFetcher()
        self.client = client
        self.max_pages = max_pages
        self.opened: set[str] = set()
        self.pages_used = 0
        self.facts: list[dict] = []                     # passed the checks, stamped with their page
        self.dropped: list[tuple[str, dict, str]] = []  # (page, fact, reason)
        self.steps: list[str] = []                      # one line per tool call, for the run report
        self.summary: str | None = None
        self.page_texts: list[str] = []               # in memory only, for the overlap check
        self.description_allowed: Decision | None = None

    def open_page(self, url: str, reason: str) -> dict:
        if site_of(url) != self.site:
            return self.refuse(url, reason, f"only pages on {self.site} may be opened")
        if url in self.opened:
            return self.refuse(url, reason, "this page was already opened")
        if self.pages_used >= self.max_pages:
            return self.refuse(url, reason, "no pages left")

        self.pages_used += 1
        self.opened.add(url)
        result = self.fetcher.fetch(url, Purpose.COLLECT_FACTS)  # engine, robots.txt, speed limit, log
        if result.content is None:
            return self.report(url, reason, {"status": "could not open", "why": why(result)})
        if site_of(result.url) != self.site:
            return self.report(url, reason, {"status": "could not open", "why": "it led to another site"})
        if result.content.startswith(b"%PDF"):
            return self.report(url, reason, {"status": "could not open", "why": "PDFs can't be read yet"})
        self.opened.add(result.url)

        page = clean_html(result.content, result.url)
        self.page_texts.append(page.text)
        if self.description_allowed is None:
            self.description_allowed = self.fetcher.ask(result.url, Purpose.WRITE_SUMMARY)
        kept, dropped = check_facts(read_page(result.url, page.text, client=self.client), page.text)
        stamp = {"source_url": result.url, "page_fingerprint": result.fingerprint}
        quotes = self.fetcher.ask(result.url, Purpose.KEEP_EVIDENCE)
        if not quotes.allowed:  # the facts may be kept, the site's sentences may not
            stamp |= {"evidence_quote": None, "evidence_translation": None,
                      "quote_not_kept": quotes.reason}
        self.facts += [{**fact, **stamp} for fact in kept]
        self.dropped += [(result.url, fact, problem) for fact, problem in dropped]
        return self.report(url, reason, {
            "status": "read",
            "facts_found": [{"kind": fact["kind"], "value": fact["value"]} for fact in kept],
            "facts_dropped": [{"kind": fact["kind"], "reason": problem} for fact, problem in dropped],
            "still_missing": self.missing(),
            "links": self.new_links(page),
            "pages_left": self.max_pages - self.pages_used,
        })

    def finish(self, summary: str) -> dict:
        self.summary = summary
        self.steps.append(f"finish: {summary}")
        return {"status": "finished"}

    def missing(self) -> list[str]:
        """Required and try-hard kinds not yet found, once facts from different pages are checked against each other."""
        kept, _ = drop_contradictions(self.facts)
        found = {fact["kind"] for fact in kept}
        return [kind for kind in REQUIRED + TRY_HARD if kind not in found]

    def new_links(self, page: CleanPage) -> list[dict]:
        """Links on the same site that haven't been opened, shortened so the agent's conversation stays small."""
        links = [{"text": link.text[:MAX_LINK_TEXT], "url": link.url} for link in page.links
                 if site_of(link.url) == self.site and link.url not in self.opened]
        return links[:MAX_LINKS]

    def refuse(self, url: str, reason: str, why_not: str) -> dict:
        return self.report(url, reason, {"status": "refused", "why": why_not})

    def report(self, url: str, reason: str, outcome: dict) -> dict:
        self.steps.append(f"open_page {url} ({reason}): {outcome['status']} {outcome.get('why', '')}".rstrip())
        return outcome
