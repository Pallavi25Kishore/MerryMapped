from app.rules.decision import Basis
from app.rules.engine import can
from app.rules.purposes import Purpose


def test_copying_is_always_denied():
    decision = can(Purpose.COPY_TEXT_OR_PHOTOS)

    assert decision.allowed is False
    assert decision.basis == Basis.APP_POLICY


def test_reading_terms_is_allowed_before_review():
    decision = can(Purpose.READ_TERMS)

    assert decision.allowed is True
    assert decision.basis == Basis.APP_POLICY


def test_collecting_facts_is_denied_before_review():
    decision = can(Purpose.COLLECT_FACTS)

    assert decision.allowed is False
    assert decision.basis == Basis.NOT_REVIEWED


def test_only_reading_terms_is_allowed_before_review():
    for purpose in Purpose:
        decision = can(purpose)
        assert decision.allowed is (purpose == Purpose.READ_TERMS)
