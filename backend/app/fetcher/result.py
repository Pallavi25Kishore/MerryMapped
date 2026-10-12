from dataclasses import dataclass

from app.rules.decision import Decision
from app.rules.purposes import Purpose


@dataclass(frozen=True)
class FetchResult:
    """What a fetch hands back: the engine's slip, and the page if it was downloaded."""

    decision: Decision
    url: str                        # the address this result is for (after any redirects)
    purpose: Purpose
    status_code: int | None = None  # the site's answer (200, 404, ...); None if never downloaded
    content: bytes | None = None    # the page, in memory only; None unless it passed every check
    problem: str | None = None      # why there is no page, even though the engine said yes
    fingerprint: str | None = None  # SHA-256 of the page: proves which version was read
