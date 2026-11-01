"""OpenStreetMap/Overpass fetcher for drainage and critical facilities."""
from __future__ import annotations

import os
import re
from datetime import UTC, datetime
from typing import Any

from hydropinpoint.config import OVERPASS_ENDPOINTS
from hydropinpoint.contracts import BoundingBox, ToolResult
from hydropinpoint.fetch.cache import (
    load_real_response,
    make_cache_key,
    request_json,
    save_real_response,
)


def _query(box: BoundingBox) -> str:
    bbox = f"{box.south},{box.west},{box.north},{box.east}"
    return f"""[out:json][timeout:25];(
      nwr[waterway~\"drain|ditch|canal\"]({bbox});
      nwr[tunnel=culvert]({bbox});
      nwr[natural=water]({bbox});
      nwr[water=reservoir]({bbox});
      nwr[amenity=hospital]({bbox});
      nwr[amenity=shelter]({bbox});
      nwr[social_facility=shelter]({bbox});
    );out center tags;"""


def _metres(value: Any) -> float | None:
    if value is None:
        return None
    text = str(value).strip().lower().replace(",", ".")
    match = re.search(r"(\d+(?:\.\d+)?)\s*(mm|cm|m|ft|feet|')?", text)
    if not match:
        return None
    number = float(match.group(1))
    unit = match.group(2) or "m"
    if unit == "mm":
        return number / 1000
    if unit == "cm":
        return number / 100
    if unit in {"ft", "feet", "'"}:
        return number * 0.3048
    return number


def _normalise(elements: list[dict[str, Any]]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for item in elements:
        tags = item.get("tags", {})
        center = item.get("center", {})
        lat = item.get("lat", center.get("lat"))
        lon = item.get("lon", center.get("lon"))
        if lat is None or lon is None:
            continue
        kind = "other"
        if tags.get("amenity") == "hospital":
            kind = "hospital"
        elif tags.get("amenity") == "shelter" or tags.get("social_facility") == "shelter":
            kind = "shelter"
        elif tags.get("natural") == "water" or tags.get("water") == "reservoir":
            kind = "waterbody"
        elif tags.get("tunnel") == "culvert":
            kind = "culvert"
        elif tags.get("waterway") in {"drain", "ditch", "canal"}:
            kind = "drain"
        size = _metres(tags.get("diameter")) or _metres(tags.get("width"))
        records.append(
            {
                "osm_type": item.get("type"),
                "osm_id": item.get("id"),
                "kind": kind,
                "name": tags.get("name") or tags.get("name:en") or f"Unnamed {kind}",
                "lat": float(lat),
                "lon": float(lon),
                "mapped_size_m": size,
                "tags": tags,
            }
        )
    return records


def fetch_osm(box: BoundingBox) -> ToolResult:
    query = _query(box)
    key = make_cache_key("osm", box.model_dump())
    errors: list[str] = []
    email = os.getenv("CONTACT_EMAIL", "contact-not-configured")
    headers = {
        "User-Agent": f"HydroPinpoint/0.1 ({email})",
        "Accept": "application/json",
    }
    for endpoint in OVERPASS_ENDPOINTS:
        result = request_json(
            url=endpoint,
            source=f"OpenStreetMap via {endpoint}",
            namespace="overpass",
            params={"data": query},
            headers=headers,
            cache_key=key,
            allow_cache_on_error=False,
            retries=1,
            timeout_s=6,
        )
        if result.error is None:
            value = _normalise(result.value.get("elements", []))
            save_real_response(key, value, result.source, result.fetched_at)
            result.value = value
            return result
        errors.append(f"{endpoint}: {result.error}")
    cached = load_real_response(key)
    if cached is not None:
        cached.error = "Live OSM lookup failed; using a saved real response."
        return cached
    return ToolResult(
        value=None,
        source="OpenStreetMap Overpass",
        fetched_at=datetime.now(UTC),
        error="OSM drainage lookup is temporarily unavailable; existing capacity is unknown.",
    )

