"""pipeline.py – end-to-end run: terrain → runoff → drain sizing.

Owner: Person B (calls A's compute_terrain / compute_runoff then B's size_drains).

Public interface (as agreed in contracts.py):

    run(box: BoundingBox) -> EngineResult

CLI smoke check:
    python -m hydropinpoint.pipeline --smoke
    python -m hydropinpoint.pipeline --top 3

Notes:
    - Imports A's and B's modules lazily to keep CI import checks fast.
    - On any source failure, adds a note to EngineResult.notes and continues
      with degraded output rather than crashing (unless no DEM at all).
"""
from __future__ import annotations

import argparse
import sys

from hydropinpoint.contracts import BoundingBox, EngineResult


def run(box: BoundingBox) -> EngineResult:
    """Run the full HydroPinpoint pipeline for *box*."""
    raise NotImplementedError("pipeline.run not yet implemented – Person B")


def _smoke(box: BoundingBox | None = None) -> None:
    """Quick smoke check: run the pipeline on a small default box."""
    from hydropinpoint.config import UI_DEFAULT_BOX
    b = box or BoundingBox(**UI_DEFAULT_BOX)
    print(f"[smoke] Running pipeline on {b} …")
    result = run(b)
    print(f"[smoke] OK: {len(result.hotspots)} hotspots, {len(result.sizings)} sizings")
    print(f"[smoke] Notes: {result.notes}")
    for h in result.hotspots[:3]:
        print(f"  hotspot {h.id}: lat={h.lat:.4f} lon={h.lon:.4f} "
              f"Q_peak={max(h.hourly_Q_m3s, default=0):.4f} m³/s "
              f"rank={h.susceptibility_rank}")


def _top(n: int, box: BoundingBox | None = None) -> None:
    from hydropinpoint.config import UI_DEFAULT_BOX
    b = box or BoundingBox(**UI_DEFAULT_BOX)
    result = run(b)
    print(f"Top {n} hotspots  |  dem: {result.dem_vintage}  |  lc: {result.landcover_vintage}")
    print(f"Rainfall source: {result.rainfall.source}  fetched_at: {result.rainfall.fetched_at}")
    for h in result.hotspots[:n]:
        peak_q = max(h.hourly_Q_m3s, default=0.0)
        ds = next((s for s in result.sizings if s.hotspot_id == h.id), None)
        peak_d = max(ds.hourly_required_D_m, default=0.0) if ds else float("nan")
        print(f"  rank={h.susceptibility_rank:3d} id={h.id:4d} "
              f"lat={h.lat:.4f} lon={h.lon:.4f} "
              f"depth={h.depression_depth_m:.2f}m "
              f"area={h.catchment_area_km2:.4f}km² "
              f"C={h.runoff_coeff_C:.2f} "
              f"Q_peak={peak_q:.4f}m³/s "
              f"D_req={peak_d:.3f}m")
    if result.notes:
        print("Notes:", result.notes)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="HydroPinpoint pipeline")
    parser.add_argument("--smoke", action="store_true", help="Quick smoke check")
    parser.add_argument("--top", type=int, metavar="N", help="Print top N hotspots")
    args = parser.parse_args()

    if args.smoke:
        _smoke()
    elif args.top:
        _top(args.top)
    else:
        parser.print_help()
        sys.exit(1)
