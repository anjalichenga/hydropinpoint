"""Hospital and shelter tool backed by live OpenStreetMap data."""
from __future__ import annotations

from hydropinpoint.config import DEFAULT_BOX
from hydropinpoint.contracts import BoundingBox, ToolResult
from hydropinpoint.fetch.osm import fetch_osm


def facilities(box: BoundingBox = DEFAULT_BOX) -> ToolResult:
    result = fetch_osm(box)
    if result.value is not None:
        result.value = [
            record for record in result.value if record.get("kind") in {"hospital", "shelter"}
        ]
    return result

