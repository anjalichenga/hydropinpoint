"""fetch/dem.py - Copernicus DEM GLO-30 windowed read over HTTP.

Owner: Person A.

Public API:
    fetch_dem(box: BoundingBox) -> ToolResult
        value is a dict with keys:
            array         np.ndarray  (H, W) float32, metres elevation
            transform     rasterio.Affine
            crs           str ("EPSG:4326")
            vintage       str ("Copernicus DEM GLO-30 2021" or fallback)
            resolution_m  int (30 or 90)
            fallback_used bool
        error is set and value is None on unrecoverable failure.

Notes:
    - Queries public AWS bucket for Copernicus DEM GLO-30.
    - Falls back to GLO-90 if the 30 m tile is unavailable.
    - Stitches multiple tiles if the box crosses a degree boundary (e.g. 13 N).
    - Caches fetched tiles in .cache/dem/ to avoid repeated downloads.
"""
from __future__ import annotations

import math
import os
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

from hydropinpoint.config import (
    DEM_FALLBACK_RESOLUTION_M,
    DEM_PREFERRED_RESOLUTION_M,
)
from hydropinpoint.contracts import BoundingBox, ToolResult

CACHE_DIR = Path(".cache") / "dem"


def tile_id_str(lat: int, lon: int, resolution_m: int = 30) -> str:
    """Return the Copernicus DEM tile filename base for a 1x1 degree cell.

    Examples:
        lat=12, lon=77, res=30 -> Copernicus_DSM_COG_10_N12_00_E077_00_DEM
        lat=12, lon=77, res=90 -> Copernicus_DSM_COG_30_N12_00_E077_00_DEM
    """
    res_code = "10" if resolution_m == 30 else "30"
    lat_prefix = "N" if lat >= 0 else "S"
    lon_prefix = "E" if lon >= 0 else "W"
    lat_part = f"{lat_prefix}{abs(lat):02d}_00"
    lon_part = f"{lon_prefix}{abs(lon):03d}_00"
    return f"Copernicus_DSM_COG_{res_code}_{lat_part}_{lon_part}_DEM"


def tile_url(tile_name: str, resolution_m: int = 30) -> str:
    """Return the HTTPS URL on AWS S3 for the given Copernicus DEM tile."""
    bucket = f"copernicus-dem-{resolution_m}m"
    return f"https://{bucket}.s3.amazonaws.com/{tile_name}/{tile_name}.tif"


def tiles_for_box(box: BoundingBox) -> list[tuple[int, int]]:
    """Return all integer (lat, lon) 1x1 degree cells overlapping the bounding box."""
    lat_min = math.floor(box.south)
    if box.north > lat_min and not box.north.is_integer():
        lat_max = math.floor(box.north)
    else:
        lat_max = math.floor(box.north - 1e-9)

    lon_min = math.floor(box.west)
    if box.east > lon_min and not box.east.is_integer():
        lon_max = math.floor(box.east)
    else:
        lon_max = math.floor(box.east - 1e-9)

    tiles: list[tuple[int, int]] = []
    for lat in range(lat_min, max(lat_min, lat_max) + 1):
        for lon in range(lon_min, max(lon_min, lon_max) + 1):
            tiles.append((lat, lon))
    return tiles


def _download_file(url: str, dest_path: Path, max_retries: int = 3) -> bool:
    """Download a file with exponential back-off retries."""
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


def get_tile_file(lat: int, lon: int, resolution_m: int = 30) -> tuple[Path | None, bool]:
    """Retrieve local Path for a tile, downloading if missing.

    Returns (file_path, was_cached).
    """
    tile_name = tile_id_str(lat, lon, resolution_m)
    local_path = CACHE_DIR / f"{tile_name}.tif"

    if local_path.exists() and local_path.stat().st_size > 0:
        return local_path, True

    url = tile_url(tile_name, resolution_m)
    success = _download_file(url, local_path)
    if success and local_path.exists() and local_path.stat().st_size > 0:
        return local_path, False
    return None, False


def fetch_dem(box: BoundingBox) -> ToolResult:
    """Windowed read of Copernicus DEM GLO-30 (or GLO-90 fallback) for *box*."""
    now = datetime.now(tz=timezone.utc)
    target_tiles = tiles_for_box(box)
    if not target_tiles:
        return ToolResult(
            value=None,
            source="Copernicus DEM",
            fetched_at=now,
            error=f"Invalid bounding box has no tile coverage: {box}",
        )

    # Attempt to retrieve GLO-30 tiles
    chosen_res = DEM_PREFERRED_RESOLUTION_M
    fallback_used = False
    tile_paths: list[Path] = []
    all_cached = True

    for lat, lon in target_tiles:
        tpath, was_cached = get_tile_file(lat, lon, chosen_res)
        if tpath is None:
            # Fall back to GLO-90 for all tiles
            chosen_res = DEM_FALLBACK_RESOLUTION_M
            fallback_used = True
            break
        tile_paths.append(tpath)
        if not was_cached:
            all_cached = False

    # If fallback needed, retry with GLO-90
    if fallback_used:
        tile_paths = []
        all_cached = True
        for lat, lon in target_tiles:
            tpath, was_cached = get_tile_file(lat, lon, chosen_res)
            if tpath is None:
                err_msg = (
                    f"Failed to fetch DEM tile for ({lat}, {lon}) in both 30m and 90m resolution."
                )
                return ToolResult(
                    value=None,
                    source=f"Copernicus DEM GLO-{chosen_res}",
                    fetched_at=now,
                    error=err_msg,
                )
            tile_paths.append(tpath)
            if not was_cached:
                all_cached = False

    try:
        # Read and window the DEM
        if len(tile_paths) == 1:
            with rasterio.open(tile_paths[0]) as src:
                window = from_bounds(box.west, box.south, box.east, box.north, src.transform)
                arr = src.read(1, window=window).astype(np.float32)
                win_transform = src.window_transform(window)
                crs_str = src.crs.to_string() if src.crs else "EPSG:4326"
        else:
            # Multiple tiles: merge then crop
            opened_sources = [rasterio.open(p) for p in tile_paths]
            try:
                bounds_tuple = (box.west, box.south, box.east, box.north)
                mosaic_arr, mosaic_transform = merge(opened_sources, bounds=bounds_tuple)
                arr = mosaic_arr[0].astype(np.float32)
                win_transform = mosaic_transform
                crs_val = opened_sources[0].crs
                crs_str = crs_val.to_string() if crs_val else "EPSG:4326"
            finally:
                for s in opened_sources:
                    s.close()

        vintage_label = (
            f"Copernicus DEM GLO-{chosen_res} 2021"
            if not fallback_used
            else f"Copernicus DEM GLO-{chosen_res} (fallback) 2021"
        )
        source_name = f"Copernicus DEM GLO-{chosen_res} (AWS)"

        result_val: dict[str, Any] = {
            "array": arr,
            "transform": win_transform,
            "crs": crs_str,
            "vintage": vintage_label,
            "resolution_m": chosen_res,
            "fallback_used": fallback_used,
        }

        return ToolResult(
            value=result_val,
            source=source_name,
            fetched_at=now,
            cached=all_cached,
            error=None,
        )

    except Exception as exc:
        return ToolResult(
            value=None,
            source=f"Copernicus DEM GLO-{chosen_res}",
            fetched_at=now,
            error=f"Error reading DEM raster window: {exc}",
        )
