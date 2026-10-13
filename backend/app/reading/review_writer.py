from datetime import date
from pathlib import Path

import yaml

from app.rules.site_review import REVIEWS_DIR, SiteReview, review_path

HEADER = """\
# Site review for {site}
# Drafted by AI ({model}) on {today}, using backend/prompts/clause_guide.md,
# from the terms pages listed below. Read every answer against those pages.
# robots.txt on {today} (for information; the engine checks the current one on every visit):
#   {robots}.
# Approve by committing this file; reject by deleting it.
"""


def write_draft(site: str, draft: dict, terms_urls: list[str], model: str,
                reviews_dir: Path = REVIEWS_DIR, today: date | None = None,
                robots: str = "not checked") -> Path:
    """Save an AI-drafted review as site_reviews/<site>.yaml, after checking it with the review form."""
    today = today or date.today()
    data = {
        "reviewed_on": today,
        "terms_urls": terms_urls,
        "automated_access": draft["automated_access"],
        "purposes": draft["purposes"],
    }
    SiteReview.model_validate(data)  # refuse anything the engine couldn't load

    path = review_path(site, reviews_dir)
    if path.exists():
        raise FileExistsError(f"{path.name} already exists; delete it first to re-draft this site")

    body = yaml.safe_dump(data, sort_keys=False, allow_unicode=True, width=100)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(HEADER.format(site=site, model=model, today=today, robots=robots) + body, encoding="utf-8")
    return path


BLOCKED_HEADER = """\
# Site review for {site}
# Written by code on {today}: the site's robots.txt blocks our reader, so its terms could not be
# read and nothing was drafted by AI.
# robots.txt on {today} (for information; the engine checks the current one on every visit):
#   {robots}.
# Approve by committing this file; reject by deleting it.
"""


def write_blocked(site: str, robots_address: str, reason: str, robots: str,
                  reviews_dir: Path = REVIEWS_DIR, today: date | None = None) -> Path:
    """A review for a site whose robots.txt blocks us: every reading purpose denied, linking allowed."""
    today = today or date.today()
    def follows():  # a fresh answer each time, so the YAML spells each one out
        return {"answer": "deny", "because": f"Follows from robots.txt: {reason}"}
    data = {
        "reviewed_on": today,
        "terms_urls": [robots_address],
        "automated_access": {"answer": "deny", "because": f"{reason}; the terms could not be read"},
        "purposes": {
            "collect_facts": follows(),
            "keep_evidence": follows(),
            "write_summary": follows(),
            "show_link": {"answer": "allow", "because": "Linking needs no download, and nothing forbids it"},
        },
    }
    SiteReview.model_validate(data)

    path = review_path(site, reviews_dir)
    if path.exists():
        raise FileExistsError(f"{path.name} already exists; delete it first to re-draft this site")
    body = yaml.safe_dump(data, sort_keys=False, allow_unicode=True, width=100)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(BLOCKED_HEADER.format(site=site, today=today, robots=robots) + body, encoding="utf-8")
    return path
