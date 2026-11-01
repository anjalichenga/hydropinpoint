"""fetch/rainfall.py - Open-Meteo forecast and archive rainfall fetcher.

Owner: Person A.

Public API:
    fetch_forecast(box: BoundingBox) -> RainfallSeries
        Hourly 72-h forecast for nine grid points around the box.
        Prints the nine values first. If identical, collapses to one RainCell
        and sets grid_values_identical=True. Label: "LIVE".

    fetch_archive(box: BoundingBox, date: str) -> RainfallSeries
        Open-Meteo ERA5 archive for *date* (YYYY-MM-DD).
        Label: "HISTORICAL REPLAY".
        Records the model name ("ERA5 (~25 km resolution)") in source.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from hydropinpoint.contracts import BoundingBox, RainCell, RainfallSeries

CACHE_DIR = Path(".cache") / "rainfall"


def grid_points_for_box(box: BoundingBox) -> list[tuple[float, float]]:
    """Generate 9 grid coordinates (3x3) covering the bounding box."""
    lat_mid = (box.south + box.north) / 2.0
    lon_mid = (box.west + box.east) / 2.0
    lats = [round(box.south, 4), round(lat_mid, 4), round(box.north, 4)]
    lons = [round(box.west, 4), round(lon_mid, 4), round(box.east, 4)]

    points: list[tuple[float, float]] = []
    for lat in lats:
        for lon in lons:
            points.append((lat, lon))
    return points


def _fetch_json(url: str, cache_file: Path | None = None) -> dict | list | None:
    """Fetch JSON from URL with local caching and retries."""
    if cache_file and cache_file.exists():
        try:
            with open(cache_file, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass

    headers = {"User-Agent": "HydroPinpoint/1.0 (water-hotspot-screener)"}
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if cache_file:
                cache_file.parent.mkdir(parents=True, exist_ok=True)
                with open(cache_file, "w", encoding="utf-8") as f:
                    json.dump(data, f)
            return data
    except Exception:
        return None


def fetch_forecast(box: BoundingBox) -> RainfallSeries:
    """Fetch 72-h hourly forecast for the 9 points around *box*."""
    now = datetime.now(tz=timezone.utc)
    points = grid_points_for_box(box)
    lats_str = ",".join(str(p[0]) for p in points)
    lons_str = ",".join(str(p[1]) for p in points)

    params = {
        "latitude": lats_str,
        "longitude": lons_str,
        "hourly": "precipitation",
        "forecast_days": "3",
        "timezone": "UTC",
    }
    url = f"https://api.open-meteo.com/v1/forecast?{urllib.parse.urlencode(params)}"
    cache_slug = f"forecast_{box.west:.2f}_{box.south:.2f}_{box.east:.2f}_{box.north:.2f}.json"
    cache_path = CACHE_DIR / cache_slug

    raw = _fetch_json(url, cache_path)

    # Fallback / dry stub if network is completely unreachable
    if not raw:
        times = [now]
        lat_c = (box.south + box.north) / 2.0
        lon_c = (box.west + box.east) / 2.0
        cell = RainCell(lat=lat_c, lon=lon_c, mm_per_h=[0.0])
        return RainfallSeries(
            times=times,
            cells=[cell],
            source="Open-Meteo forecast (offline/unreachable)",
            fetched_at=now,
            grid_values_identical=True,
            label="LIVE",
        )

    # Normalize response to list of location dicts
    responses: list[dict] = raw if isinstance(raw, list) else [raw]

    # Extract times from first location
    time_strs = responses[0].get("hourly", {}).get("time", [])
    times = [datetime.fromisoformat(ts).replace(tzinfo=timezone.utc) for ts in time_strs]

    # Print the nine values first as mandated by Person A prompt
    print("[Rainfall Forecast] 9-point grid inspection:")
    precip_series_list: list[list[float]] = []
    for idx, (resp, pt) in enumerate(zip(responses, points, strict=False)):
        series = resp.get("hourly", {}).get("precipitation", [])
        float_series = [float(v) for v in series]
        precip_series_list.append(float_series)
        peak_mm = max(float_series, default=0.0)
        total_mm = sum(float_series)
        print(f"  pt {idx+1} ({pt[0]}, {pt[1]}): total={total_mm:.1f} mm, peak={peak_mm:.1f} mm/h")

    # Check if all 9 series are identical
    identical = True
    first_series = precip_series_list[0]
    for other in precip_series_list[1:]:
        if other != first_series:
            identical = False
            break

    if identical:
        mid_lat = (box.south + box.north) / 2.0
        mid_lon = (box.west + box.east) / 2.0
        cells = [RainCell(lat=mid_lat, lon=mid_lon, mm_per_h=first_series)]
    else:
        cells = [
            RainCell(lat=pt[0], lon=pt[1], mm_per_h=series)
            for pt, series in zip(points, precip_series_list, strict=False)
        ]

    return RainfallSeries(
        times=times,
        cells=cells,
        source="Open-Meteo forecast (72h)",
        fetched_at=now,
        grid_values_identical=identical,
        label="LIVE",
    )


def fetch_archive(box: BoundingBox, date: str = "2022-09-05") -> RainfallSeries:
    """Fetch Open-Meteo historical archive for *box* on *date* (YYYY-MM-DD)."""
    now = datetime.now(tz=timezone.utc)
    lat_mid = round((box.south + box.north) / 2.0, 4)
    lon_mid = round((box.west + box.east) / 2.0, 4)

    params = {
        "latitude": str(lat_mid),
        "longitude": str(lon_mid),
        "start_date": date,
        "end_date": date,
        "hourly": "precipitation",
        "models": "era5",
        "timezone": "UTC",
    }
    url = f"https://archive-api.open-meteo.com/v1/archive?{urllib.parse.urlencode(params)}"
    cache_path = CACHE_DIR / f"archive_{date}_{lat_mid}_{lon_mid}.json"

    raw = _fetch_json(url, cache_path)

    if not raw or not isinstance(raw, dict):
        times = [now]
        cell = RainCell(lat=lat_mid, lon=lon_mid, mm_per_h=[0.0])
        return RainfallSeries(
            times=times,
            cells=[cell],
            source="Open-Meteo ERA5 archive (~25km resolution, offline fallback)",
            fetched_at=now,
            grid_values_identical=True,
            label="HISTORICAL REPLAY",
        )

    hourly = raw.get("hourly", {})
    time_strs = hourly.get("time", [])
    times = [datetime.fromisoformat(ts).replace(tzinfo=timezone.utc) for ts in time_strs]
    precip = [float(v) for v in hourly.get("precipitation", [])]

    cells = [RainCell(lat=lat_mid, lon=lon_mid, mm_per_h=precip)]

    return RainfallSeries(
        times=times,
        cells=cells,
        source="Open-Meteo ERA5 archive (~25 km resolution)",
        fetched_at=now,
        grid_values_identical=True,
        label="HISTORICAL REPLAY",
    )
