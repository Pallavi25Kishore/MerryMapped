import re

# The five answers every draft must give.
ANSWER_KEYS = ["automated_access", "collect_facts", "keep_evidence", "write_summary", "show_link"]

# Clause guide rows that decide answers (12 and 13 are "ignore", so never cited).
RULE_ROWS = {"1", "2", "3", "4a", "4b", "5", "6", "6b", "7", "8", "9a", "9b", "10", "11"}

ROW_START = re.compile(r"^(Row|Follows from row) (\w+):")
QUOTED = re.compile(r'"([^"]+)"|„([^“"]+)[“"]|«\s*([^»]+?)\s*»')
SHORTENED = re.compile(r"\.\.\.|…")


def tidy(text: str) -> str:
    """Same spacing and quote marks everywhere, so formatting differences don't count."""
    for curly, plain in (("’", "'"), ("‘", "'"), ("“", '"'), ("”", '"'), ("„", '"')):
        text = text.replace(curly, plain)
    return " ".join(text.split())


def quote_found(quote: str, terms_text: str) -> bool:
    """True if the quote appears in the terms; a quote shortened with ... must match part by part, in order."""
    terms, position = tidy(terms_text), 0
    for part in SHORTENED.split(quote):
        part = tidy(part)
        if part:
            position = terms.find(part, position)
            if position == -1:
                return False
            position += len(part)
    return True


def check_draft(draft: dict, terms_text: str) -> list[str]:
    """Every problem with an AI-drafted review; an empty list means it passed."""
    answers = {"automated_access": draft.get("automated_access"), **draft.get("purposes", {})}
    problems = []

    for key in ANSWER_KEYS:
        item = answers.get(key)
        if not item:
            problems.append(f"{key}: missing")
            continue
        because = item.get("because", "")
        start = ROW_START.match(because)
        if not start or start.group(2) not in RULE_ROWS:
            problems.append(f"{key}: 'because' must start with 'Row N:' or 'Follows from row N:'")
            continue
        quotes = [next(q for q in found if q) for found in QUOTED.findall(because)]
        if start.group(1) == "Row" and start.group(2) != "1" and not quotes:
            problems.append(f"{key}: row {start.group(2)} must quote the clause")
        for quote in quotes:
            if not quote_found(quote, terms_text):
                problems.append(f'{key}: quote not found in the terms: "{quote}"')

    def denied(key):
        return (answers.get(key) or {}).get("answer") == "deny"

    must_deny = set()
    if denied("automated_access"):
        must_deny |= {"collect_facts", "keep_evidence", "write_summary"}
    if denied("collect_facts"):
        must_deny |= {"keep_evidence", "write_summary"}
    for key in ANSWER_KEYS:
        if key in must_deny and answers.get(key) and not denied(key):
            problems.append(f"{key}: must be deny, because it follows from an earlier deny")

    return problems
