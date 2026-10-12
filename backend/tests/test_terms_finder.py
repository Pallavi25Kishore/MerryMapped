from app.reading.clean import CleanPage, Link
from app.reading.terms_finder import find_terms_pages

START = "https://www.weihnachtsmarkt-koeln.de/"
SITE = "https://www.weihnachtsmarkt-koeln.de"


def page_with(*links):
    """A cleaned start page with these (text, address) links."""
    return CleanPage("Start", "", tuple(Link(text, url) for text, url in links))


def test_finds_an_impressum():
    page = page_with(("Programm", f"{SITE}/programm"), ("Impressum", f"{SITE}/impressum"))

    assert find_terms_pages(page, START) == [f"{SITE}/impressum"]


def test_terms_of_use_come_first():
    page = page_with(
        ("Impressum", f"{SITE}/impressum"),
        ("Datenschutz", f"{SITE}/datenschutz"),
        ("AGB", f"{SITE}/agb"),
    )

    assert find_terms_pages(page, START) == [
        f"{SITE}/agb", f"{SITE}/impressum", f"{SITE}/datenschutz",
    ]


def test_at_most_three():
    page = page_with(
        ("AGB", f"{SITE}/agb"),
        ("Nutzungsbedingungen", f"{SITE}/nutzungsbedingungen"),
        ("Impressum", f"{SITE}/impressum"),
        ("Disclaimer", f"{SITE}/disclaimer"),
        ("Datenschutz", f"{SITE}/datenschutz"),
    )

    assert len(find_terms_pages(page, START)) == 3


def test_other_sites_are_ignored():
    page = page_with(("Ticket-AGB", "https://tickets-shop.de/agb"), ("Impressum", f"{SITE}/impressum"))

    assert find_terms_pages(page, START) == [f"{SITE}/impressum"]


def test_french_and_dutch_words():
    page = page_with(
        ("Mentions légales", f"{SITE}/mentions-legales"),
        ("CGU", f"{SITE}/cgu"),
        ("Algemene voorwaarden", f"{SITE}/nl/voorwaarden"),
    )

    assert find_terms_pages(page, START) == [
        f"{SITE}/cgu", f"{SITE}/nl/voorwaarden", f"{SITE}/mentions-legales",
    ]


def test_matches_the_address_alone():
    page = page_with(("Rechtliches", f"{SITE}/de/agb.html"))

    assert find_terms_pages(page, START) == [f"{SITE}/de/agb.html"]


def test_no_false_matches():
    page = page_with(("Tagblatt", f"{SITE}/tagblatt"), ("Stages", f"{SITE}/stages"))

    assert find_terms_pages(page, START) == []


def test_one_page_of_two_kinds_is_counted_once():
    page = page_with(("Impressum & Datenschutz", f"{SITE}/impressum-datenschutz"))

    assert find_terms_pages(page, START) == [f"{SITE}/impressum-datenschutz"]


def test_nothing_found_gives_an_empty_list():
    page = page_with(("Programm", f"{SITE}/programm"), ("Anfahrt", f"{SITE}/anfahrt"))

    assert find_terms_pages(page, START) == []
