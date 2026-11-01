"""Shelter-to-hospital route tool."""
from __future__ import annotations

import math
from datetime import UTC, datetime

from hydropinpoint.config import DEFAULT_BOX
from hydropinpoint.contracts import BoundingBox, ToolResult
from hydropinpoint.fetch.routing import route as fetch_route
from hydropinpoint.tools.facilities import facilities


def _distance(a: dict, b: dict) -> float:
    return math.hypot(float(a["lat"]) - float(b["lat"]), float(a["lon"]) - float(b["lon"]))


def shelter_to_hospital(box: BoundingBox = DEFAULT_BOX) -> ToolResult:
    fetched = facilities(box)
    if fetched.value is None:
        return fetched
    shelters = [row for row in fetched.value if row["kind"] == "shelter"]
    hospitals = [row for row in fetched.value if row["kind"] == "hospital"]
    if not shelters or not hospitals:
        return ToolResult(
            value=None,
            source=fetched.source,
            fetched_at=fetched.fetched_at,
            cached=fetched.cached,
            error="no mapped shelter/hospital pair found in the selected area",
        )
    shelter, hospital = min(
        ((shelter, hospital) for shelter in shelters for hospital in hospitals),
        key=lambda pair: _distance(*pair),
    )
    routed = fetch_route(shelter["lat"], shelter["lon"], hospital["lat"], hospital["lon"])
    if routed.value is None:
        return routed
    routed.value = {"shelter": shelter, "hospital": hospital, "route": routed.value}
    routed.fetched_at = max(routed.fetched_at, fetched.fetched_at)
    return routed

