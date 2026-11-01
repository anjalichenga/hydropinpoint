"""Readable LangGraph workflow for planning, execution, validation and writing."""
from __future__ import annotations

import json
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from typing import Any, TypedDict

from hydropinpoint.config import (
    AGENT_TIMEOUT_S,
    GEMINI_API_KEY,
    GEMINI_FALLBACK_MODEL,
    GEMINI_MODEL,
    MAX_VALIDATOR_ATTEMPTS,
)
from hydropinpoint.contracts import ToolResult
from hydropinpoint.tools.about import about
from hydropinpoint.tools.facilities import facilities
from hydropinpoint.tools.hotspots import hotspots
from hydropinpoint.tools.replay import replay
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
    explanatory = any(
        phrase in question
        for phrase in (
            "what is hydropinpoint",
            "how does",
            "how do you",
            "explain",
            "methodology",
            "architecture",
            "limitation",
            "accuracy",
            "reliable",
            "data source",
        )
    )
    requests_ranked_data = any(
        word in question for word in ("show", "list", "top", "current", "today", "which", "where")
    )
    if explanatory and not requests_ranked_data:
        return {
            **state,
            "tasks": [{"name": "about"}],
            "attempts": state.get("attempts", 0),
            "status": "planned",
        }
    scenario = re.search(r"(\d+(?:\.\d+)?)\s*mm\s*/?\s*h", question)
    if scenario:
        tasks.append({"name": "scenario", "mm_per_h": float(scenario.group(1))})
    if any(word in question for word in ("replay", "historical", "2022")):
        tasks.append({"name": "replay"})
    if any(word in question for word in ("ward", "pump")):
        tasks.extend(({"name": "hotspots", "top": 5}, {"name": "wards"}))
    if "route" in question or ("hospital" in question and "shelter" in question):
        tasks.append({"name": "route"})
    elif any(word in question for word in ("hospital", "shelter", "facility")):
        tasks.append({"name": "facilities"})
    hotspot_terms = (
        "hotspot",
        "flood risk",
        "vulnerable",
        "runoff",
        "drain",
        "diameter",
        "catchment",
        "current rainfall",
        "live rainfall",
        "top area",
    )
    if any(term in question for term in hotspot_terms):
        tasks.append({"name": "hotspots", "top": 5})
    if not tasks:
        tasks.append({"name": "about"})
    unique = list({json.dumps(task, sort_keys=True): task for task in tasks}.values())
    return {**state, "tasks": unique, "attempts": state.get("attempts", 0), "status": "planned"}


def _execute(task: dict[str, Any]) -> ToolResult:
    name = task["name"]
    if name == "about":
        return about()
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
    if name == "replay":
        return replay()
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


def _source_based_answer(question: str, results: list[ToolResult]) -> str:
    lowered = question.lower()
    documentation = next(
        (
            result.value
            for result in results
            if result.source == "HydroPinpoint project documentation"
        ),
        None,
    )
    if isinstance(documentation, dict):
        if any(word in lowered for word in ("limitation", "reliable", "accuracy")):
            limitations = " ".join(documentation["limitations"])
            replay_result = documentation["historical_replay"]
            return (
                f"{limitations} In the historical replay, the hit rate was "
                f"{replay_result['model_hit_rate_percent']}% compared with a "
                f"{replay_result['random_baseline_percent']}% random baseline."
            )
        if any(word in lowered for word in ("how", "method", "workflow", "work")):
            return "HydroPinpoint works in five stages: " + "; ".join(
                documentation["workflow"]
            )
        return f"{documentation['purpose']} {documentation['agent']}"

    hotspot_result = next(
        (
            result
            for result in results
            if result.source.startswith("HydroPinpoint pipeline")
            and isinstance(result.value, list)
        ),
        None,
    )
    if hotspot_result is not None:
        rows = [
            "| Priority | Hotspot | Peak runoff (m³/s) | Required drain (m) | Capacity |",
            "|---:|---:|---:|---:|---|",
        ]
        for item in hotspot_result.value:
            sizing = item["drain_sizing"]
            rows.append(
                f"| {item['susceptibility_rank']} | {item['id']} | "
                f"{item['peak_Q_m3s']} | {sizing['peak_required_D_m']} | "
                f"{sizing['capacity_note']} |"
            )
        return "Here are the highest-priority screening results:\n\n" + "\n".join(rows)

    scenario_result = next(
        (result for result in results if "design-storm scenario" in result.source.lower()),
        None,
    )
    if scenario_result is not None and isinstance(scenario_result.value, dict):
        intensity = scenario_result.value["cells"][0]["mm_per_h"][0]
        return (
            f"This is a SCENARIO using {intensity} mm/h rainfall. It is a user-entered "
            "design assumption, not a live forecast."
        )

    replay_result = next(
        (
            result
            for result in results
            if isinstance(result.value, dict) and "report" in result.value
        ),
        None,
    )
    if replay_result is not None:
        return str(replay_result.value["report"])

    route_result = next(
        (
            result.value
            for result in results
            if isinstance(result.value, dict) and "route" in result.value
        ),
        None,
    )
    if isinstance(route_result, dict):
        route_data = route_result["route"]
        return (
            f"The route connects {route_result['shelter']['name']} to "
            f"{route_result['hospital']['name']}. Distance: "
            f"{route_data['distance_m']} m. Duration: {route_data['duration_s']} seconds."
        )

    facility_result = next(
        (
            result.value
            for result in results
            if isinstance(result.value, list)
            and result.value
            and isinstance(result.value[0], dict)
            and "kind" in result.value[0]
        ),
        None,
    )
    if isinstance(facility_result, list):
        rows = ["| Facility | Type | Latitude | Longitude |", "|---|---|---:|---:|"]
        for item in facility_result[:8]:
            rows.append(
                f"| {item['name']} | {item['kind']} | {item['lat']} | {item['lon']} |"
            )
        return "Here are the mapped facilities available from OSM:\n\n" + "\n".join(rows)

    sources = "; ".join(result.source for result in results)
    return f"I could not produce a detailed answer, but the available sources were: {sources}."


def reasoner(state: AgentState) -> AgentState:
    usable = [result for result in state["results"] if result.value is not None]
    context = [result.model_dump(mode="json") for result in usable]
    if not usable:
        draft = "Data unavailable. " + "; ".join(state.get("issues", []))
    elif GEMINI_API_KEY:
        from google import genai
        from google.genai import types

        prompt = (
            "You are HydroPinpoint, a screening assistant, not a flood predictor. "
            "Answer the user's question directly and concisely using only the JSON tool "
            "outputs. Copy numeric values exactly as supplied; do not calculate, estimate, "
            "or invent values. Cite the source and fetched_at timestamp beside each numeric "
            "claim. Never claim surcharge or a capacity ratio. Clearly label scenarios and "
            "state that existing capacity is unknown when no mapped size is present. "
            "Start with a one-sentence takeaway. When comparing multiple records, use one "
            "compact Markdown table with short human-readable headings and units in the "
            "headings. Sort hotspots by susceptibility rank (highest priority first), routes "
            "by distance, and other rows by relevance. Show at most 8 rows and put details "
            "after the table. Do not output JSON.\nQuestion: "
            + state["question"]
            + "\nTool outputs: "
            + json.dumps(context, ensure_ascii=False)
        )
        client = genai.Client(
            api_key=GEMINI_API_KEY,
            http_options=types.HttpOptions(timeout=AGENT_TIMEOUT_S * 1000),
        )
        models = tuple(
            dict.fromkeys(("gemini-2.5-flash-lite", GEMINI_MODEL, GEMINI_FALLBACK_MODEL))
        )
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
            draft = _source_based_answer(state["question"], usable)
    else:
        draft = _source_based_answer(state["question"], usable)
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
