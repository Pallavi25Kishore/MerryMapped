from app.reading.terms_finder import simplify

# A run of more than this many words in a row, shared with a page, counts as copied wording.
MAX_SHARED_WORDS = 5


def copied_phrases(text: str, pages: list[str]) -> list[str]:
    """Every run of 6 or more words in a row that the text shares with any page; empty means it passed."""
    words = simplify(text).split()
    page_texts = [simplify(page) for page in pages]
    size = MAX_SHARED_WORDS + 1
    copied, run_start, run_end = [], None, None
    for start in range(len(words) - size + 1):
        window = " " + " ".join(words[start:start + size]) + " "
        if any(window in page for page in page_texts):
            if run_end is not None and start <= run_end:   # overlaps the run we're in: extend it
                run_end = start + size
            else:                                          # a new run
                if run_start is not None:
                    copied.append(" ".join(words[run_start:run_end]))
                run_start, run_end = start, start + size
    if run_start is not None:
        copied.append(" ".join(words[run_start:run_end]))
    return copied
