import pytest

from app.rules.purposes import Purpose


def test_valid_purpose_is_accepted():
    assert Purpose("collect_facts") == Purpose.COLLECT_FACTS


def test_typo_is_rejected():
    with pytest.raises(ValueError):
        Purpose("collect_fact")


def test_there_are_exactly_six_purposes():
    assert len(Purpose) == 6
