"""engine/hydraulics.py – Manning pipe-sizing from runoff discharge.

Owner: Person B.

Public interface (as agreed in contracts.py):

    size_drains(hotspots: list[Hotspot]) -> list[DrainSizing]
        For each hotspot with hourly_Q_m3s filled, computes the required full-flow
        circular pipe diameter D (metres) using Manning's equation:
            Q = (1/n) * A_pipe * R^(2/3) * S^(1/2)
        where:
            A_pipe = pi * D^2 / 4
            R = D / 4  (hydraulic radius of full circular pipe)
            n = MANNING_N_PIPE from config.py
            S = max(flow_path_slope_S, SLOPE_FLOOR_M_PER_M) from config.py

        Sets slope_floor_applied=True when the floor changes the slope.
        Rounds up D to the nearest standard size in STANDARD_PIPE_DIAMETERS_M.
        Tries to match mapped_drain_size_m from OSM (B's tools); sets
        mapped_narrower_than_required accordingly.
        capacity_note is always "existing capacity unknown".

Notes:
    - Do not use the slope floor in A's code; B applies it here.
    - Outside_rational_validity hotspots are sized anyway (Q is an underestimate);
      a warning is added to the capacity_note.
"""
from __future__ import annotations

from hydropinpoint.contracts import DrainSizing, Hotspot


def size_drains(hotspots: list[Hotspot]) -> list[DrainSizing]:
    """Compute required pipe diameter for each hotspot (Manning full-flow)."""
    raise NotImplementedError("size_drains not yet implemented – Person B")
