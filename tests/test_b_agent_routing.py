from datetime import UTC, datetime

from hydropinpoint.agent.graph import _source_based_answer, planner
from hydropinpoint.contracts import ToolResult
from hydropinpoint.tools.about import about


def test_general_question_uses_fast_local_context() -> None:
    state = planner({"question": "How does HydroPinpoint work?"})

    assert state["tasks"] == [{"name": "about"}]


def test_hotspot_question_limits_expensive_result_size() -> None:
    state = planner({"question": "Show the top flood risk hotspots"})

    assert state["tasks"] == [{"name": "hotspots", "top": 5}]


def test_unknown_question_does_not_run_terrain_pipeline() -> None:
    state = planner({"question": "What can I ask you?"})

    assert state["tasks"] == [{"name": "about"}]


def test_local_fallback_answers_method_question() -> None:
    answer = _source_based_answer("How does it work?", [about()])

    assert "terrain depressions" in answer
    assert "requested screening data is available" not in answer


def test_local_fallback_formats_hotspot_data() -> None:
    result = ToolResult(
        value=[
            {
                "id": 12,
                "susceptibility_rank": 1,
                "peak_Q_m3s": 0.4,
                "drain_sizing": {
                    "peak_required_D_m": 0.6,
                    "capacity_note": "existing capacity unknown",
                },
            }
        ],
        source="HydroPinpoint pipeline; rainfall: test",
        fetched_at=datetime.now(UTC),
    )

    answer = _source_based_answer("Show hotspots", [result])

    assert "| 1 | 12 | 0.4 | 0.6 |" in answer
