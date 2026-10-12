from app.rules.decision import Basis, Decision
from app.rules.purposes import Purpose
from app.rules.site_review import SiteReview

# Purposes that need a bot or AI to read the site's pages.
NEEDS_READING = {Purpose.COLLECT_FACTS, Purpose.KEEP_EVIDENCE, Purpose.WRITE_SUMMARY}


def is_instagram(site: str) -> bool:
    """True for instagram.com and its subdomains, such as www.instagram.com."""
    return site == "instagram.com" or site.endswith(".instagram.com")


def can(site: str, purpose: Purpose, review: SiteReview | None = None) -> Decision:
    """Decide whether MerryMapped may use a site for a purpose.

    review is the site's admin-approved review, or None if nobody has reviewed
    the site yet. Rules are checked in order; the first that applies decides.
    """
    # Rule 1: app policy. Never copy descriptions or photos, whatever the site says.
    if purpose == Purpose.COPY_TEXT_OR_PHOTOS:
        return Decision(
            allowed=False,
            reason="MerryMapped never copies descriptions or photos",
            basis=Basis.APP_POLICY,
            citation="App policy: facts, short quotes and own-words summaries only",
        )

    # Rule 2: reading a site's rules is always allowed, so they can be reviewed.
    if purpose == Purpose.READ_TERMS:
        return Decision(
            allowed=True,
            reason="A site's rules must be read before they can be reviewed",
            basis=Basis.APP_POLICY,
            citation="App policy: robots.txt, the start page and up to 3 terms pages",
        )

    # Rule 3: Instagram is link-only. Its terms forbid automated collection.
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

    # Rule 4: nobody has reviewed this site yet, so nothing else is allowed.
    if review is None:
        return Decision(
            allowed=False,
            reason="Nobody has reviewed this site's terms yet",
            basis=Basis.NOT_REVIEWED,
            citation="No admin-approved site review for this site",
        )

    # Rule 5: the site's terms forbid bots, so no purpose that reads pages.
    if purpose in NEEDS_READING and review.automated_access.answer == "deny":
        return Decision(
            allowed=False,
            reason="The site's terms forbid bots",
            basis=Basis.SITE_TERMS,
            citation=review.automated_access.because,
        )

    # Rule 5b: evidence and summaries need the pages read, so collecting facts must be allowed.
    if purpose in {Purpose.KEEP_EVIDENCE, Purpose.WRITE_SUMMARY}:
        reading = can(site, Purpose.COLLECT_FACTS, review)
        if not reading.allowed:
            return Decision(
                allowed=False,
                reason=f"This site's pages may not be read: {reading.reason}",
                basis=reading.basis,
                citation=reading.citation,
            )

    # Rule 6: the review's answer for this purpose.
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
