"""OSRM route fetcher with graceful failure and saved-real-response fallback."""
from __future__ import annotations

from hydropinpoint.config import OSRM_URL
from hydropinpoint.contracts import ToolResult
from hydropinpoint.fetch.cache import request_json


def route(start_lat: float, start_lon: float, end_lat: float, end_lon: float) -> ToolResult:
    coordinates = f"{start_lon},{start_lat};{end_lon},{end_lat}"
    result = request_json(
        url=f"{OSRM_URL}/{coordinates}",
        source="OSRM demo server",
        namespace="osrm",
        params={"overview": "full", "geometries": "geojson", "steps": "false"},
        rate_limit_s=1.0,
    )
    if result.value is None:
        return result
    routes = result.value.get("routes", [])
    if not routes:
        result.value = None
        result.error = f"OSRM returned no route ({result.value})"
        return result
    first = routes[0]
    result.value = {
        "distance_m": first.get("distance"),
        "duration_s": first.get("duration"),
        "geometry": first.get("geometry"),
    }
    return result

