"""engine/hydrology.py - Rational Method runoff and flow-path slope.

Owner: Person A.

Public interface (as agreed in contracts.py):
    compute_terrain(box: BoundingBox) -> list[Hotspot]
        Static terrain & landcover computation: extracts sinks, delineates catchments,
        computes slope S, imperviousness, C, susceptibility score and rank.

    compute_runoff(hotspots: list[Hotspot], rain: RainfallSeries) -> list[Hotspot]
        Applies Rational Method: Q = 0.278 * C * I * A (I mm/h, A km2, Q m3/s).
        Fills hourly_Q_m3s aligned with rain.times.
"""
from __future__ import annotations

import math

import numpy as np

from hydropinpoint.config import (
    MAX_HOTSPOTS,
    MAX_RATIONAL_AREA_KM2,
    RUNOFF_COEFF_DEFAULT,
)
from hydropinpoint.contracts import BoundingBox, Hotspot, RainfallSeries
from hydropinpoint.engine.dem import process_dem
from hydropinpoint.engine.landcover import compute_landcover_stats
from hydropinpoint.engine.rainfall import assign_rain_cells
from hydropinpoint.engine.scoring import score_hotspots
from hydropinpoint.fetch.dem import fetch_dem
from hydropinpoint.fetch.landcover import fetch_landcover


def compute_terrain(box: BoundingBox) -> list[Hotspot]:
    """Fetch DEM and landcover, process terrain, and return static Hotspot models."""
    dem_res = fetch_dem(box)
    if dem_res.error or dem_res.value is None:
        raise RuntimeError(f"DEM fetch failed for terrain analysis: {dem_res.error}")

    dem_data = dem_res.value
    dem_arr = dem_data["array"]
    transform = dem_data["transform"]
    crs = dem_data["crs"]

    # Process DEM: fill sinks, extract flow direction and catchments
    dem_out = process_dem(dem_arr, transform, crs)
    catchment_labels = dem_out["catchment_labels"]
    sinks = dem_out["sinks"]
    filled_arr = dem_out["filled_array"]

    if not sinks:
        return []

    # Fetch landcover for the box
    lc_res = fetch_landcover(box)
    if lc_res.value is not None:
        lc_arr = lc_res.value["array"]
        lc_stats = compute_landcover_stats(catchment_labels, lc_arr, transform)
    else:
        # Fallback to default values if landcover fetch fails
        lc_stats = {}

    # Cell physical spacing in metres
    dx_m = abs(transform[0]) * 111000.0 * math.cos(math.radians(box.south))
    dy_m = abs(transform[4]) * 111000.0

    hotspots: list[Hotspot] = []
    for s in sinks:
        s_id = s["id"]
        default_lc = {"imperviousness": 0.5, "runoff_coeff_C": RUNOFF_COEFF_DEFAULT}
        c_stats = lc_stats.get(s_id, default_lc)

        # Flow-path slope S: difference between max catchment elevation and sink elevation,
        # divided by estimated flow distance (m/m)
        c_mask = (catchment_labels == s_id)
        if np.any(c_mask):
            c_elevs = filled_arr[c_mask]
            elev_max = float(np.max(c_elevs))
            elev_min = float(s["depth_m"]) + float(np.min(c_elevs))
            elev_drop = max(0.1, elev_max - elev_min)
            # Flow distance approximated from catchment cell count radius
            n_cells = float(np.sum(c_mask))
            flow_len_m = max(30.0, math.sqrt(n_cells) * math.sqrt(dx_m * dy_m))
            raw_slope_S = round(elev_drop / flow_len_m, 5)
        else:
            raw_slope_S = 0.005

        area_km2 = s["area_km2"]
        outside_validity = bool(area_km2 > MAX_RATIONAL_AREA_KM2)

        h = Hotspot(
            id=s_id,
            lat=s["centroid_lat"],
            lon=s["centroid_lon"],
            catchment_area_km2=area_km2,
            depression_depth_m=s["depth_m"],
            imperviousness=c_stats["imperviousness"],
            runoff_coeff_C=c_stats["runoff_coeff_C"],
            flow_path_slope_S=raw_slope_S,
            susceptibility_score=0.0,
            susceptibility_rank=s_id,
            outside_rational_validity=outside_validity,
            hourly_Q_m3s=[],
        )
        hotspots.append(h)

    # Score and rank hotspots
    scored = score_hotspots(hotspots)
    return scored[:MAX_HOTSPOTS]


def compute_runoff(hotspots: list[Hotspot], rain: RainfallSeries) -> list[Hotspot]:
    """Calculate hourly runoff discharge Q using the Rational Method.

    Formula: Q = 0.278 * C * I * A
    Units:
        C : dimensionless runoff coefficient (0..1)
        I : rainfall intensity (mm/h)
        A : catchment area (km²)
        Q : runoff discharge (m³/s)
    """
    if not hotspots or not rain.times:
        return hotspots

    # Ensure hotspots are mapped to appropriate rainfall cells
    assigned_hotspots = assign_rain_cells(hotspots, rain)

    for h in assigned_hotspots:
        cell_idx = min(h.rain_cell_index, len(rain.cells) - 1)
        rain_cell = rain.cells[cell_idx]
        hourly_intensities = rain_cell.mm_per_h

        q_series: list[float] = []
        for i_mm_per_h in hourly_intensities:
            # Q = 0.278 * C * I * A
            # (Note: Q is computed even if outside_rational_validity is flagged,
            # as required by the specification so hydraulic sizing can still operate)
            q = 0.278 * h.runoff_coeff_C * i_mm_per_h * h.catchment_area_km2
            q_series.append(round(max(0.0, float(q)), 4))

        h.hourly_Q_m3s = q_series

    return assigned_hotspots
