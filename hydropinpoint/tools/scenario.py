"""Explicit, isolated design-storm scenario tool."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

from hydropinpoint.config import DEFAULT_BOX
from hydropinpoint.contracts import BoundingBox, RainCell, RainfallSeries, ToolResult


def scenario_rainfall(
    mm_per_h: float,
    hours: int = 1,
    box: BoundingBox = DEFAULT_BOX,
) -> ToolResult:
    if mm_per_h < 0 or hours < 1 or hours > 168:
        return ToolResult(
            value=None,
            source="User-entered design-storm scenario",
            fetched_at=datetime.now(UTC),
            error="mm_per_h must be non-negative and hours must be between 1 and 168",
        )
    now = datetime.now(UTC).replace(minute=0, second=0, microsecond=0)
    center_lat = (box.south + box.north) / 2
    center_lon = (box.west + box.east) / 2
    series = RainfallSeries(
        times=[now + timedelta(hours=index) for index in range(hours)],
        cells=[RainCell(lat=center_lat, lon=center_lon, mm_per_h=[mm_per_h] * hours)],
        source="User-entered design-storm scenario (ASSUMPTION)",
        fetched_at=now,
        grid_values_identical=True,
        label="SCENARIO",
    )
    return ToolResult(
        value=series.model_dump(mode="json"),
        source=series.source,
        fetched_at=now,
    )

