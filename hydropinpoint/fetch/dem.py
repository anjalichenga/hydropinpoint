"""fetch/dem.py – Copernicus DEM GLO-30 windowed read over HTTP.

Owner: Person A.

Public API:
    fetch_dem(box: BoundingBox) -> ToolResult
        value is a dict with keys:
            array      np.ndarray  (H, W) float32, metres
            transform  rasterio.Affine
            crs        str ("EPSG:4326")
            vintage    str
            resolution_m int (30 or 90 if fallback used)
        error is set and value is None on unrecoverable failure.

Notes:
    - Tries GLO-30 first (s3://copernicus-dem-30m over HTTPS; public, no auth).
    - Falls back to GLO-90 (s3://copernicus-dem-90m) if any GLO-30 tile fails.
    - Handles the case where the bounding box crosses a tile boundary (e.g. N12/N13).
    - Retries up to 3 times with exponential back-off before declaring failure.
    - Saves the merged array to .cache/dem_{box_slug}.tif (git-ignored).
"""
from __future__ import annotations

# Implementation will be added by Person A.
# Stub so the package imports cleanly at scaffold time.
from hydropinpoint.contracts import BoundingBox, ToolResult


def fetch_dem(box: BoundingBox) -> ToolResult:
    """Fetch Copernicus DEM GLO-30 (or GLO-90 fallback) for *box*."""
    raise NotImplementedError("fetch_dem not yet implemented – Person A")
