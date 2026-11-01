"""engine/scoring.py – susceptibility index for hotspots.

Owner: Person A.

Public API:
    score_hotspots(hotspots: list[Hotspot]) -> list[Hotspot]
        Computes susceptibility_score (0..1) and susceptibility_rank (1 = worst)
        from the ranks of depression_depth_m, catchment_area_km2, and imperviousness.
        Returns hotspots sorted by rank ascending (rank 1 first).

Notes:
    - Scoring is static (independent of rainfall). It reflects terrain and land cover.
    - Rank-based composite avoids unit-mixing: each of the three factors is ranked
      1..N (1 = highest value), then summed and normalised.
    - Severity (absolute Q) is computed separately in compute_runoff; it is not
      part of the susceptibility score.
    - Validated against intuition: built-up areas with deep depressions and large
      catchments should rank highest.
"""
from __future__ import annotations

from hydropinpoint.contracts import Hotspot


def score_hotspots(hotspots: list[Hotspot]) -> list[Hotspot]:
    """Compute susceptibility score and rank; return hotspots sorted by rank."""
    raise NotImplementedError("score_hotspots not yet implemented – Person A")
