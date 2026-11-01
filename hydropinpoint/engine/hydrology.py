"""engine/hydrology.py – Rational Method runoff and flow-path slope.

Owner: Person A.

Public interface (as agreed in contracts.py):

    compute_terrain(box: BoundingBox) -> list[Hotspot]
        Calls fetch_dem, fetch_landcover, process_dem, compute_landcover_stats.
        Fills static Hotspot fields (centroid, catchment_area_km2, depression_depth_m,
        imperviousness, runoff_coeff_C, flow_path_slope_S, susceptibility_score,
        susceptibility_rank). Does NOT fill hourly_Q_m3s.

    compute_runoff(hotspots: list[Hotspot], rain: RainfallSeries) -> list[Hotspot]
        Fills hourly_Q_m3s using the Rational Method:
            Q = 0.278 * C * I * A   (I in mm/h, A in km², Q in m³/s)
        Sets outside_rational_validity=True for catchments > MAX_RATIONAL_AREA_KM2.
        Does NOT apply the slope floor (that is B's job in hydraulics.py).

Notes:
    - Formula source: IS 1893:2016 / Chow, Maidment & Mays "Applied Hydrology".
      The 0.278 factor converts units: Q[m³/s] = C * I[mm/h] * A[km²] / 3.6
      (same as 0.278 * C * I * A).
    - Flow-path slope S is the elevation difference along the D8 flow path from
      the catchment outlet to the most distant upstream cell, divided by that
      path length in metres. Raw value; B applies the floor.
    - A dry-day forecast (all I = 0) returns all Q = 0 without error.
"""
from __future__ import annotations

from hydropinpoint.contracts import BoundingBox, Hotspot, RainfallSeries


def compute_terrain(box: BoundingBox) -> list[Hotspot]:
    """Fetch DEM + landcover, delineate catchments, return static Hotspot list."""
    raise NotImplementedError("compute_terrain not yet implemented – Person A")


def compute_runoff(hotspots: list[Hotspot], rain: RainfallSeries) -> list[Hotspot]:
    """Apply Rational Method to fill hourly_Q_m3s for each hotspot."""
    raise NotImplementedError("compute_runoff not yet implemented – Person A")
