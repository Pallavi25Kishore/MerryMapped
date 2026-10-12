from dataclasses import FrozenInstanceError

import pytest

from app.rules.decision import Basis, Decision


def make_decision():
    return Decision(
        allowed=False,
        reason="The site's terms forbid bots",
        basis=Basis.SITE_TERMS,
        citation='"Automatisierte Zugriffe sind untersagt" (AGB §4)',
    )


def test_decision_can_be_filled_in():
    decision = make_decision()

    assert decision.allowed is False
    assert decision.reason == "The site's terms forbid bots"
    assert decision.basis == Basis.SITE_TERMS
    assert decision.citation == '"Automatisierte Zugriffe sind untersagt" (AGB §4)'


def test_decision_needs_every_box():
    with pytest.raises(TypeError):
        Decision(allowed=False, reason="No reason given", basis=Basis.SITE_TERMS)


def test_decision_cannot_be_changed():
    decision = make_decision()

    with pytest.raises(FrozenInstanceError):
        decision.allowed = True
