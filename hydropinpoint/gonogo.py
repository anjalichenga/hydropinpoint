"""Live source go/no-go matrix."""
from __future__ import annotations

import importlib.util

from hydropinpoint.config import DEFAULT_BOX
from hydropinpoint.fetch.cache import request_json
from hydropinpoint.fetch.geocode import geocode
from hydropinpoint.fetch.osm import fetch_osm
from hydropinpoint.fetch.routing import route
from hydropinpoint.fetch.wards import fetch_wards


def _status(name: str, result: object, fallback: str) -> tuple[str, str, str]:
    value = getattr(result, "value", None)
    error = getattr(result, "error", None)
    cached = getattr(result, "cached", False)
    state = "PASS" if value is not None else "FAIL"
    detail = "cached real response" if cached else (error or "live response")
    return name, state, f"{detail}; fallback: {fallback}"


def checks() -> list[tuple[str, str, str]]:
    center_lat = (DEFAULT_BOX.south + DEFAULT_BOX.north) / 2
    center_lon = (DEFAULT_BOX.west + DEFAULT_BOX.east) / 2
    open_meteo = request_json(
        url="https://api.open-meteo.com/v1/forecast",
        source="Open-Meteo forecast",
        namespace="open-meteo-gonogo",
        params={"latitude": center_lat, "longitude": center_lon, "hourly": "precipitation"},
    )
    output = [
        _status("Open-Meteo", open_meteo, "saved real response"),
        _status("Overpass", fetch_osm(DEFAULT_BOX), "alternate mirrors, then cache"),
        _status("Geocoder", geocode("Bengaluru"), "Photon, then cache"),
        _status(
            "OSRM",
            route(center_lat, center_lon, center_lat + 0.01, center_lon + 0.01),
            "route unavailable message",
        ),
        _status("DataMeet wards", fetch_wards(), "saved real response"),
    ]
    for label, module in (
        ("DEM", "hydropinpoint.fetch.dem"),
        ("WorldCover", "hydropinpoint.fetch.landcover"),
    ):
        present = importlib.util.find_spec(module) is not None
        output.append((label, "PASS" if present else "FAIL", "Person A module"))
    return output


def main() -> int:
    rows = checks()
    width = max(len(row[0]) for row in rows)
    for name, state, detail in rows:
        print(f"{name:<{width}}  {state:<4}  {detail}")
    return 0 if all(row[1] == "PASS" for row in rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())

