"""Hotspot tool."""
from __future__ import annotations

from datetime import UTC, datetime

from hydropinpoint.config import DEFAULT_BOX
from hydropinpoint.contracts import BoundingBox, ToolResult
from hydropinpoint.pipeline import IntegrationUnavailableError, run


def hotspots(box: BoundingBox = DEFAULT_BOX, top: int | None = None) -> ToolResult:
    try:
        result = run(box)
    except IntegrationUnavailableError as exc:
        return ToolResult(
            value=None, source="HydroPinpoint pipeline", fetched_at=datetime.now(UTC), error=str(exc)
        )
    ranked = sorted(result.hotspots, key=lambda row: row.susceptibility_rank)
    if top is not None:
        ranked = ranked[:top]
    sizings = {row.hotspot_id: row for row in result.sizings}
    value = [
        {
            **row.model_dump(mode="json"),
            "drain_sizing": sizings[row.id].model_dump(mode="json"),
        }
        for row in ranked
    ]
    return ToolResult(
        value=value,
        source=f"HydroPinpoint pipeline; rainfall: {result.rainfall.source}",
        fetched_at=result.generated_at,
        error="; ".join(result.notes) or None,
    )

