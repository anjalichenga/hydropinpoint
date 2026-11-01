"""engine/rainfall.py – map each hotspot to its Open-Meteo grid cell.

Owner: Person A.

Public API:
    assign_rain_cells(hotspots: list[Hotspot], rain: RainfallSeries) -> list[Hotspot]
        For each hotspot, finds the nearest RainCell (by centroid distance) and
        sets hotspot.rain_cell_index. Returns hotspots with the field filled.

Notes:
    - Open-Meteo grid spacing is approximately 9–25 km depending on the model;
      for a 10 × 10 km box this often means a single cell.
    - If grid_values_identical is True, all hotspots get rain_cell_index = 0.
"""
from __future__ import annotations

from hydropinpoint.contracts import Hotspot, RainfallSeries


def assign_rain_cells(hotspots: list[Hotspot], rain: RainfallSeries) -> list[Hotspot]:
    """Assign each hotspot to its nearest rainfall grid cell."""
    raise NotImplementedError("assign_rain_cells not yet implemented – Person A")
