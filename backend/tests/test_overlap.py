from app.reading.overlap import copied_phrases

PAGE = ("Over 140 festively decorated stalls offering arts and crafts, gifts and gastronomy. "
        "The market stands in front of the cathedral.")


def test_own_words_pass():
    assert copied_phrases("Around 140 stalls sell crafts and food beside the cathedral.", [PAGE]) == []


def test_a_copied_run_of_six_words_is_caught():
    text = "Expect festively decorated stalls offering arts and more."

    assert copied_phrases(text, [PAGE]) == ["festively decorated stalls offering arts and"]


def test_five_shared_words_pass():
    assert copied_phrases("It sits in front of the cathedral square.", [PAGE]) == []


def test_a_longer_copy_is_reported_as_one_phrase():
    text = "Here you find over 140 festively decorated stalls offering arts today."

    assert copied_phrases(text, [PAGE]) == ["over 140 festively decorated stalls offering arts"]


def test_punctuation_capitals_and_accents_do_not_hide_a_copy():
    page = "Der Markt liegt direkt am Kölner Dom, mitten in der Stadt."

    assert copied_phrases("der markt liegt direkt am kolner dom", [page]) == [
        "der markt liegt direkt am kolner dom"
    ]


def test_a_copy_from_any_page_is_caught():
    other = "Mulled wine is served at the central fountain every evening."

    assert copied_phrases("Mulled wine is served at the central fountain.", [PAGE, other]) == [
        "mulled wine is served at the central fountain"
    ]
