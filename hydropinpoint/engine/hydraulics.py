"""Pure hydraulic sizing from runoff to a screening-level pipe diameter."""
from __future__ import annotations

import math

from hydropinpoint.config import MANNING_N, MIN_PIPE_SLOPE
from hydropinpoint.contracts import DrainSizing, Hotspot

MANNING_CIRCULAR_PIPE_FACTOR = 0.3117


def required_diameter_m(
    discharge_m3s: float,
    slope_m_per_m: float,
    manning_n: float = MANNING_N,
) -> float:
    """Return full-flow circular-pipe diameter in metres using Manning's equation."""
    if discharge_m3s < 0:
        raise ValueError("discharge_m3s must be non-negative")
    if slope_m_per_m <= 0:
        raise ValueError("slope_m_per_m must be positive")
    if manning_n <= 0:
        raise ValueError("manning_n must be positive")
    if discharge_m3s == 0:
        return 0.0
    return (
        discharge_m3s * manning_n
        / (MANNING_CIRCULAR_PIPE_FACTOR * math.sqrt(slope_m_per_m))
    ) ** (3 / 8)


def size_drains(hotspots: list[Hotspot]) -> list[DrainSizing]:
    """Size one full-flow circular drain for every hourly runoff value."""
    output: list[DrainSizing] = []
    for hotspot in hotspots:
        raw_slope = hotspot.flow_path_slope_S
        slope_floor_applied = raw_slope < MIN_PIPE_SLOPE
        slope = max(raw_slope, MIN_PIPE_SLOPE)
        output.append(
            DrainSizing(
                hotspot_id=hotspot.id,
                hourly_required_D_m=[
                    required_diameter_m(discharge, slope) for discharge in hotspot.hourly_Q_m3s
                ],
                slope_floor_applied=slope_floor_applied,
            )
        )
    return output

