import json
import re
from dataclasses import dataclass
from pathlib import Path

import anthropic

from app.planning.checker import MarketInfo
from app.planning.plan import Plan, TripRequest
from app.reading.market_reader import TAGS
from app.settings import WISH_REVIEWER_MODEL

WISH_PROMPT = Path(__file__).resolve().parents[2] / "prompts" / "wish_reviewer.md"
VERDICTS = ["met", "partly_met", "not_met", "no_information"]
MIN_EVIDENCE = 3  # characters: shorter "evidence" proves nothing


@dataclass(frozen=True)
class WishNote:
    """How the plan meets one wish: a verdict (VERDICTS, or "not_covered" for what MerryMapped
    cannot do), the facts it rests on as (market id, text), and a note for the traveller."""
    wish: str
    verdict: str
    evidence: tuple[tuple[int, str], ...]
    note: str


def planned_ids(plan: Plan) -> list[int]:
    return list(dict.fromkeys(visit.market_id for day in plan.days for visit in day.visits))


def facts_of(market: MarketInfo) -> list[str]:
    """Every text a wish may be judged on: the description, the details and the tags."""
    texts = [fact["value"]["text"] for fact in market.facts if fact["kind"] == "detail"]
    texts += [fact["value"]["tag"] for fact in market.facts if fact["kind"] == "tag"]
    return texts + ([market.description] if market.description else [])


def tag_notes(tags: tuple[str, ...], plan: Plan, markets: dict[int, MarketInfo]) -> list[WishNote]:
    """Picked tags are judged in code: met if a planned market has the tag in its checked facts."""
    notes = []
    for tag in tags:
        having = [i for i in planned_ids(plan)
                  if any(f["kind"] == "tag" and f["value"]["tag"] == tag for f in markets[i].facts)]
        if having:
            names = ", ".join(markets[i].name for i in having)
            notes.append(WishNote(tag, "met", tuple((i, tag) for i in having), f"Tagged {tag}: {names}."))
        else:
            notes.append(WishNote(tag, "not_met", (), f"None of the planned markets is tagged {tag} "
                                                     f"({TAGS.get(tag, 'no meaning known')})."))
    return notes


def review_schema(market_ids: list[int]) -> dict:
    evidence = {"type": "object", "properties": {"market_id": {"type": "integer", "enum": market_ids},
                                                 "text": {"type": "string"}},
                "required": ["market_id", "text"], "additionalProperties": False}
    note = {"type": "object",
            "properties": {"wish": {"type": "string"}, "verdict": {"type": "string", "enum": VERDICTS},
                           "evidence": {"type": "array", "items": evidence}, "note": {"type": "string"}},
            "required": ["wish", "verdict", "evidence", "note"], "additionalProperties": False}
    return {"type": "object", "properties": {"wishes": {"type": "array", "items": note}},
            "required": ["wishes"], "additionalProperties": False}


def review_message(wishes: list[str], plan: Plan, markets: dict[int, MarketInfo]) -> str:
    days = []
    for day in plan.days:
        move = f"travel {day.travel.from_city} to {day.travel.to_city}" if day.travel else "no travel"
        back = f", back to {day.travel_back.to_city}" if day.travel_back else ""
        visited = ", ".join(f"{markets[v.market_id].name} (market {v.market_id})" for v in day.visits) or "no market"
        days.append(f"{day.day:%a %d %b}: {move}{back}; {visited}; sleep in {day.sleep_in}")
    facts = []
    for i in planned_ids(plan):
        market = markets[i]
        details = [f["value"]["text"] for f in market.facts if f["kind"] == "detail"]
        tags = [f["value"]["tag"] for f in market.facts if f["kind"] == "tag"]
        facts.append(f"Market {i}: {market.name} ({market.city})\nDescription: {market.description or 'none'}\n"
                     f"Tags: {', '.join(tags) or 'none'}\nDetails: {'; '.join(details) or 'none'}")
    wish_lines = "\n".join(f"- {wish}" for wish in wishes)
    return (f"<wishes>\n{wish_lines}\n</wishes>\n\n<plan>\n" + "\n".join(days) + "\n</plan>\n\n"
            "<market_facts>\n" + "\n\n".join(facts) + "\n</market_facts>")


def simplify(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().lower()


def checked(note: WishNote, plan: Plan, markets: dict[int, MarketInfo]) -> WishNote:
    """Keep only evidence found word for word in a planned market's facts. A met or partly met
    verdict left without evidence becomes no_information."""
    ids = set(planned_ids(plan))
    kept = tuple((i, text) for i, text in note.evidence
                 if i in ids and len(simplify(text)) >= MIN_EVIDENCE
                 and any(simplify(text) in simplify(fact) for fact in facts_of(markets[i])))
    if note.verdict in ("met", "partly_met") and not kept:
        return WishNote(note.wish, "no_information", (), "Our checked facts don't show this.")
    return WishNote(note.wish, note.verdict, kept, note.note)


def review_wishes(request: TripRequest, plan: Plan, markets: dict[int, MarketInfo],
                  not_covered: list[str] = (), client=None, model: str = WISH_REVIEWER_MODEL) -> list[WishNote]:
    """Notes on every picked tag (by code), every typed wish (by AI, evidence checked in code),
    and everything MerryMapped cannot do."""
    notes = tag_notes(request.tags, plan, markets)
    wishes = [wish.strip() for wish in request.wishes.split(";") if wish.strip()]
    if wishes:
        client = client or anthropic.Anthropic()
        response = client.messages.create(
            model=model, max_tokens=4000, system=WISH_PROMPT.read_text(encoding="utf-8"),
            output_config={"format": {"type": "json_schema", "schema": review_schema(planned_ids(plan))}},
            messages=[{"role": "user", "content": review_message(wishes, plan, markets)}],
        )
        reply = json.loads(next(block.text for block in response.content if block.type == "text"))
        for item in reply["wishes"]:
            note = WishNote(item["wish"], item["verdict"],
                            tuple((e["market_id"], e["text"]) for e in item["evidence"]), item["note"])
            notes.append(checked(note, plan, markets))
    notes += [WishNote(item, "not_covered", (), f"MerryMapped can't include this: {item}.") for item in not_covered]
    return notes
