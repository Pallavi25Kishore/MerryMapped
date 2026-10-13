import json
from dataclasses import dataclass
from pathlib import Path

import anthropic

from app.reading.market_reader import TAGS
from app.reading.terms_finder import simplify
from app.settings import FACT_VERIFIER_MODEL

VERIFIER_PROMPT = Path(__file__).resolve().parents[2] / "prompts" / "fact_verifier.md"

NULLABLE_TEXT = {"anyOf": [{"type": "string"}, {"type": "null"}]}
VERDICT = {
    "type": "object",
    "properties": {
        "id": {"type": "integer"},
        "verdict": {"type": "string", "enum": ["supported", "partly", "unsupported"]},
        "trimmed": NULLABLE_TEXT,
        "reason": NULLABLE_TEXT,
    },
    "required": ["id", "verdict", "trimmed", "reason"],
    "additionalProperties": False,
}
VERDICTS_SCHEMA = {
    "type": "object",
    "properties": {"verdicts": {"type": "array", "items": VERDICT}},
    "required": ["verdicts"],
    "additionalProperties": False,
}


@dataclass(frozen=True)
class Verified:
    """The verifier's outcome: facts to keep (some trimmed), plus everything for the run report."""

    facts: list[dict]                # kept, in their original order
    trimmed: list[tuple[str, str]]   # (detail as it was, detail as trimmed)
    dropped: list[tuple[dict, str]]  # (fact, reason)
    unverified: list[dict]           # kept without a verdict: no quote to check, or none given


def verify_facts(facts: list[dict], client=None, model: str = FACT_VERIFIER_MODEL) -> Verified:
    """A second AI reads each fact against its own quote; code applies the verdicts."""
    to_check = [fact for fact in facts if fact.get("evidence_quote")]
    verdicts = ask_verifier(to_check, client, model) if to_check else {}
    kept, trimmed, dropped, unverified = [], [], [], []
    for fact in facts:
        verdict = verdicts.get(id(fact))
        if verdict is None:                      # no quote kept, or the verifier skipped it
            unverified.append(fact)
            kept.append(fact)
        elif verdict["verdict"] == "supported":
            kept.append(fact)
        elif verdict["verdict"] == "partly" and fact["kind"] == "detail" \
                and only_removes_words(verdict["trimmed"], fact["value"]["text"]):
            kept.append({**fact, "value": {"text": verdict["trimmed"]}})
            trimmed.append((fact["value"]["text"], verdict["trimmed"]))
        else:
            dropped.append((fact, verdict["reason"] or "the quote does not support it"))
    return Verified(kept, trimmed, dropped, unverified)


def ask_verifier(facts: list[dict], client, model: str) -> dict[int, dict]:
    """One request with every fact numbered; the answers, keyed by the fact they belong to."""
    client = client or anthropic.Anthropic()
    response = client.messages.create(
        model=model, max_tokens=4000, system=VERIFIER_PROMPT.read_text(encoding="utf-8"),
        output_config={"format": {"type": "json_schema", "schema": VERDICTS_SCHEMA}},
        messages=[{"role": "user", "content": facts_message(facts)}],
    )
    reply = next(block.text for block in response.content if block.type == "text")
    by_number = dict(enumerate(facts, start=1))
    return {id(by_number[v["id"]]): v for v in json.loads(reply)["verdicts"] if v["id"] in by_number}


def facts_message(facts: list[dict]) -> str:
    """Each fact numbered and wrapped, with its value, its quote and, for tags, the tag's meaning."""
    wrapped = []
    for number, fact in enumerate(facts, start=1):
        lines = [f'<fact id="{number}" kind="{fact["kind"]}">',
                 f"value: {json.dumps(fact['value'], ensure_ascii=False)}",
                 f"quote: {fact['evidence_quote']}"]
        if fact["kind"] == "tag":
            lines.append(f"meaning: {TAGS[fact['value']['tag']]}")
        wrapped.append("\n".join(lines + ["</fact>"]))
    return "Check each fact against its own quote.\n\n" + "\n\n".join(wrapped)


def only_removes_words(trimmed: str | None, original: str) -> bool:
    """A real trim: shorter, and every word in it was already in the original detail."""
    new, old = simplify(trimmed or "").split(), simplify(original).split()
    return 0 < len(new) < len(old) and set(new) <= set(old)
