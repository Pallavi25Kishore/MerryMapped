from dataclasses import dataclass
from enum import StrEnum


class Basis(StrEnum):
    """Which kind of rule decided an answer."""

    APP_POLICY = "app_policy"      # our own choice, stricter than the law
    NOT_REVIEWED = "not_reviewed"  # nobody has checked this site yet (default no)
    SITE_TERMS = "site_terms"      # the site's terms of use (a contract)
    ROBOTS_TXT = "robots_txt"      # the site's robots.txt
    LAW = "law"                    # a law: EU, national or US


@dataclass(frozen=True)
class Decision:
    """The rules engine's answer to one question. Sealed once made."""

    allowed: bool
    reason: str
    basis: Basis
    citation: str
