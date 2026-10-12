from datetime import date
from pathlib import Path

import yaml

from app.rules.site_review import REVIEWS_DIR, SiteReview, review_path

HEADER = """\
# Site review for {site}
# Drafted by AI ({model}) on {today}, using backend/prompts/clause_guide.md,
# from the terms pages listed below. Read every answer against those pages.
# Approve by committing this file; reject by deleting it.
"""


def write_draft(site: str, draft: dict, terms_urls: list[str], model: str,
                reviews_dir: Path = REVIEWS_DIR, today: date | None = None) -> Path:
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
    path.write_text(HEADER.format(site=site, model=model, today=today) + body, encoding="utf-8")
    return path
