"""tests/test_a_rainfall_fetch.py - Unit tests for Open-Meteo rainfall helpers.

Owner: Person A.
No network. Hand-calculated coordinates and schema tests.
"""
from __future__ import annotations

from hydropinpoint.contracts import BoundingBox
from hydropinpoint.fetch.rainfall import grid_points_for_box


def test_grid_points_for_box_count():
    box = BoundingBox(west=77.60, south=12.90, east=77.70, north=13.00)
    pts = grid_points_for_box(box)
    assert len(pts) == 9


def test_grid_points_for_box_corners():
    box = BoundingBox(west=77.60, south=12.90, east=77.70, north=13.00)
    pts = grid_points_for_box(box)
    # Corners and midpoint
    assert (12.90, 77.60) in pts
    assert (13.00, 77.70) in pts
    assert (12.95, 77.65) in pts
