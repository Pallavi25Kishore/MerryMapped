from app.rules.decision import Basis, Decision
from app.rules.purposes import Purpose


def can(purpose: Purpose, site_rules=None) -> Decision:
    """Decide whether MerryMapped may use a site for a purpose.

    site_rules is the site's approved decision file, or None if nobody has
    reviewed the site yet. Rules are checked in order; the first that applies decides.
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

    # Rule 3: nobody has reviewed this site yet, so nothing else is allowed.
    if site_rules is None:
        return Decision(
            allowed=False,
            reason="Nobody has reviewed this site's terms yet",
            basis=Basis.NOT_REVIEWED,
            citation="No approved decision file for this site",
        )

    # Last rule: default no. Nothing above allowed this purpose.
    return Decision(
        allowed=False,
        reason="No approved rule allows this purpose",
        basis=Basis.NOT_REVIEWED,
        citation="Default no: denied unless allowed by an engine rule or the admin-approved site decision file",
    )
