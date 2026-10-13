from urllib.parse import urlparse

from protego import Protego

from app.rules.decision import Basis, Decision
from app.rules.purposes import Purpose
from app.rules.site_review import SiteReview

# Purposes that need a bot or AI to read the site's pages.
NEEDS_READING = {Purpose.COLLECT_FACTS, Purpose.KEEP_EVIDENCE, Purpose.WRITE_SUMMARY}

# Purposes that download pages from the site.
FETCHES_PAGES = NEEDS_READING | {Purpose.READ_TERMS}

BOT_NAME = "MerryMappedBot"

# Well-known AI crawlers. A robots.txt block aimed at any of them also blocks us.
AI_BOT_NAMES = [
    "GPTBot", "ChatGPT-User", "ClaudeBot", "Claude-User", "anthropic-ai", "CCBot",
    "Google-Extended", "Applebot-Extended", "PerplexityBot", "Meta-ExternalAgent",
    "Bytespider", "cohere-ai",
]


def site_of(url: str) -> str:
    """The site an address belongs to, without a leading www."""
    host = urlparse(url).hostname or ""
    return host.removeprefix("www.")


def robots_note(page_url: str, robots_txt: str | None) -> str:
    """One line for people: what the site's robots.txt says about a page. The engine never reads it."""
    if robots_txt is None:
        return "could not be fetched, so every page counts as blocked"
    if robots_txt == "":
        return "no robots.txt, so no restrictions"
    rules = Protego.parse(robots_txt)
    us = "may" if rules.can_fetch(page_url, BOT_NAME) else "may NOT"
    blocked = [bot for bot in AI_BOT_NAMES if not rules.can_fetch(page_url, bot)]
    ai = f"AI bots blocked: {', '.join(blocked)}" if blocked else "no AI bots blocked"
    delay = rules.crawl_delay(BOT_NAME)
    pace = f"crawl delay {delay:g} seconds" if delay else "no crawl delay"
    return f"found; {BOT_NAME} {us} fetch the start page; {ai}; {pace}"


def is_instagram(site: str) -> bool:
    """True for instagram.com and its subdomains, such as www.instagram.com."""
    return site == "instagram.com" or site.endswith(".instagram.com")


def robots_check(url: str, robots_txt: str | None) -> Decision | None:
    """A No slip if robots.txt blocks this page for us or a well-known AI bot, else None.

    robots_txt is the file's text, "" if the site has none, or None if it could not be fetched.
    """
    path = urlparse(url).path or "/"
    if path == "/robots.txt":
        return None

    if robots_txt is None:
        return Decision(
            allowed=False,
            reason="The site's robots.txt could not be checked",
            basis=Basis.ROBOTS_TXT,
            citation="RFC 9309: if robots.txt is unreachable, treat every page as blocked",
        )

    rules = Protego.parse(robots_txt)
    for bot in [BOT_NAME, *AI_BOT_NAMES]:
        if not rules.can_fetch(url, bot):
            return Decision(
                allowed=False,
                reason=f"The site's robots.txt blocks this page for {bot}",
                basis=Basis.ROBOTS_TXT,
                citation=f"robots.txt: {bot} may not fetch {path}",
            )
    return None


def can(url: str, purpose: Purpose, review: SiteReview | None = None,
        robots_txt: str | None = None) -> Decision:
    """Decide whether MerryMapped may use a page for a purpose.

    review is the site's admin-approved review, or None if nobody has reviewed the site yet.
    robots_txt is the site's robots.txt text, "" if it has none, or None if it could not be
    fetched. Rules are checked in order; the first that applies decides.
    """
    site = site_of(url)

    # Rule 1: app policy. Never copy descriptions or photos, whatever the site says.
    if purpose == Purpose.COPY_TEXT_OR_PHOTOS:
        return Decision(
            allowed=False,
            reason="MerryMapped never copies descriptions or photos",
            basis=Basis.APP_POLICY,
            citation="App policy: facts, short quotes and own-words summaries only",
        )

    # Rule 2: robots.txt blocks this page (for us or a well-known AI bot).
    if purpose in FETCHES_PAGES:
        blocked = robots_check(url, robots_txt)
        if blocked is not None:
            return blocked

    # Rule 3: reading a site's rules is allowed, so they can be reviewed.
    if purpose == Purpose.READ_TERMS:
        return Decision(
            allowed=True,
            reason="A site's rules must be read before they can be reviewed",
            basis=Basis.APP_POLICY,
            citation="App policy: robots.txt, the start page and up to 3 terms pages",
        )

    # Rule 4: Instagram is link-only. Its terms forbid automated collection.
    if is_instagram(site):
        if purpose == Purpose.SHOW_LINK:
            return Decision(
                allowed=True,
                reason="Linking to Instagram is allowed",
                basis=Basis.APP_POLICY,
                citation="App policy: Instagram is link-only; linking to public pages "
                "is lawful (CJEU Svensson, C-466/12)",
            )
        return Decision(
            allowed=False,
            reason="MerryMapped only links to Instagram",
            basis=Basis.APP_POLICY,
            citation="App policy: Instagram's terms forbid automated collection, "
            "and posts contain personal data",
        )

    # Rule 5: nobody has reviewed this site yet, so nothing else is allowed.
    if review is None:
        return Decision(
            allowed=False,
            reason="Nobody has reviewed this site's terms yet",
            basis=Basis.NOT_REVIEWED,
            citation="No admin-approved site review for this site",
        )

    # Rule 6: the site's terms forbid bots, so no purpose that reads pages.
    if purpose in NEEDS_READING and review.automated_access.answer == "deny":
        return Decision(
            allowed=False,
            reason="The site's terms forbid bots",
            basis=Basis.SITE_TERMS,
            citation=review.automated_access.because,
        )

    # Rule 6b: evidence and summaries need the pages read, so collecting facts must be allowed.
    if purpose in {Purpose.KEEP_EVIDENCE, Purpose.WRITE_SUMMARY}:
        reading = can(url, Purpose.COLLECT_FACTS, review, robots_txt)
        if not reading.allowed:
            return Decision(
                allowed=False,
                reason=f"This site's pages may not be read: {reading.reason}",
                basis=reading.basis,
                citation=reading.citation,
            )

    # Rule 7: the review's answer for this purpose.
    answer = getattr(review.purposes, purpose.value)
    if answer is not None:
        verdict = "allows" if answer.answer == "allow" else "denies"
        return Decision(
            allowed=answer.answer == "allow",
            reason=f"Admin-approved review ({review.reviewed_on}) {verdict} this",
            basis=Basis.SITE_TERMS,
            citation=answer.because,
        )

    # Last rule: default no. Nothing above allowed this purpose.
    return Decision(
        allowed=False,
        reason="No approved rule allows this purpose",
        basis=Basis.NOT_REVIEWED,
        citation="Default no: denied unless allowed by an engine rule or the admin-approved site review",
    )
