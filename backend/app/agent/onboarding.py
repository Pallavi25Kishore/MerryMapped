import json
from dataclasses import dataclass
from pathlib import Path

import anthropic

from app.agent.tools import TOOLS, AgentTools
from app.reading.fact_checks import drop_contradictions
from app.settings import ONBOARDING_AGENT_MODEL

AGENT_PROMPT = Path(__file__).resolve().parents[2] / "prompts" / "onboarding_agent.md"
MAX_ROUNDS = 15


@dataclass(frozen=True)
class Collected:
    """What the agent hands back: checked facts with their pages, plus everything for the run report."""

    facts: list[dict]
    dropped: list[tuple[str, dict, str]]  # (page, fact, reason)
    missing: list[str]
    steps: list[str]
    summary: str


def onboard(start_url: str, tools: AgentTools | None = None, client=None,
            model: str = ONBOARDING_AGENT_MODEL) -> Collected:
    """Let Claude navigate the market's site with the tools, then check all facts against each other."""
    client = client or anthropic.Anthropic()
    tools = tools or AgentTools(start_url, client=client)
    messages = [{"role": "user", "content":
                 f"The market's site starts at {start_url}. You have {tools.max_pages} pages."}]

    for _ in range(MAX_ROUNDS):
        response = client.messages.create(model=model, max_tokens=2000,
                                          system=AGENT_PROMPT.read_text(encoding="utf-8"),
                                          tools=TOOLS, messages=messages)
        messages.append({"role": "assistant", "content": response.content})
        calls = [block for block in response.content if block.type == "tool_use"]
        if not calls:
            break  # Claude answered in words instead of using a tool: the search is over
        messages.append({"role": "user", "content": [
            {"type": "tool_result", "tool_use_id": call.id,
             "content": json.dumps(run_tool(tools, call.name, call.input), ensure_ascii=False)}
            for call in calls
        ]})
        if tools.summary is not None or not tools.missing() or tools.pages_used >= tools.max_pages:
            break  # finished, everything found, or no pages left: code decides, not Claude

    facts, contradicted = drop_contradictions(once_each(tools.facts))
    return Collected(
        facts=facts,
        dropped=tools.dropped + [(fact["source_url"], fact, why) for fact, why in contradicted],
        missing=tools.missing(),
        steps=tools.steps,
        summary=tools.summary or "stopped by the guardrails",
    )


def run_tool(tools: AgentTools, name: str, given: dict) -> dict:
    """Carry out one tool request from Claude."""
    if name == "open_page":
        return tools.open_page(str(given.get("url", "")), str(given.get("reason", "")))
    if name == "finish":
        return tools.finish(str(given.get("summary", "")))
    return {"status": "refused", "why": f"there is no tool called {name}"}


def once_each(facts: list[dict]) -> list[dict]:
    """The same fact from several pages is kept once, from the first page that stated it."""
    seen, kept = set(), []
    for fact in facts:
        key = (fact["kind"], json.dumps(fact["value"], sort_keys=True))
        if key not in seen:
            seen.add(key)
            kept.append(fact)
    return kept
