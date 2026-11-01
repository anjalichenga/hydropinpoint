from __future__ import annotations

import pytest

from hydropinpoint.config import SLOPE_FLOOR_M_PER_M
from hydropinpoint.contracts import Hotspot
from hydropinpoint.engine.hydraulics import required_diameter_m, size_drains


def _hotspot(slope: float, discharge: float) -> Hotspot:
    return Hotspot(
        id=1, lat=12.95, lon=77.65, catchment_area_km2=0.1,
        depression_depth_m=0.5, imperviousness=0.7, runoff_coeff_C=0.8,
        flow_path_slope_S=slope, susceptibility_score=0.9,
        susceptibility_rank=1, hourly_Q_m3s=[discharge],
    )


def test_required_diameter_hand_calculation() -> None:
    # D = (0.1 * 0.013 / (0.3117 * sqrt(0.005))) ** (3/8)
    assert required_diameter_m(0.1, 0.005) == pytest.approx(0.3459558, rel=1e-5)


def test_slope_floor_is_flagged() -> None:
    result = size_drains([_hotspot(SLOPE_FLOOR_M_PER_M / 10, 0.1)])[0]
    assert result.slope_floor_applied is True
    assert result.hourly_required_D_m[0] > 0
