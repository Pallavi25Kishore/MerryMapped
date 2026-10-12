from app.rules.decision import Basis
from app.rules.engine import can
from app.rules.purposes import Purpose
from app.rules.site_review import SiteReview

PAGE = "https://www.koeln-market.example/markt/termine"
INSTAGRAM = "https://www.instagram.com/example.market/"
NO_ROBOTS = ""  # the site has no robots.txt, so robots.txt restricts nothing
BOTS_CLAUSE = '"Automatisierte Zugriffe sind untersagt" (AGB §4)'


def make_review(automated_access="allow", **purposes):
    """Build a review in one line, e.g. make_review(collect_facts="allow")."""
    return SiteReview.model_validate({
        "reviewed_on": "2026-10-20",
        "terms_urls": ["https://koeln-market.example/nutzungsbedingungen"],
        "automated_access": {"answer": automated_access, "because": BOTS_CLAUSE},
        "purposes": {
            name: {"answer": answer, "because": f"Clause about {name}"}
            for name, answer in purposes.items()
        },
    })


# Rules 1, 3 and 5: app policy and not reviewed

def test_copying_is_always_denied():
    decision = can(PAGE, Purpose.COPY_TEXT_OR_PHOTOS, robots_txt=NO_ROBOTS)

    assert decision.allowed is False
    assert decision.basis == Basis.APP_POLICY


def test_reading_terms_is_allowed_before_review():
    decision = can(PAGE, Purpose.READ_TERMS, robots_txt=NO_ROBOTS)

    assert decision.allowed is True
    assert decision.basis == Basis.APP_POLICY


def test_collecting_facts_is_denied_before_review():
    decision = can(PAGE, Purpose.COLLECT_FACTS, robots_txt=NO_ROBOTS)

    assert decision.allowed is False
    assert decision.basis == Basis.NOT_REVIEWED


def test_only_reading_terms_is_allowed_before_review():
    for purpose in Purpose:
        decision = can(PAGE, purpose, robots_txt=NO_ROBOTS)
        assert decision.allowed is (purpose == Purpose.READ_TERMS)


# Rule 2: robots.txt

def test_robots_blocked_page_is_denied():
    robots = "User-agent: *\nDisallow: /markt/anmeldung\n"
    page = "https://koeln-market.example/markt/anmeldung"
    decision = can(page, Purpose.COLLECT_FACTS, make_review(collect_facts="allow"), robots)

    assert decision.allowed is False
    assert decision.basis == Basis.ROBOTS_TXT


def test_robots_leaves_other_pages_alone():
    robots = "User-agent: *\nDisallow: /markt/anmeldung\n"
    decision = can(PAGE, Purpose.COLLECT_FACTS, make_review(collect_facts="allow"), robots)

    assert decision.allowed is True


def test_robots_more_specific_line_wins():
    robots = "User-agent: *\nAllow: /\nDisallow: /markt/anmeldung\n"
    page = "https://koeln-market.example/markt/anmeldung"
    decision = can(page, Purpose.COLLECT_FACTS, make_review(collect_facts="allow"), robots)

    assert decision.allowed is False


def test_robots_block_on_an_ai_bot_also_blocks_us():
    robots = "User-agent: GPTBot\nDisallow: /\n"
    decision = can(PAGE, Purpose.COLLECT_FACTS, make_review(collect_facts="allow"), robots)

    assert decision.allowed is False
    assert "GPTBot" in decision.reason


def test_unreachable_robots_blocks_page_downloads():
    decision = can(PAGE, Purpose.COLLECT_FACTS, make_review(collect_facts="allow"), None)

    assert decision.allowed is False
    assert decision.basis == Basis.ROBOTS_TXT


def test_robots_txt_itself_can_always_be_read():
    robots_page = "https://koeln-market.example/robots.txt"

    assert can(robots_page, Purpose.READ_TERMS, robots_txt=None).allowed is True


def test_robots_also_limits_reading_terms():
    robots = "User-agent: *\nDisallow: /agb\n"
    decision = can("https://koeln-market.example/agb", Purpose.READ_TERMS, robots_txt=robots)

    assert decision.allowed is False
    assert decision.basis == Basis.ROBOTS_TXT


def test_robots_does_not_affect_links():
    robots = "User-agent: *\nDisallow: /\n"

    assert can(PAGE, Purpose.SHOW_LINK, make_review(show_link="allow"), robots).allowed is True


# Rule 4: Instagram is link-only

def test_instagram_link_is_allowed():
    assert can(INSTAGRAM, Purpose.SHOW_LINK).allowed is True


def test_instagram_collecting_is_denied_even_if_a_review_allows_it():
    decision = can(INSTAGRAM, Purpose.COLLECT_FACTS, make_review(collect_facts="allow"), NO_ROBOTS)

    assert decision.allowed is False
    assert decision.basis == Basis.APP_POLICY


def test_instagram_with_www_counts_but_lookalikes_do_not():
    lookalike = "https://notinstagram.example/weihnachtsmarkt"

    assert can(INSTAGRAM, Purpose.COLLECT_FACTS, robots_txt=NO_ROBOTS).basis == Basis.APP_POLICY
    assert can(lookalike, Purpose.COLLECT_FACTS, robots_txt=NO_ROBOTS).basis == Basis.NOT_REVIEWED


# Rule 6: bots forbidden in the terms

def test_bots_forbidden_overrides_the_purpose_line():
    review = make_review(automated_access="deny", collect_facts="allow", keep_evidence="allow")
    decision = can(PAGE, Purpose.KEEP_EVIDENCE, review, NO_ROBOTS)

    assert decision.allowed is False
    assert decision.citation == BOTS_CLAUSE


def test_bots_forbidden_does_not_affect_links():
    review = make_review(automated_access="deny", show_link="allow")

    assert can(PAGE, Purpose.SHOW_LINK, review, NO_ROBOTS).allowed is True


# Rule 6b: evidence and summaries need collecting facts

def test_summary_is_denied_when_collecting_is_denied():
    review = make_review(collect_facts="deny", write_summary="allow")

    assert can(PAGE, Purpose.WRITE_SUMMARY, review, NO_ROBOTS).allowed is False


def test_summary_is_denied_when_collecting_has_no_line():
    review = make_review(write_summary="allow")

    assert can(PAGE, Purpose.WRITE_SUMMARY, review, NO_ROBOTS).allowed is False


def test_summary_is_allowed_when_both_are_allowed():
    review = make_review(collect_facts="allow", write_summary="allow")

    assert can(PAGE, Purpose.WRITE_SUMMARY, review, NO_ROBOTS).allowed is True


# Rule 7 and the default no

def test_review_allow_gives_yes_with_its_citation():
    decision = can(PAGE, Purpose.COLLECT_FACTS, make_review(collect_facts="allow"), NO_ROBOTS)

    assert decision.allowed is True
    assert decision.basis == Basis.SITE_TERMS
    assert decision.citation == "Clause about collect_facts"
    assert "2026-10-20" in decision.reason


def test_review_deny_gives_no():
    decision = can(PAGE, Purpose.COLLECT_FACTS, make_review(collect_facts="deny"), NO_ROBOTS)

    assert decision.allowed is False


def test_missing_line_gives_default_no():
    decision = can(PAGE, Purpose.SHOW_LINK, make_review(collect_facts="allow"), NO_ROBOTS)

    assert decision.allowed is False
    assert decision.basis == Basis.NOT_REVIEWED
