"""Nominatim geocoder with policy-compliant identity and Photon fallback."""
from __future__ import annotations

import os
from datetime import UTC, datetime
from typing import Any

from hydropinpoint.config import NOMINATIM_URL, PHOTON_URL, USER_AGENT
from hydropinpoint.contracts import ToolResult
from hydropinpoint.fetch.cache import make_cache_key, request_json


def _nominatim_records(value: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "name": row.get("display_name", "Unnamed result"),
            "lat": float(row["lat"]),
            "lon": float(row["lon"]),
            "type": row.get("type"),
        }
        for row in value
        if row.get("lat") is not None and row.get("lon") is not None
    ]


def _photon_records(value: dict[str, Any]) -> list[dict[str, Any]]:
    records = []
    for feature in value.get("features", []):
        coordinates = feature.get("geometry", {}).get("coordinates", [])
        if len(coordinates) < 2:
            continue
        props = feature.get("properties", {})
        records.append(
            {
                "name": props.get("name") or props.get("label") or "Unnamed result",
                "lat": float(coordinates[1]),
                "lon": float(coordinates[0]),
                "type": props.get("type") or props.get("osm_value"),
            }
        )
    return records


def geocode(query: str, limit: int = 5) -> ToolResult:
    key = make_cache_key("geocode", {"query": query, "limit": limit})
    email = os.getenv("CONTACT_EMAIL", "").strip()
    errors: list[str] = []
    if email:
        result = request_json(
            url=NOMINATIM_URL,
            source="OpenStreetMap Nominatim",
            namespace="nominatim",
            params={"q": query, "format": "jsonv2", "limit": limit, "email": email},
            headers={"User-Agent": USER_AGENT.format(email=email)},
            cache_key=key,
            rate_limit_s=1.0,
            allow_cache_on_error=False,
        )
        if result.error is None:
            result.value = _nominatim_records(result.value)
            return result
        errors.append(result.error)
    else:
        errors.append("CONTACT_EMAIL is unset; Nominatim skipped")

    photon = request_json(
        url=PHOTON_URL,
        source="Photon geocoder (Nominatim fallback)",
        namespace="photon",
        params={"q": query, "limit": limit},
        cache_key=key,
        rate_limit_s=1.0,
    )
    if photon.value is not None:
        photon.value = _photon_records(photon.value)
        if errors:
            photon.error = "; ".join(errors)
        return photon
    return ToolResult(
        value=None,
        source="Nominatim / Photon",
        fetched_at=datetime.now(UTC),
        error="; ".join(errors + ([photon.error] if photon.error else [])),
    )

