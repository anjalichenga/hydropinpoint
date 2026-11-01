"""fetch/landcover.py - ESA WorldCover 2020 windowed read over HTTP.

Owner: Person A.

Public API:
    fetch_landcover(box: BoundingBox) -> ToolResult
        value is a dict with keys:
            array      np.ndarray  (H, W) uint8, WorldCover class codes
            transform  rasterio.Affine
            crs        str ("EPSG:4326")
            vintage    str ("ESA WorldCover 2020 v100")
        error set on failure and value is None.

Notes:
    - Built-up class code is 50 per ESA WorldCover v100 product manual.
    - WorldCover tiles are 3x3 degree blocks on AWS (bucket esa-worldcover).
    - Caches fetched tiles to .cache/landcover/.
"""
from __future__ import annotations

import math
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import rasterio
from rasterio.merge import merge
from rasterio.windows import from_bounds

from hydropinpoint.contracts import BoundingBox, ToolResult

CACHE_DIR = Path(".cache") / "landcover"
WORLDCOVER_VINTAGE = "ESA WorldCover 2020 v100"
BUILT_UP_CLASS_CODE = 50


def worldcover_tile_id(lat: float, lon: float) -> str:
    """Return the ESA WorldCover 3x3 degree tile identifier.

    The grid aligns to 3-degree steps (e.g. N12E075 for lat 12..15, lon 75..78).
    """
    tile_lat = int(math.floor(lat / 3.0) * 3)
    tile_lon = int(math.floor(lon / 3.0) * 3)

    lat_prefix = "N" if tile_lat >= 0 else "S"
    lon_prefix = "E" if tile_lon >= 0 else "W"
    return f"{lat_prefix}{abs(tile_lat):02d}{lon_prefix}{abs(tile_lon):03d}"


def worldcover_tile_url(tile_id: str) -> str:
    """Return the HTTPS URL on AWS S3 for the given ESA WorldCover 2020 tile."""
    filename = f"ESA_WorldCover_10m_2020_v100_{tile_id}_Map.tif"
    return f"https://esa-worldcover.s3.eu-central-1.amazonaws.com/v100/2020/map/{filename}"


def worldcover_tiles_for_box(box: BoundingBox) -> list[str]:
    """Return all unique 3x3 degree tile IDs covering the bounding box."""
    lat_min = int(math.floor(box.south / 3.0) * 3)
    if box.north % 3 != 0:
        lat_max = int(math.floor(box.north / 3.0) * 3)
    else:
        lat_max = int(math.floor((box.north - 1e-9) / 3.0) * 3)

    lon_min = int(math.floor(box.west / 3.0) * 3)
    if box.east % 3 != 0:
        lon_max = int(math.floor(box.east / 3.0) * 3)
    else:
        lon_max = int(math.floor((box.east - 1e-9) / 3.0) * 3)

    tile_ids: list[str] = []
    for lat in range(lat_min, max(lat_min, lat_max) + 1, 3):
        for lon in range(lon_min, max(lon_min, lon_max) + 1, 3):
            t_id = worldcover_tile_id(float(lat), float(lon))
            if t_id not in tile_ids:
                tile_ids.append(t_id)
    return tile_ids


def _download_tile(url: str, dest_path: Path, max_retries: int = 3) -> bool:
    """Download tile with retries."""
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = dest_path.with_suffix(".tmp")
    headers = {"User-Agent": "HydroPinpoint/1.0 (water-hotspot-screener)"}
    req = urllib.request.Request(url, headers=headers)

    delay = 1.0
    for attempt in range(1, max_retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp, open(temp_path, "wb") as f:
                while chunk := resp.read(65536):
                    f.write(chunk)
            temp_path.replace(dest_path)
            return True
        except (urllib.error.URLError, TimeoutError, OSError):
            if temp_path.exists():
                temp_path.unlink(missing_ok=True)
            if attempt == max_retries:
                return False
            time.sleep(delay)
            delay *= 2.0
    return False


def get_worldcover_file(tile_id: str) -> tuple[Path | None, bool]:
    """Retrieve local Path for tile, downloading if missing."""
    filename = f"ESA_WorldCover_10m_2020_v100_{tile_id}_Map.tif"
    local_path = CACHE_DIR / filename
    if local_path.exists() and local_path.stat().st_size > 0:
        return local_path, True

    url = worldcover_tile_url(tile_id)
    success = _download_tile(url, local_path)
    if success and local_path.exists() and local_path.stat().st_size > 0:
        return local_path, False
    return None, False


def fetch_landcover(box: BoundingBox) -> ToolResult:
    """Fetch ESA WorldCover 2020 window for *box*."""
    now = datetime.now(tz=timezone.utc)
    target_tiles = worldcover_tiles_for_box(box)
    if not target_tiles:
        return ToolResult(
            value=None,
            source="ESA WorldCover 2020",
            fetched_at=now,
            error=f"No WorldCover tiles found for box: {box}",
        )

    tile_paths: list[Path] = []
    all_cached = True
    for t_id in target_tiles:
        path, was_cached = get_worldcover_file(t_id)
        if path is None:
            return ToolResult(
                value=None,
                source="ESA WorldCover 2020 (AWS)",
                fetched_at=now,
                error=f"Failed to download ESA WorldCover tile: {t_id}",
            )
        tile_paths.append(path)
        if not was_cached:
            all_cached = False

    try:
        if len(tile_paths) == 1:
            with rasterio.open(tile_paths[0]) as src:
                window = from_bounds(box.west, box.south, box.east, box.north, src.transform)
                arr = src.read(1, window=window).astype(np.uint8)
                win_transform = src.window_transform(window)
                crs_str = src.crs.to_string() if src.crs else "EPSG:4326"
        else:
            opened_sources = [rasterio.open(p) for p in tile_paths]
            try:
                bounds_tuple = (box.west, box.south, box.east, box.north)
                mosaic_arr, mosaic_transform = merge(opened_sources, bounds=bounds_tuple)
                arr = mosaic_arr[0].astype(np.uint8)
                win_transform = mosaic_transform
                crs_val = opened_sources[0].crs
                crs_str = crs_val.to_string() if crs_val else "EPSG:4326"
            finally:
                for s in opened_sources:
                    s.close()

        result_val: dict[str, Any] = {
            "array": arr,
            "transform": win_transform,
            "crs": crs_str,
            "vintage": WORLDCOVER_VINTAGE,
        }

        return ToolResult(
            value=result_val,
            source="ESA WorldCover 2020 (AWS)",
            fetched_at=now,
            cached=all_cached,
            error=None,
        )

    except Exception as exc:
        return ToolResult(
            value=None,
            source="ESA WorldCover 2020 (AWS)",
            fetched_at=now,
            error=f"Error reading landcover window: {exc}",
        )
