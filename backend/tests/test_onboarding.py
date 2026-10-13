import json
import re
from types import SimpleNamespace

from app.agent.onboarding import MAX_ROUNDS, onboard
from tests.test_agent_tools import tools as make_tools
from tests.test_draft_review import PretendSite

START = "https://koeln-market.example/"
ZEITEN = "https://koeln-market.example/zeiten"

HOME = """<html><body><h1>Weihnachtsmarkt 2026</h1>
<p>Geöffnet vom 16.11. bis 23.12.</p><p>Täglich 11 bis 21 Uhr.</p>
<a href="/zeiten">Zeiten</a></body></html>""".encode()
ANFAHRT_PAGE = """<html><body><h1>Anfahrt</h1><p>Auf dem Hauptmarkt</p></body></html>""".encode()
ZEITEN_PAGE = """<html><body><h1>Weihnachtsmarkt 2026</h1>
<p>Eröffnung am 17.11.</p><p>Täglich 11 bis 21 Uhr.</p></body></html>""".encode()

EMPTY_VALUE = dict.fromkeys(["date", "days", "opens", "closes", "from", "until", "text", "tag"])
ALL_DAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]


def fact(kind, value, quote, year_quote="Weihnachtsmarkt 2026"):
    return {"kind": kind, "value": {**EMPTY_VALUE, **value}, "evidence_quote": quote,
            "evidence_translation": None, "year_quote": year_quote}


OPENING = fact("opening_date", {"date": "2026-11-16"}, "Geöffnet vom 16.11. bis 23.12.")
CLOSING = fact("closing_date", {"date": "2026-12-23"}, "Geöffnet vom 16.11. bis 23.12.")
HOURS = fact("hours", {"days": ALL_DAYS, "opens": "11:00", "closes": "21:00"},
             "Täglich 11 bis 21 Uhr.", year_quote=None)
LATER_OPENING = fact("opening_date", {"date": "2026-11-17"}, "Eröffnung am 17.11.")
ADDRESS = fact("address", {"text": "Hauptmarkt"}, "Auf dem Hauptmarkt", year_quote=None)
ANFAHRT = "https://koeln-market.example/anfahrt"


def open_page(url):
    return ("open_page", {"url": url, "reason": "test"})


class PretendAgentAndReader:
    """Plays both Claudes: the agent (requests with tools) follows a script of moves;
    the market reader (requests with a form) answers with the facts prepared for each page."""

    def __init__(self, moves, facts_by_page, repeat_last=False):
        self.moves = list(moves)
        self.facts_by_page = facts_by_page
        self.repeat_last = repeat_last
        self.agent_requests = []
        self.messages = self  # so code can call client.messages.create(...)

    def create(self, **request):
        if "tools" in request:
            self.agent_requests.append(request)
            if not self.moves:
                return SimpleNamespace(content=[SimpleNamespace(type="text", text="I am done.")])
            name, given = self.moves[0] if self.repeat_last and len(self.moves) == 1 else self.moves.pop(0)
            call = SimpleNamespace(type="tool_use", id=f"call_{len(self.agent_requests)}", name=name, input=given)
            return SimpleNamespace(content=[call])
        url = re.search(r'<market_page url="([^"]+)">', request["messages"][0]["content"]).group(1)
        form = {"facts": self.facts_by_page.get(url, [])}
        return SimpleNamespace(content=[SimpleNamespace(type="text", text=json.dumps(form))])


def run(tmp_path, claude):
    site = PretendSite({"/": (200, "text/html", HOME), "/zeiten": (200, "text/html", ZEITEN_PAGE),
                        "/anfahrt": (200, "text/html", ANFAHRT_PAGE)})
    tools = make_tools(tmp_path, site)
    tools.client = claude
    return onboard(START, tools=tools, client=claude)


def test_code_stops_the_search_once_everything_is_found(tmp_path):
    claude = PretendAgentAndReader([open_page(START), open_page(ANFAHRT), open_page(ZEITEN)],
                                   {START: [OPENING, CLOSING, HOURS], ANFAHRT: [ADDRESS]})
    collected = run(tmp_path, claude)

    assert len(claude.agent_requests) == 2  # the hours page was never opened
    assert [f["kind"] for f in collected.facts] == ["opening_date", "closing_date", "hours", "address"]
    assert collected.missing == []
    assert collected.summary == "stopped by the guardrails"


def test_the_address_gets_three_more_pages_then_the_search_ends_without_it(tmp_path):
    pages = [START, ZEITEN, ANFAHRT, "https://koeln-market.example/faq", "https://koeln-market.example/kontakt"]
    claude = PretendAgentAndReader([open_page(url) for url in pages], {START: [OPENING, CLOSING, HOURS]})
    collected = run(tmp_path, claude)

    assert len(claude.agent_requests) == 4  # the start page, then 3 tries for the address
    assert collected.missing == ["address"]
    assert [f["kind"] for f in collected.facts] == ["opening_date", "closing_date", "hours"]


def test_claude_can_finish(tmp_path):
    claude = PretendAgentAndReader([open_page(START), ("finish", {"summary": "No hours anywhere."})],
                                   {START: [OPENING, CLOSING]})
    collected = run(tmp_path, claude)

    assert collected.summary == "No hours anywhere."
    assert collected.missing == ["hours", "address"]


def test_the_search_stops_after_the_last_round(tmp_path):
    claude = PretendAgentAndReader([open_page("https://other-market.example/")], {}, repeat_last=True)
    collected = run(tmp_path, claude)

    assert len(claude.agent_requests) == MAX_ROUNDS
    assert collected.facts == []


def test_the_same_fact_on_two_pages_is_kept_once(tmp_path):
    claude = PretendAgentAndReader([open_page(START), open_page(ZEITEN)],
                                   {START: [OPENING, CLOSING], ZEITEN: [HOURS, HOURS]})
    collected = run(tmp_path, claude)

    assert [f["kind"] for f in collected.facts] == ["opening_date", "closing_date", "hours"]


def test_pages_that_disagree_are_both_dropped_and_reported(tmp_path):
    claude = PretendAgentAndReader([open_page(START), open_page(ZEITEN)],
                                   {START: [OPENING, HOURS], ZEITEN: [LATER_OPENING]})
    collected = run(tmp_path, claude)

    assert [f["kind"] for f in collected.facts] == ["hours"]
    assert [(page, reason) for page, _, reason in collected.dropped] == [
        (START, "different opening_dates were given"),
        (ZEITEN, "different opening_dates were given"),
    ]
    assert collected.missing == ["opening_date", "closing_date", "address"]
