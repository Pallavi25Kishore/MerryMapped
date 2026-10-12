import re
from datetime import date
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, HttpUrl

# backend/site_reviews/: one admin-approved YAML review per site.
REVIEWS_DIR = Path(__file__).resolve().parents[2] / "site_reviews"

# Every form below: no unknown boxes, no empty text, sealed once checked.
STRICT = ConfigDict(extra="forbid", str_min_length=1, frozen=True)


class Answer(BaseModel):
    """One reviewed answer, with the clause or reason it rests on."""

    model_config = STRICT

    answer: Literal["allow", "deny"]
    because: str


class ReviewedPurposes(BaseModel):
    """The purposes a site review may decide. Engine rules decide the other two."""

    model_config = STRICT

    collect_facts: Answer | None = None
    keep_evidence: Answer | None = None
    write_summary: Answer | None = None
    show_link: Answer | None = None


class SiteReview(BaseModel):
    """An admin-approved review of one website's terms."""

    model_config = STRICT

    reviewed_on: date
    terms_urls: list[HttpUrl] = Field(min_length=1)
    automated_access: Answer
    purposes: ReviewedPurposes


def review_path(site: str, reviews_dir: Path = REVIEWS_DIR) -> Path:
    """Where a site's review lives. Refuses names that could point outside the reviews folder."""
    if not re.fullmatch(r"[a-z0-9.-]+", site):
        raise ValueError(f"Not a valid site name: {site!r}")
    return reviews_dir / f"{site}.yaml"


def load_review(site: str, reviews_dir: Path = REVIEWS_DIR) -> SiteReview | None:
    """Read and check a site's approved review, or return None if it has none."""
    path = review_path(site, reviews_dir)
    if not path.exists():
        return None

    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return SiteReview.model_validate(data)
