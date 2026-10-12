import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from app.fetcher.result import FetchResult

# backend/logs/visits.jsonl: one line per attempted visit, only ever added to.
LOG_PATH = Path(__file__).resolve().parents[2] / "logs" / "visits.jsonl"


def fingerprint(content: bytes) -> str:
    """A SHA-256 hash of a page: proves which version was read, without keeping a copy."""
    return hashlib.sha256(content).hexdigest()


class VisitLog:
    """Writes one line per attempted visit, including refusals. Never stores page content."""

    def __init__(self, path: Path = LOG_PATH):
        self.path = path

    def record(self, result: FetchResult) -> None:
        entry = {
            "time": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "url": result.url,
            "purpose": result.purpose,
            "allowed": result.decision.allowed,
            "reason": result.decision.reason,
            "basis": result.decision.basis,
            "citation": result.decision.citation,
            "status_code": result.status_code,
            "problem": result.problem,
            "fingerprint": result.fingerprint,
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as log_file:
            log_file.write(json.dumps(entry, ensure_ascii=False) + "\n")
