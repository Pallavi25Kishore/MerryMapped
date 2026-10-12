import re
import unicodedata
from urllib.parse import urlparse

from app.reading.clean import CleanPage
from app.rules.engine import site_of

MAX_TERMS_PAGES = 3

# Words that mark a terms page, most important kind first. Written without accents
# or punctuation, because link text and addresses are simplified the same way.
TERMS_WORDS = [
    # 1. Terms of use: the contract
    ["nutzungsbedingungen", "agb", "geschaftsbedingungen", "geschaeftsbedingungen",
     "cgu", "conditions d utilisation", "conditions generales",
     "gebruiksvoorwaarden", "algemene voorwaarden", "terms"],
    # 2. Legal notice: who runs the site
    ["impressum", "mentions legales", "colofon", "disclaimer", "legal notice"],
    # 3. Privacy policy
    ["datenschutz", "confidentialite", "privacyverklaring", "privacybeleid", "privacy"],
]


def simplify(text: str) -> str:
    """Lowercase, accents removed, and anything that isn't a letter or digit made a space."""
    plain = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower()
    return " " + " ".join(re.findall(r"[a-z0-9]+", plain)) + " "


def find_terms_pages(page: CleanPage, page_url: str) -> list[str]:
    """Up to 3 terms pages linked from a page on the same site, most important first."""
    site = site_of(page_url)
    found = []
    for words in TERMS_WORDS:
        for link in page.links:
            if site_of(link.url) != site or link.url in found:
                continue
            searched = simplify(link.text + " " + urlparse(link.url).path)
            if any(f" {word} " in searched for word in words):
                found.append(link.url)
    return found[:MAX_TERMS_PAGES]
