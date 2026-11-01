"""tests/test_a_dem_engine.py - Pure-function tests for D8 hydrology engine.

Owner: Person A.
Hand-calculated synthetic grids. No network, no dummy data.
"""
from __future__ import annotations

import numpy as np
from rasterio.transform import from_origin

from hydropinpoint.engine.dem import (
    compute_d8_flow,
    compute_flow_accumulation,
    delineate_catchments,
    fill_depressions,
)


def test_fill_depressions_synthetic():
    # 5x5 grid: rim is 10m, center is 6m (depression depth = 4m)
    dem = np.full((5, 5), 10.0, dtype=np.float32)
    dem[2, 2] = 6.0

    filled, depth = fill_depressions(dem)
    assert filled[2, 2] == 10.0
    assert depth[2, 2] == 4.0
    assert np.all(depth[0, :] == 0.0)


def test_d8_flow_direction_slope():
    # Plane tilting down from West to East (higher elevation on left, lower on right)
    dem = np.array([
        [10.0, 9.0, 8.0],
        [10.0, 9.0, 8.0],
        [10.0, 9.0, 8.0],
    ], dtype=np.float32)

    flow_dir = compute_d8_flow(dem)
    # Cells in column 0 and 1 should flow East (code 1)
    assert flow_dir[1, 0] == 1
    assert flow_dir[1, 1] == 1


def test_flow_accumulation_chain():
    # Linear slope left to right: 3 -> 2 -> 1
    dem = np.array([[3.0, 2.0, 1.0]], dtype=np.float32)
    flow_dir = compute_d8_flow(dem)
    acc = compute_flow_accumulation(dem, flow_dir)
    # Cell 0 has acc 1, cell 1 gets 1+1=2, cell 2 gets 2+1=3
    assert acc[0, 0] == 1
    assert acc[0, 1] == 2
    assert acc[0, 2] == 3


def test_delineate_catchments_basic():
    dem = np.full((7, 7), 20.0, dtype=np.float32)
    # Create sink at (3, 3) with depth 2m
    dem[3, 3] = 18.0
    # Slope surrounding cells inward
    dem[2:5, 2:5] = np.array([
        [19.0, 19.0, 19.0],
        [19.0, 18.0, 19.0],
        [19.0, 19.0, 19.0],
    ])

    filled, depth = fill_depressions(dem)
    flow_dir = compute_d8_flow(filled)
    transform = from_origin(77.6, 13.0, 0.0003, 0.0003)

    labels, sinks = delineate_catchments(
        filled, depth, flow_dir, transform, min_depth=0.5, min_area_km2=0.0
    )
    assert len(sinks) >= 1
    assert sinks[0]["depth_m"] >= 1.0
    assert labels[3, 3] > 0
