import json

from app.fetcher.result import FetchResult
from app.fetcher.visit_log import VisitLog, fingerprint
from app.rules.decision import Basis, Decision
from app.rules.purposes import Purpose

SLIP = Decision(
    allowed=True,
    reason="Admin-approved review (2026-10-20) allows this",
    basis=Basis.SITE_TERMS,
    citation="No clause restricts collecting facts",
)


def read_lines(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def test_same_page_gives_same_fingerprint():
    assert fingerprint(b"Opening: 20 Nov") == fingerprint(b"Opening: 20 Nov")


def test_one_character_changes_the_fingerprint():
    assert fingerprint(b"Opening: 20 Nov") != fingerprint(b"Opening: 21 Nov")


def test_log_line_has_every_box(tmp_path):
    log = VisitLog(tmp_path / "visits.jsonl")
    log.record(FetchResult(SLIP, "https://weihnachtsmarkt-koeln.de/markt", Purpose.COLLECT_FACTS,
                           status_code=200, fingerprint="abc123"))

    [entry] = read_lines(tmp_path / "visits.jsonl")
    assert entry["url"] == "https://weihnachtsmarkt-koeln.de/markt"
    assert entry["purpose"] == "collect_facts"
    assert entry["allowed"] is True
    assert entry["basis"] == "site_terms"
    assert entry["citation"] == "No clause restricts collecting facts"
    assert entry["status_code"] == 200
    assert entry["fingerprint"] == "abc123"
    assert entry["time"].endswith("+00:00")  # UTC


def test_lines_are_added_never_overwritten(tmp_path):
    log = VisitLog(tmp_path / "visits.jsonl")
    log.record(FetchResult(SLIP, "https://weihnachtsmarkt-koeln.de/a", Purpose.COLLECT_FACTS))
    log.record(FetchResult(SLIP, "https://weihnachtsmarkt-koeln.de/b", Purpose.COLLECT_FACTS))

    urls = [entry["url"] for entry in read_lines(tmp_path / "visits.jsonl")]
    assert urls == ["https://weihnachtsmarkt-koeln.de/a", "https://weihnachtsmarkt-koeln.de/b"]
