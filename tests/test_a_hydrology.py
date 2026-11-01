"""tests/test_a_hydrology.py - Hand-calculated tests for Person A hydrology engine.

Owner: Person A.
Formula: Q = 0.278 * C * I * A. No network, pure functions only.
"""
from __future__ import annotations

from datetime import datetime, timezone

import numpy as np

from hydropinpoint.contracts import Hotspot, RainCell, RainfallSeries
from hydropinpoint.engine.hydrology import compute_runoff
from hydropinpoint.engine.landcover import compute_landcover_stats
from hydropinpoint.engine.rainfall import assign_rain_cells
from hydropinpoint.engine.scoring import score_hotspots

NOW = datetime.now(tz=timezone.utc)


def test_rational_method_hand_calculated():
    # C = 0.80, I = 50 mm/h, A = 0.10 km2 -> Q = 0.278 * 0.8 * 50 * 0.1 = 1.112 m3/s
    h = Hotspot(
        id=1,
        lat=12.95,
        lon=77.65,
        catchment_area_km2=0.10,
        depression_depth_m=0.5,
        imperviousness=0.8,
        runoff_coeff_C=0.80,
        flow_path_slope_S=0.005,
        susceptibility_score=0.9,
        susceptibility_rank=1,
    )
    cell = RainCell(lat=12.95, lon=77.65, mm_per_h=[50.0])
    rain = RainfallSeries(
        times=[NOW],
        cells=[cell],
        source="unit-test",
        fetched_at=NOW,
        grid_values_identical=True,
    )

    result = compute_runoff([h], rain)
    assert len(result[0].hourly_Q_m3s) == 1
    assert abs(result[0].hourly_Q_m3s[0] - 1.112) < 0.001


def test_rational_method_dry_day():
    # Dry day: I = 0 mm/h -> Q = 0.0 m3/s without errors
    h = Hotspot(
        id=1,
        lat=12.95,
        lon=77.65,
        catchment_area_km2=0.10,
        depression_depth_m=0.5,
        imperviousness=0.8,
        runoff_coeff_C=0.80,
        flow_path_slope_S=0.005,
        susceptibility_score=0.9,
        susceptibility_rank=1,
    )
    cell = RainCell(lat=12.95, lon=77.65, mm_per_h=[0.0, 0.0])
    rain = RainfallSeries(
        times=[NOW, NOW],
        cells=[cell],
        source="unit-test",
        fetched_at=NOW,
        grid_values_identical=True,
    )

    result = compute_runoff([h], rain)
    assert result[0].hourly_Q_m3s == [0.0, 0.0]


def test_score_hotspots_ranking():
    # 2 hotspots: h1 has deeper sink, larger area, higher imperviousness
    h1 = Hotspot(
        id=1,
        lat=12.95,
        lon=77.65,
        catchment_area_km2=0.50,
        depression_depth_m=2.0,
        imperviousness=0.9,
        runoff_coeff_C=0.85,
        flow_path_slope_S=0.01,
        susceptibility_score=0.0,
        susceptibility_rank=0,
    )
    h2 = Hotspot(
        id=2,
        lat=12.96,
        lon=77.66,
        catchment_area_km2=0.05,
        depression_depth_m=0.4,
        imperviousness=0.2,
        runoff_coeff_C=0.40,
        flow_path_slope_S=0.005,
        susceptibility_score=0.0,
        susceptibility_rank=0,
    )

    scored = score_hotspots([h2, h1])
    assert scored[0].id == 1
    assert scored[0].susceptibility_rank == 1
    assert scored[1].id == 2
    assert scored[1].susceptibility_rank == 2
    assert scored[0].susceptibility_score > scored[1].susceptibility_score


def test_compute_landcover_stats():
    # Catchment 1 has 4 cells: three built-up (50), one tree cover (10)
    # Tree cover C = 0.35, Built-up C = 0.80
    # Expected imperviousness = 3/4 = 0.75
    # Expected C = (0.80 * 3 + 0.35 * 1) / 4 = 2.75 / 4 = 0.6875 -> ~0.688
    labels = np.array([[1, 1], [1, 1]], dtype=np.int32)
    lc = np.array([[50, 50], [50, 10]], dtype=np.uint8)

    stats = compute_landcover_stats(labels, lc)
    assert 1 in stats
    assert stats[1]["imperviousness"] == 0.75
    assert abs(stats[1]["runoff_coeff_C"] - 0.688) < 0.002


def test_assign_rain_cells_nearest():
    h = Hotspot(
        id=1,
        lat=12.91,
        lon=77.61,
        catchment_area_km2=0.1,
        depression_depth_m=0.5,
        imperviousness=0.5,
        runoff_coeff_C=0.5,
        flow_path_slope_S=0.005,
        susceptibility_score=0.5,
        susceptibility_rank=1,
    )
    c1 = RainCell(lat=12.90, lon=77.60, mm_per_h=[10.0])  # closer
    c2 = RainCell(lat=13.00, lon=77.70, mm_per_h=[20.0])  # further
    rain = RainfallSeries(
        times=[NOW],
        cells=[c1, c2],
        source="unit-test",
        fetched_at=NOW,
        grid_values_identical=False,
    )

    assigned = assign_rain_cells([h], rain)
    assert assigned[0].rain_cell_index == 0
