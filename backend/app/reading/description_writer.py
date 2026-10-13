import json
import re
from pathlib import Path

import anthropic

from app.reading.market_reader import TAGS
from app.reading.overlap import copied_phrases
from app.settings import DESCRIPTION_WRITER_MODEL

DESCRIPTION_PROMPT = Path(__file__).resolve().parents[2] / "prompts" / "description_writer.md"
MAX_SENTENCES = 5
SENTENCE_END = re.compile(r"[.!?](\s|$)")
DESCRIPTION_SCHEMA = {
    "type": "object",
    "properties": {"description": {"type": "string"}},
    "required": ["description"],
    "additionalProperties": False,
}


class DescriptionFailed(Exception):
    """The description failed the checks twice; none is saved."""


def write_description(name: str, city: str, country: str, facts: list[dict], pages: list[str],
                      client=None, model: str = DESCRIPTION_WRITER_MODEL) -> str:
    """Write the market's description from its checked facts only; checked against every page read."""
    client = client or anthropic.Anthropic()
    messages = [{"role": "user", "content": facts_message(name, city, country, facts)}]
    for _ in range(2):  # the first try, plus one retry
        response = client.messages.create(
            model=model, max_tokens=1000, system=DESCRIPTION_PROMPT.read_text(encoding="utf-8"),
            output_config={"format": {"type": "json_schema", "schema": DESCRIPTION_SCHEMA}},
            messages=messages,
        )
        reply = next(block.text for block in response.content if block.type == "text")
        description = json.loads(reply)["description"].strip()
        problems = description_problems(description, pages)
        if not problems:
            return description
        messages.append({"role": "assistant", "content": reply})
        messages.append({"role": "user", "content":
            "The description failed these checks. Fix them and answer again:\n" + "\n".join(problems)})
    raise DescriptionFailed("; ".join(problems))


def description_problems(description: str, pages: list[str]) -> list[str]:
    """Every problem with a description; an empty list means it passed."""
    problems = []
    if not description:
        problems.append("the description is empty")
    sentences = len(SENTENCE_END.findall(description))
    if sentences > MAX_SENTENCES:
        problems.append(f"{sentences} sentences, at most {MAX_SENTENCES}")
    problems += [f'copied wording: "{phrase}"' for phrase in copied_phrases(description, pages)]
    return problems


def facts_message(name: str, city: str, country: str, facts: list[dict]) -> str:
    """The checked facts in plain English lines: values only, never the site's quotes."""
    def values(kind):
        return [fact["value"] for fact in facts if fact["kind"] == kind]

    lines = [f"Market: {name}, {city}, {country}"]
    if values("opening_date") and values("closing_date"):
        lines.append(f"Season: {values('opening_date')[0]['date']} to {values('closing_date')[0]['date']}")
    if closed := values("closed_on"):
        lines.append("Closed: " + ", ".join(value["date"] for value in closed))
    if where := values("address"):
        lines.append("Where: " + where[0]["text"])
    if details := values("detail"):
        lines.append("Details: " + "; ".join(value["text"] for value in details))
    if tags := values("tag"):
        lines.append("Features: " + "; ".join(TAGS[value["tag"]] for value in tags))
    return "Write the description from these facts.\n\n<market_facts>\n" + "\n".join(lines) + "\n</market_facts>"
