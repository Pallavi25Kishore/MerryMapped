from datetime import date

import pytest
from pydantic import ValidationError

from app.reading.review_writer import write_draft
from app.rules.site_review import load_review

SITE = "weihnachtsmarkt-koeln.de"
TERMS_URLS = ["https://weihnachtsmarkt-koeln.de/agb"]
TODAY = date(2026, 10, 20)
MODEL = "claude-sonnet-5-5"


def answer(answer, because):
    return {"answer": answer, "because": because}


def good_draft():
    return {
        "automated_access": answer("allow", "Row 1: terms reviewed, no clause restricts bots"),
        "purposes": {
            "collect_facts": answer("allow", "Row 1: terms reviewed, no clause restricts collecting facts"),
            "keep_evidence": answer("allow", "Row 1: terms reviewed, no clause restricts quoting"),
            "write_summary": answer("allow", 'Row 6: "Die Bearbeitung der Inhalte ist untersagt." (§3)'),
            "show_link": answer("allow", "Row 1: terms reviewed, no clause restricts linking"),
        },
    }


def write(tmp_path, draft=None):
    return write_draft(SITE, draft or good_draft(), TERMS_URLS, MODEL, reviews_dir=tmp_path, today=TODAY)


def test_written_file_loads_back(tmp_path):
    write(tmp_path)
    review = load_review(SITE, reviews_dir=tmp_path)

    assert review.purposes.write_summary.because == 'Row 6: "Die Bearbeitung der Inhalte ist untersagt." (§3)'
    assert review.automated_access.answer == "allow"


def test_header_is_present(tmp_path):
    text = write(tmp_path).read_text(encoding="utf-8")

    assert text.startswith(f"# Site review for {SITE}\n")
    assert f"Drafted by AI ({MODEL}) on 2026-10-20" in text
    assert "clause_guide.md" in text


def test_code_fills_the_date_and_pages(tmp_path):
    write(tmp_path)
    review = load_review(SITE, reviews_dir=tmp_path)

    assert review.reviewed_on == TODAY
    assert [str(url) for url in review.terms_urls] == TERMS_URLS


def test_german_letters_are_readable(tmp_path):
    text = write(tmp_path).read_text(encoding="utf-8")

    assert "Die Bearbeitung der Inhalte ist untersagt." in text
    assert "§3" in text


def test_bad_draft_is_refused_and_nothing_is_written(tmp_path):
    draft = good_draft()
    draft["purposes"]["show_link"] = answer("maybe", "Row 1: unsure")

    with pytest.raises(ValidationError):
        write(tmp_path, draft)
    assert not (tmp_path / f"{SITE}.yaml").exists()


def test_never_overwrites_an_existing_review(tmp_path):
    existing = tmp_path / f"{SITE}.yaml"
    existing.write_text("# an approved review\n", encoding="utf-8")

    with pytest.raises(FileExistsError):
        write(tmp_path)
    assert existing.read_text(encoding="utf-8") == "# an approved review\n"


def test_unsafe_site_name_is_refused(tmp_path):
    with pytest.raises(ValueError):
        write_draft("../../secret", good_draft(), TERMS_URLS, MODEL, reviews_dir=tmp_path, today=TODAY)
