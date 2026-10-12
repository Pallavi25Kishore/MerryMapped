from app.rules.decision import Basis
from app.rules.engine import can
from app.rules.purposes import Purpose
from app.rules.site_review import SiteReview

SITE = "weihnachtsmarkt-koeln.de"
BOTS_CLAUSE = '"Automatisierte Zugriffe sind untersagt" (AGB §4)'


def make_review(automated_access="allow", **purposes):
    """Build a review in one line, e.g. make_review(collect_facts="allow")."""
    return SiteReview.model_validate({
        "reviewed_on": "2026-10-20",
        "terms_urls": ["https://weihnachtsmarkt-koeln.de/nutzungsbedingungen"],
        "automated_access": {"answer": automated_access, "because": BOTS_CLAUSE},
        "purposes": {
            name: {"answer": answer, "because": f"Clause about {name}"}
            for name, answer in purposes.items()
        },
    })


# Rules 1, 2 and 4: app policy and not reviewed

def test_copying_is_always_denied():
    decision = can(SITE, Purpose.COPY_TEXT_OR_PHOTOS)

    assert decision.allowed is False
    assert decision.basis == Basis.APP_POLICY


def test_reading_terms_is_allowed_before_review():
    decision = can(SITE, Purpose.READ_TERMS)

    assert decision.allowed is True
    assert decision.basis == Basis.APP_POLICY


def test_collecting_facts_is_denied_before_review():
    decision = can(SITE, Purpose.COLLECT_FACTS)

    assert decision.allowed is False
    assert decision.basis == Basis.NOT_REVIEWED


def test_only_reading_terms_is_allowed_before_review():
    for purpose in Purpose:
        decision = can(SITE, purpose)
        assert decision.allowed is (purpose == Purpose.READ_TERMS)


# Rule 3: Instagram is link-only

def test_instagram_link_is_allowed():
    assert can("instagram.com", Purpose.SHOW_LINK).allowed is True


def test_instagram_collecting_is_denied_even_if_a_review_allows_it():
    decision = can("instagram.com", Purpose.COLLECT_FACTS, make_review(collect_facts="allow"))

    assert decision.allowed is False
    assert decision.basis == Basis.APP_POLICY


def test_instagram_subdomains_count_but_lookalikes_do_not():
    assert can("www.instagram.com", Purpose.COLLECT_FACTS).basis == Basis.APP_POLICY
    assert can("notinstagram.com", Purpose.COLLECT_FACTS).basis == Basis.NOT_REVIEWED


# Rule 5: bots forbidden

def test_bots_forbidden_overrides_the_purpose_line():
    review = make_review(automated_access="deny", collect_facts="allow", keep_evidence="allow")
    decision = can(SITE, Purpose.KEEP_EVIDENCE, review)

    assert decision.allowed is False
    assert decision.citation == BOTS_CLAUSE


def test_bots_forbidden_does_not_affect_links():
    review = make_review(automated_access="deny", show_link="allow")

    assert can(SITE, Purpose.SHOW_LINK, review).allowed is True


# Rule 5b: evidence and summaries need collecting facts

def test_summary_is_denied_when_collecting_is_denied():
    review = make_review(collect_facts="deny", write_summary="allow")

    assert can(SITE, Purpose.WRITE_SUMMARY, review).allowed is False


def test_summary_is_denied_when_collecting_has_no_line():
    review = make_review(write_summary="allow")

    assert can(SITE, Purpose.WRITE_SUMMARY, review).allowed is False


def test_summary_is_allowed_when_both_are_allowed():
    review = make_review(collect_facts="allow", write_summary="allow")

    assert can(SITE, Purpose.WRITE_SUMMARY, review).allowed is True


# Rule 6: the review's answer, and the default no

def test_review_allow_gives_yes_with_its_citation():
    decision = can(SITE, Purpose.COLLECT_FACTS, make_review(collect_facts="allow"))

    assert decision.allowed is True
    assert decision.basis == Basis.SITE_TERMS
    assert decision.citation == "Clause about collect_facts"
    assert "2026-10-20" in decision.reason


def test_review_deny_gives_no():
    decision = can(SITE, Purpose.COLLECT_FACTS, make_review(collect_facts="deny"))

    assert decision.allowed is False


def test_missing_line_gives_default_no():
    decision = can(SITE, Purpose.SHOW_LINK, make_review(collect_facts="allow"))

    assert decision.allowed is False
    assert decision.basis == Basis.NOT_REVIEWED
