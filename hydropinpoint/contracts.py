"""Shared contract between Person A (terrain/hydrology) and Person B (hydraulics/tools/agent/app).

Units are stated in every field name or comment. Change this file only through a
`shared:` pull request approved by both people.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

RainLabel = Literal["LIVE", "SCENARIO", "HISTORICAL REPLAY"]


class BoundingBox(BaseModel):
    """WGS84 degrees."""
    west: float
    south: float
    east: float
    north: float


class ToolResult(BaseModel):
    """Uniform wrapper returned by every fetcher and tool, so the validator and the
    citation checker can work on all of them."""
    value: Any
    source: str                      # human-readable source name
    fetched_at: datetime             # UTC timestamp of the real fetch (or of the cached fetch)
    cached: bool = False             # True when served from a saved real response
    error: str | None = None      # set when the call failed; value is then None


class RainCell(BaseModel):
    lat: float
    lon: float
    mm_per_h: list[float]            # hourly intensity, aligned with RainfallSeries.times


class RainfallSeries(BaseModel):
    times: list[datetime]            # UTC hourly timestamps
    cells: list[RainCell]            # unique forecast cells (1 if all nine grid values identical)
    source: str                      # e.g. "Open-Meteo forecast" or "Open-Meteo archive (<model>)"
    fetched_at: datetime
    grid_values_identical: bool      # True when the nine grid points returned identical values
    label: RainLabel = "LIVE"        # never mix labels in one series


class Hotspot(BaseModel):
    id: int
    lat: float                       # centroid, degrees
    lon: float
    catchment_area_km2: float
    depression_depth_m: float        # filled minus original elevation
    imperviousness: float            # 0..1
    runoff_coeff_C: float            # 0..1 (ASSUMPTION, see config.py)
    flow_path_slope_S: float         # m/m, raw slope along the flow path; the floor is applied by B
    susceptibility_score: float      # 0..1, static
    susceptibility_rank: int         # 1 = most susceptible
    rain_cell_index: int = 0         # index into RainfallSeries.cells
    outside_rational_validity: bool = False   # catchment above the configured maximum area
    hourly_Q_m3s: list[float] = Field(default_factory=list)  # aligned with RainfallSeries.times


class DrainSizing(BaseModel):
    hotspot_id: int
    hourly_required_D_m: list[float]          # required full-flow circular pipe diameter, metres
    slope_floor_applied: bool                 # True when the minimum-slope floor set the size
    mapped_drain_size_m: float | None = None   # from OSM width or diameter, if mapped
    mapped_narrower_than_required: bool | None = None
    capacity_note: str = "existing capacity unknown"


class EngineResult(BaseModel):
    box: BoundingBox
    hotspots: list[Hotspot]
    sizings: list[DrainSizing]
    rainfall: RainfallSeries
    dem_vintage: str
    landcover_vintage: str
    notes: list[str] = Field(default_factory=list)   # fallbacks used, degraded sources
    generated_at: datetime


# ---- Interfaces (signatures only; implementations live in each owner's modules) ----
# A: hydropinpoint.engine.hydrology / dem / scoring
#   compute_terrain(box: BoundingBox) -> list[Hotspot]
#   compute_runoff(hotspots: list[Hotspot], rain: RainfallSeries) -> list[Hotspot]
# B: hydropinpoint.engine.hydraulics, hydropinpoint.pipeline
#   size_drains(hotspots: list[Hotspot]) -> list[DrainSizing]
#   run(box: BoundingBox) -> EngineResult
