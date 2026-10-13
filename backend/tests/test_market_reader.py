import json
from types import SimpleNamespace

from app.reading.market_reader import FACTS_SCHEMA, read_page

URL = "https://koeln-market.example/de/zeiten/"
TEXT = "Weihnachtsmarkt 2026\nDer Markt ist vom 16.11. bis 23.12. geöffnet."

EMPTY_VALUE = dict.fromkeys(["date", "days", "opens", "closes", "from", "until", "text", "tag"])
OPENING = {
    "kind": "opening_date",
    "value": {**EMPTY_VALUE, "date": "2026-11-16"},
    "evidence_quote": "Der Markt ist vom 16.11. bis 23.12. geöffnet.",
    "evidence_translation": "The market is open from 16 Nov to 23 Dec.",
    "year_quote": "Weihnachtsmarkt 2026",
}


class PretendClaude:
    """Stands in for the Anthropic client: returns one prepared form and records the request."""

    def __init__(self, form):
        self.form = form
        self.requests = []
        self.messages = self  # so code can call client.messages.create(...)

    def create(self, **request):
        self.requests.append(request)
        return SimpleNamespace(content=[SimpleNamespace(type="text", text=json.dumps(self.form))])


def test_facts_come_back_without_the_empty_fields():
    facts = read_page(URL, TEXT, client=PretendClaude({"facts": [OPENING]}))

    assert facts == [{**OPENING, "value": {"date": "2026-11-16"}}]


def test_request_uses_the_prompt_the_schema_and_the_page_tags():
    claude = PretendClaude({"facts": []})
    read_page(URL, TEXT, client=claude)
    request = claude.requests[0]

    assert request["system"].startswith("# Market reader")
    assert request["output_config"] == {"format": {"type": "json_schema", "schema": FACTS_SCHEMA}}
    page = request["messages"][0]["content"]
    assert f'<market_page url="{URL}">\n{TEXT}\n</market_page>' in page


def test_a_page_without_facts_gives_an_empty_list():
    assert read_page(URL, TEXT, client=PretendClaude({"facts": []})) == []


def test_the_form_offers_details_and_only_the_fixed_tags():
    fact = FACTS_SCHEMA["properties"]["facts"]["items"]["properties"]

    assert {"detail", "tag"} <= set(fact["kind"]["enum"])
    text_or_null = fact["value"]["properties"]["tag"]["anyOf"]
    assert {"type": "null"} in text_or_null
    tags = text_or_null[0]["enum"]
    assert "artisan" in tags
    assert "romantic" not in tags
