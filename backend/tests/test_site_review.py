import pytest
from pydantic import ValidationError

from app.rules.purposes import Purpose
from app.rules.site_review import ReviewedPurposes, SiteReview, load_review


def valid_review():
    """A properly filled-in review, as it looks after reading the YAML file."""
    return {
        "reviewed_on": "2026-10-20",
        "terms_urls": ["https://weihnachtsmarkt-koeln.de/nutzungsbedingungen"],
        "automated_access": {"answer": "allow", "because": "No clause restricts bots"},
        "purposes": {
            "collect_facts": {"answer": "allow", "because": "No clause restricts collecting facts"},
            "write_summary": {
                "answer": "deny",
                "because": '"Bearbeitungen der Inhalte sind untersagt" (Nutzungsbedingungen §3)',
            },
        },
    }


def test_valid_review_is_accepted():
    review = SiteReview.model_validate(valid_review())

    assert review.reviewed_on.isoformat() == "2026-10-20"
    assert review.automated_access.answer == "allow"
    assert review.purposes.collect_facts.answer == "allow"
    assert review.purposes.write_summary.answer == "deny"


def test_purpose_line_can_be_left_out():
    review = SiteReview.model_validate(valid_review())

    assert review.purposes.keep_evidence is None


def test_engine_only_purpose_is_refused():
    data = valid_review()
    data["purposes"]["copy_text_or_photos"] = {"answer": "allow", "because": "Typo or mistake"}

    with pytest.raises(ValidationError):
        SiteReview.model_validate(data)


def test_misspelt_answer_is_refused():
    data = valid_review()
    data["purposes"]["collect_facts"]["answer"] = "alow"

    with pytest.raises(ValidationError):
        SiteReview.model_validate(data)


def test_blank_because_is_refused():
    data = valid_review()
    data["automated_access"]["because"] = ""

    with pytest.raises(ValidationError):
        SiteReview.model_validate(data)


def test_impossible_date_is_refused():
    data = valid_review()
    data["reviewed_on"] = "2026-13-45"

    with pytest.raises(ValidationError):
        SiteReview.model_validate(data)


def test_review_needs_at_least_one_terms_page():
    data = valid_review()
    data["terms_urls"] = []

    with pytest.raises(ValidationError):
        SiteReview.model_validate(data)


def test_reviewed_purposes_match_the_purposes_list():
    engine_only = {Purpose.READ_TERMS, Purpose.COPY_TEXT_OR_PHOTOS}

    assert set(ReviewedPurposes.model_fields) == set(Purpose) - engine_only


GOOD_REVIEW_FILE = """\
reviewed_on: 2026-10-20
terms_urls:
  - https://weihnachtsmarkt-koeln.de/nutzungsbedingungen
automated_access:
  answer: allow
  because: "No clause restricts bots"
purposes:
  collect_facts:
    answer: allow
    because: "No clause restricts collecting facts"
"""


def test_review_file_is_found(tmp_path):
    (tmp_path / "weihnachtsmarkt-koeln.de.yaml").write_text(GOOD_REVIEW_FILE, encoding="utf-8")

    review = load_review("weihnachtsmarkt-koeln.de", reviews_dir=tmp_path)

    assert review.purposes.collect_facts.answer == "allow"


def test_no_review_file_means_not_reviewed(tmp_path):
    assert load_review("weihnachtsmarkt-koeln.de", reviews_dir=tmp_path) is None


def test_badly_filled_in_file_is_refused(tmp_path):
    bad = GOOD_REVIEW_FILE.replace("answer: allow", "answer: alow")
    (tmp_path / "weihnachtsmarkt-koeln.de.yaml").write_text(bad, encoding="utf-8")

    with pytest.raises(ValidationError):
        load_review("weihnachtsmarkt-koeln.de", reviews_dir=tmp_path)


def test_empty_file_is_refused(tmp_path):
    (tmp_path / "weihnachtsmarkt-koeln.de.yaml").write_text("", encoding="utf-8")

    with pytest.raises(ValidationError):
        load_review("weihnachtsmarkt-koeln.de", reviews_dir=tmp_path)


def test_unsafe_site_name_is_refused(tmp_path):
    with pytest.raises(ValueError):
        load_review("../../secret", reviews_dir=tmp_path)
