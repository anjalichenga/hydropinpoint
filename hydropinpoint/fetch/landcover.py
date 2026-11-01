"""fetch/landcover.py – ESA WorldCover 2020 windowed read over HTTP.

Owner: Person A.

Public API:
    fetch_landcover(box: BoundingBox) -> ToolResult
        value is a dict with keys:
            array    np.ndarray  (H, W) uint8, WorldCover class codes
            vintage  str  ("ESA WorldCover 2020")
        error set on failure.

Notes:
    - Built-up class code is 50 per ESA WorldCover v100 / v200 product manual.
      Confirm in the tile metadata before relying on it.
    - Tiles are available at Terrascope (free, no auth for the 10-m product).
    - Saves to .cache/landcover_{box_slug}.tif (git-ignored).
"""
from __future__ import annotations

from hydropinpoint.contracts import BoundingBox, ToolResult


def fetch_landcover(box: BoundingBox) -> ToolResult:
    """Fetch ESA WorldCover 2020 for *box*."""
    raise NotImplementedError("fetch_landcover not yet implemented – Person A")
