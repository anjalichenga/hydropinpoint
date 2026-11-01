"""BBMP ward-boundary fetcher."""
from __future__ import annotations

from hydropinpoint.config import DATAMEET_WARDS_URL
from hydropinpoint.contracts import ToolResult
from hydropinpoint.fetch.cache import request_json

WARD_VINTAGE = "DataMeet BBMP ward boundaries; repository vintage not guaranteed"


def fetch_wards() -> ToolResult:
    result = request_json(
        url=DATAMEET_WARDS_URL,
        source=WARD_VINTAGE,
        namespace="datameet-wards",
    )
    if result.value is not None and result.value.get("type") != "FeatureCollection":
        result.value = None
        result.error = "ward source did not return a GeoJSON FeatureCollection"
    return result

