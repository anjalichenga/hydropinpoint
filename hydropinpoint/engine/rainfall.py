"""engine/rainfall.py - Map each hotspot to its nearest Open-Meteo rainfall cell.

Owner: Person A.

Public API:
    assign_rain_cells(hotspots: list[Hotspot], rain: RainfallSeries) -> list[Hotspot]
        For each hotspot, finds the nearest RainCell by geographic distance and
        sets hotspot.rain_cell_index.
"""
from __future__ import annotations

import math

from hydropinpoint.contracts import Hotspot, RainfallSeries


def assign_rain_cells(hotspots: list[Hotspot], rain: RainfallSeries) -> list[Hotspot]:
    """Assign each hotspot to its nearest rainfall grid cell."""
    if not hotspots or not rain.cells:
        return hotspots

    # If all grid values are identical, all hotspots map to cell 0
    if rain.grid_values_identical or len(rain.cells) == 1:
        for h in hotspots:
            h.rain_cell_index = 0
        return hotspots

    # Otherwise assign each hotspot to the geographically closest cell
    for h in hotspots:
        best_idx = 0
        min_dist_sq = float("inf")
        for idx, cell in enumerate(rain.cells):
            dlat = h.lat - cell.lat
            dlon = (h.lon - cell.lon) * math.cos(math.radians(h.lat))
            dist_sq = dlat * dlat + dlon * dlon
            if dist_sq < min_dist_sq:
                min_dist_sq = dist_sq
                best_idx = idx
        h.rain_cell_index = best_idx

    return hotspots
