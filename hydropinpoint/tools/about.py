"""Fast, local project-context tool for general assistant questions."""
from datetime import UTC, datetime

from hydropinpoint.contracts import ToolResult


def about() -> ToolResult:
    return ToolResult(
        value={
            "name": "HydroPinpoint",
            "purpose": (
                "An explainable urban flood-screening and drainage-sizing prototype "
                "for Bengaluru; it is not an operational flood forecast."
            ),
            "workflow": [
                "Detect terrain depressions and micro-catchments from Copernicus DEM.",
                "Estimate imperviousness from ESA WorldCover.",
                "Apply Open-Meteo rainfall and the Rational Method to estimate runoff.",
                "Use Manning's equation to estimate required circular drain diameter.",
                "Present ranked hotspots on a Streamlit and OpenStreetMap interface.",
            ],
            "agent": (
                "LangGraph plans tool calls, validates results, asks Gemini to answer, "
                "and checks numeric claims against tool outputs."
            ),
            "limitations": [
                "DEM buildings and vegetation can create false depressions.",
                "Rainfall grids can miss street-level cloudbursts.",
                "Existing drain capacity is unknown when OSM has no width or diameter.",
                "Results are screening evidence, not emergency advice.",
            ],
            "historical_replay": {
                "event": "Bengaluru flooding on 5 September 2022",
                "model_hit_rate_percent": 42.9,
                "matched_localities": 3,
                "reported_localities": 7,
                "random_baseline_percent": 8.1,
                "signal_to_random": 5.26,
            },
        },
        source="HydroPinpoint project documentation",
        fetched_at=datetime.now(UTC),
    )
