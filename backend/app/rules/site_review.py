from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl

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
