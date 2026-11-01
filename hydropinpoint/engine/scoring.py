"""engine/scoring.py - Susceptibility index and ranking for hotspots.

Owner: Person A.

Public API:
    score_hotspots(hotspots: list[Hotspot]) -> list[Hotspot]
        Computes static susceptibility_score (0..1) and susceptibility_rank (1 = highest)
        from the ranks of depression depth, catchment area, and imperviousness.
        Returns hotspots sorted with rank 1 first.
"""
from __future__ import annotations

import numpy as np

from hydropinpoint.contracts import Hotspot


def score_hotspots(hotspots: list[Hotspot]) -> list[Hotspot]:
    """Score and rank hotspots based on static terrain and landcover properties."""
    if not hotspots:
        return []

    n = len(hotspots)
    if n == 1:
        hotspots[0].susceptibility_score = 1.0
        hotspots[0].susceptibility_rank = 1
        return hotspots

    depths = np.array([h.depression_depth_m for h in hotspots], dtype=float)
    areas = np.array([h.catchment_area_km2 for h in hotspots], dtype=float)
    imperv = np.array([h.imperviousness for h in hotspots], dtype=float)

    # Rank each feature: highest value gets rank 1, lowest gets rank N
    def get_ranks_descending(arr: np.ndarray) -> np.ndarray:
        order = np.argsort(-arr)
        ranks = np.empty_like(order, dtype=float)
        ranks[order] = np.arange(1, n + 1)
        return ranks

    r_depth = get_ranks_descending(depths)
    r_area = get_ranks_descending(areas)
    r_imperv = get_ranks_descending(imperv)

    # Composite rank sum: lower rank sum = more susceptible (rank 1 is highest)
    composite_rank_sum = (r_depth + r_area + r_imperv) / 3.0

    # Normalise score to 0..1 where 1.0 is most susceptible and 0.0 is least
    min_sum = 1.0
    max_sum = float(n)
    if max_sum > min_sum:
        scores = 1.0 - ((composite_rank_sum - min_sum) / (max_sum - min_sum))
    else:
        scores = np.ones(n, dtype=float)

    for h, score in zip(hotspots, scores, strict=False):
        h.susceptibility_score = round(float(np.clip(score, 0.0, 1.0)), 3)

    # Sort hotspots descending by susceptibility_score (rank 1 first)
    sorted_hotspots = sorted(
        hotspots,
        key=lambda h: (h.susceptibility_score, h.depression_depth_m, h.catchment_area_km2),
        reverse=True,
    )

    for rank, h in enumerate(sorted_hotspots, start=1):
        h.susceptibility_rank = rank

    return sorted_hotspots
