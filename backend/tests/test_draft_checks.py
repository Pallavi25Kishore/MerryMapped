from app.reading.draft_checks import check_draft

TERMS = """Nutzungsbedingungen
§3 Die Bearbeitung der
   Inhalte ist untersagt.
§5 Die Vervielfältigung, Bearbeitung, Verbreitung und jede Art der Verwertung außerhalb der
Grenzen des Urheberrechtes bedürfen der schriftlichen Zustimmung.
§6 Toute reproduction de l’ensemble du site est interdite.
§7 Automatisierte Zugriffe sind untersagt.
"""


def answer(answer, because):
    return {"answer": answer, "because": because}


def good_draft():
    """A draft that passes every check."""
    return {
        "automated_access": answer("allow", "Row 1: terms reviewed, no clause restricts bots"),
        "purposes": {
            "collect_facts": answer("allow", "Row 1: terms reviewed, no clause restricts collecting facts"),
            "keep_evidence": answer("allow", "Row 1: terms reviewed, no clause restricts quoting"),
            "write_summary": answer("allow", 'Row 6: "Die Bearbeitung der Inhalte ist untersagt." (§3)'),
            "show_link": answer("allow", "Row 1: terms reviewed, no clause restricts linking"),
        },
    }


def bots_denied_draft():
    """A consistent draft for a site that forbids bots."""
    draft = good_draft()
    draft["automated_access"] = answer("deny", 'Row 2: "Automatisierte Zugriffe sind untersagt." (§7)')
    for key in ("collect_facts", "keep_evidence", "write_summary"):
        draft["purposes"][key] = answer("deny", "Follows from row 2: automated access is denied")
    return draft


def test_good_draft_passes():
    assert check_draft(good_draft(), TERMS) == []


def test_consistent_bots_draft_passes():
    assert check_draft(bots_denied_draft(), TERMS) == []


def test_missing_answer():
    draft = good_draft()
    del draft["purposes"]["show_link"]

    assert check_draft(draft, TERMS) == ["show_link: missing"]


def test_because_must_start_with_a_row():
    draft = good_draft()
    draft["purposes"]["show_link"] = answer("allow", "Seems fine")

    assert check_draft(draft, TERMS) == [
        "show_link: 'because' must start with 'Row N:' or 'Follows from row N:'"
    ]


def test_unknown_row_is_refused():
    draft = good_draft()
    draft["purposes"]["show_link"] = answer("allow", "Row 99: made-up rule")

    assert len(check_draft(draft, TERMS)) == 1


def test_rule_without_a_quote_is_refused():
    draft = bots_denied_draft()
    draft["automated_access"] = answer("deny", "Row 2: the site forbids bots")

    assert check_draft(draft, TERMS) == ["automated_access: row 2 must quote the clause"]


def test_invented_quote_is_refused():
    draft = good_draft()
    draft["purposes"]["write_summary"] = answer("deny", 'Row 6b: "Zusammenfassungen sind verboten" (§8)')

    assert check_draft(draft, TERMS) == [
        'write_summary: quote not found in the terms: "Zusammenfassungen sind verboten"'
    ]


def test_changed_word_is_refused():
    draft = bots_denied_draft()
    draft["automated_access"] = answer("deny", 'Row 2: "Automatisierte Zugriffe sind verboten." (§7)')

    assert len(check_draft(draft, TERMS)) == 1


def test_different_spacing_is_fine():
    # §3 is split over two lines with extra spaces in TERMS; the good draft quotes it on one line.
    assert check_draft(good_draft(), TERMS) == []


def test_curly_apostrophe_is_fine():
    draft = good_draft()
    draft["purposes"]["write_summary"] = answer(
        "allow", 'Row 5: "Toute reproduction de l\'ensemble du site est interdite." (§6)')

    assert check_draft(draft, TERMS) == []


def test_german_and_french_quote_marks():
    draft = good_draft()
    draft["purposes"]["write_summary"] = answer("allow", "Row 6: „Die Bearbeitung der Inhalte ist untersagt.“ (§3)")
    draft["purposes"]["keep_evidence"] = answer("allow", "Row 5: « Toute reproduction de l’ensemble du site est interdite. » (§6)")

    assert check_draft(draft, TERMS) == []


def test_invented_quote_in_french_quote_marks_is_refused():
    draft = good_draft()
    draft["purposes"]["keep_evidence"] = answer("deny", "Row 7: « Toute citation est interdite » (§9)")

    assert len(check_draft(draft, TERMS)) == 1


def test_shortened_quote_with_parts_in_order():
    draft = good_draft()
    draft["purposes"]["write_summary"] = answer(
        "allow", 'Row 10: "Vervielfältigung, Bearbeitung ... außerhalb der Grenzen des Urheberrechtes" (§5)')

    assert check_draft(draft, TERMS) == []


def test_shortened_quote_with_parts_out_of_order_is_refused():
    draft = good_draft()
    draft["purposes"]["write_summary"] = answer(
        "allow", 'Row 10: "außerhalb der Grenzen des Urheberrechtes ... Vervielfältigung" (§5)')

    assert len(check_draft(draft, TERMS)) == 1


def test_bots_denied_but_evidence_allowed_is_refused():
    draft = bots_denied_draft()
    draft["purposes"]["keep_evidence"] = answer("allow", "Row 1: terms reviewed, no clause restricts quoting")

    assert check_draft(draft, TERMS) == [
        "keep_evidence: must be deny, because it follows from an earlier deny"
    ]


def test_facts_denied_but_summary_allowed_is_refused():
    draft = good_draft()
    draft["purposes"]["collect_facts"] = answer("deny", 'Row 2: "Automatisierte Zugriffe sind untersagt." (§7)')

    assert check_draft(draft, TERMS) == [
        "keep_evidence: must be deny, because it follows from an earlier deny",
        "write_summary: must be deny, because it follows from an earlier deny",
    ]
