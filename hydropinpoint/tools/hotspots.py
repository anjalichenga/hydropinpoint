"""Hotspot tool."""
from __future__ import annotations

from datetime import UTC, datetime

from hydropinpoint.config import DEFAULT_BOX
from hydropinpoint.contracts import BoundingBox, ToolResult
from hydropinpoint.pipeline import IntegrationUnavailableError, run_cached


def hotspots(box: BoundingBox = DEFAULT_BOX, top: int | None = None) -> ToolResult:
    try:
        result = run_cached(box)
    except IntegrationUnavailableError as exc:
        return ToolResult(
            value=None,
            source="HydroPinpoint pipeline",
            fetched_at=datetime.now(UTC),
            error=str(exc),
        )
    ranked = sorted(result.hotspots, key=lambda row: row.susceptibility_rank)
    if top is not None:
        ranked = ranked[:top]
    sizings = {row.hotspot_id: row for row in result.sizings}
    value = []
    for row in ranked:
        hotspot = row.model_dump(mode="json")
        hotspot["peak_Q_m3s"] = max(hotspot.pop("hourly_Q_m3s"), default=0.0)
        sizing = sizings[row.id].model_dump(mode="json")
        sizing["peak_required_D_m"] = max(
            sizing.pop("hourly_required_D_m"), default=0.0
        )
        value.append({**hotspot, "drain_sizing": sizing})
    return ToolResult(
        value=value,
        source=f"HydroPinpoint pipeline; rainfall: {result.rainfall.source}",
        fetched_at=result.generated_at,
        error="; ".join(result.notes) or None,
    )

