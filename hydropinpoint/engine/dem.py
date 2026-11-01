"""engine/dem.py – DEM processing: fill, flow direction, accumulation, catchments.

Owner: Person A.

Public API:
    process_dem(dem_array, transform, crs, config) -> DEMResult (namedtuple or dict)
        Fills depressions (Priority-Flood or NumPy fallback), computes D8 flow
        direction, flow accumulation, delineates catchments for each sink that
        passes the depth and area thresholds in config.py.

        Returns a dict with:
            filled_array     np.ndarray
            flow_dir         np.ndarray  (D8 codes 1..128)
            accumulation     np.ndarray  (cell count)
            sinks            list[dict]  each has keys:
                                         row, col, depth_m, area_km2, centroid_lat, centroid_lon
            catchment_labels np.ndarray  (int, 0 = not assigned)

Notes:
    - Depression depth = filled elevation – original elevation.
    - Sinks shallower than MIN_DEPRESSION_DEPTH_M or smaller than
      MIN_CATCHMENT_AREA_KM2 (from config.py) are discarded.
    - If pysheds or richdem is available, use it; otherwise fall back to a
      NumPy + scikit-image D8 implementation (small, easy to explain to judges).
    - Prints the top-10 sinks by depression depth with area at the end.
"""
from __future__ import annotations

# Implementation by Person A.
# Stub so the package imports cleanly at scaffold time.


def process_dem(dem_array, transform, crs, cfg=None):
    """Fill depressions and compute D8 accumulation and catchments."""
    raise NotImplementedError("process_dem not yet implemented – Person A")
