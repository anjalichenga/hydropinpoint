"""Readable LangGraph workflow for planning, execution, validation and writing."""
from __future__ import annotations

import json
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from typing import Any, TypedDict

from hydropinpoint.config import (
    GEMINI_API_KEY,
    GEMINI_FALLBACK_MODEL,
    GEMINI_MODEL,
    MAX_VALIDATOR_ATTEMPTS,
)
from hydropinpoint.contracts import ToolResult
from hydropinpoint.tools.facilities import facilities
from hydropinpoint.tools.hotspots import hotspots
from hydropinpoint.tools.route import shelter_to_hospital
from hydropinpoint.tools.scenario import scenario_rainfall
from hydropinpoint.tools.wards import wards


class AgentState(TypedDict, total=False):
    question: str
    tasks: list[dict[str, Any]]
    results: list[ToolResult]
    attempts: int
    issues: list[str]
    draft: str
    answer: str
    citations: list[dict[str, Any]]
    status: str


def planner(state: AgentState) -> AgentState:
    question = state["question"].lower()
    tasks: list[dict[str, Any]] = []
    scenario = re.search(r"(\d+(?:\.\d+)?)\s*mm\s*/?\s*h", question)
    if scenario:
        tasks.append({"name": "scenario", "mm_per_h": float(scenario.group(1))})
    if any(word in question for word in ("ward", "pump")):
        tasks.extend(({"name": "hotspots"}, {"name": "wards"}))
    if any(word in question for word in ("hospital", "shelter", "route")):
        tasks.extend(({"name": "hotspots", "top": 3}, {"name": "facilities"}))
    if "route" in question or ("hospital" in question and "shelter" in question):
        tasks.append({"name": "route"})
    if not tasks:
        tasks.append({"name": "hotspots", "top": 3})
    unique = list({json.dumps(task, sort_keys=True): task for task in tasks}.values())
    return {**state, "tasks": unique, "attempts": state.get("attempts", 0), "status": "planned"}


def _execute(task: dict[str, Any]) -> ToolResult:
    name = task["name"]
    if name == "hotspots":
        return hotspots(top=task.get("top"))
    if name == "wards":
        return wards()
    if name == "facilities":
        return facilities()
    if name == "route":
        return shelter_to_hospital()
    if name == "scenario":
        return scenario_rainfall(task["mm_per_h"])
    raise ValueError(f"unknown tool: {name}")


def executor(state: AgentState) -> AgentState:
    with ThreadPoolExecutor(max_workers=min(4, len(state["tasks"]))) as pool:
        results = list(pool.map(_execute, state["tasks"]))
    return {**state, "results": results, "status": "executed"}


def validator(state: AgentState) -> AgentState:
    issues: list[str] = []
    stale_before = datetime.now(UTC) - timedelta(hours=24)
    for result in state["results"]:
        if result.value is None:
            issues.append(result.error or f"{result.source}: data unavailable")
        if result.cached and result.fetched_at < stale_before:
            issues.append(f"{result.source}: cached data is older than 24 hours")
    return {
        **state,
        "attempts": state.get("attempts", 0) + 1,
        "issues": issues,
        "status": "validated",
    }


def _retry_or_reason(state: AgentState) -> str:
    if state.get("issues") and state.get("attempts", 0) < MAX_VALIDATOR_ATTEMPTS:
        return "retry"
    return "reason"


def _source_based_answer(results: list[ToolResult]) -> str:
    sources = "; ".join(
        f"{result.source} (fetched {result.fetched_at.isoformat()})" for result in results
    )
    return (
        "The requested screening data is available in the structured result. "
        f"Sources: {sources}. Existing drain capacity remains unknown unless a mapped "
        "size is shown."
    )


def reasoner(state: AgentState) -> AgentState:
    usable = [result for result in state["results"] if result.value is not None]
    context = [result.model_dump(mode="json") for result in usable]
    if not usable:
        draft = "Data unavailable. " + "; ".join(state.get("issues", []))
    elif GEMINI_API_KEY:
        from google import genai

        prompt = (
            "You are HydroPinpoint, a screening assistant, not a flood predictor. "
            "Answer the user's question directly and concisely using only the JSON tool "
            "outputs. Copy numeric values exactly as supplied; do not calculate, estimate, "
            "or invent values. Cite the source and fetched_at timestamp beside each numeric "
            "claim. Never claim surcharge or a capacity ratio. Clearly label scenarios and "
            "state that existing capacity is unknown when no mapped size is present. "
            "Use plain text, not JSON.\nQuestion: " + state["question"] + "\nTool outputs: "
            + json.dumps(context, ensure_ascii=False)
        )
        client = genai.Client(api_key=GEMINI_API_KEY)
        models = tuple(dict.fromkeys((GEMINI_MODEL, GEMINI_FALLBACK_MODEL)))
        draft = ""
        for model in models:
            try:
                response = client.models.generate_content(model=model, contents=prompt)
                draft = response.text or ""
            except Exception:
                continue
            if draft.strip():
                break
        if not draft.strip():
            draft = _source_based_answer(usable)
    else:
        draft = _source_based_answer(usable)
    return {**state, "draft": draft, "status": "reasoned"}


def writer(state: AgentState) -> AgentState:
    from hydropinpoint.agent.citation_checker import check_numbers

    answer, citations = check_numbers(state["draft"], state["results"])
    return {**state, "answer": answer, "citations": citations, "status": "complete"}


def build_graph():
    from langgraph.graph import END, StateGraph

    graph = StateGraph(AgentState)
    graph.add_node("planner", planner)
    graph.add_node("executor", executor)
    graph.add_node("validator", validator)
    graph.add_node("reasoner", reasoner)
    graph.add_node("writer", writer)
    graph.set_entry_point("planner")
    graph.add_edge("planner", "executor")
    graph.add_edge("executor", "validator")
    graph.add_conditional_edges(
        "validator", _retry_or_reason, {"retry": "executor", "reason": "reasoner"}
    )
    graph.add_edge("reasoner", "writer")
    graph.add_edge("writer", END)
    return graph.compile()


def ask(question: str) -> AgentState:
    return build_graph().invoke({"question": question, "attempts": 0, "status": "starting"})
