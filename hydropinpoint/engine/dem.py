"""engine/dem.py - DEM processing: fill depressions, D8 flow, accumulation, catchments.

Owner: Person A.

Public API:
    process_dem(dem_array, transform, crs, cfg=None) -> dict
        Fills depressions via morphological reconstruction, computes D8 flow
        direction, flow accumulation by elevation order, delineates catchments,
        and filters sinks by depth and area thresholds from config.py.

        Returns a dict with:
            filled_array     np.ndarray (float32)
            depression_depth np.ndarray (float32)
            flow_dir         np.ndarray (uint8, D8 codes 1..128, 0 = pit)
            accumulation     np.ndarray (int32, cell count)
            sinks            list[dict] (row, col, depth_m, area_km2, centroid_lat, centroid_lon)
            catchment_labels np.ndarray (int32, sink id per cell, 0 = none)
"""
from __future__ import annotations

import math
from typing import Any

import numpy as np
import rasterio.transform
from scipy import ndimage
from skimage.morphology import reconstruction

from hydropinpoint.config import (
    MIN_CATCHMENT_AREA_KM2,
    MIN_DEPRESSION_DEPTH_M,
)

# D8 offset lookup: (dr, dc, D8_code, distance_factor)
D8_NEIGHBORS = [
    (0, 1, 1, 1.0),            # East
    (-1, 1, 2, math.sqrt(2)),  # North-East
    (-1, 0, 4, 1.0),           # North
    (-1, -1, 8, math.sqrt(2)), # North-West
    (0, -1, 16, 1.0),          # West
    (1, -1, 32, math.sqrt(2)), # South-West
    (1, 0, 64, 1.0),           # South
    (1, 1, 128, math.sqrt(2)), # South-East
]


def fill_depressions(dem: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Fill depressions using morphological reconstruction by erosion.

    Returns (filled_dem, depression_depth).
    """
    dem_clean = np.where(np.isnan(dem), np.nanmin(dem), dem).astype(np.float64)
    seed = dem_clean.copy()
    seed[1:-1, 1:-1] = np.nanmax(dem_clean) + 1000.0

    filled = reconstruction(seed, dem_clean, method="erosion")
    depth = np.maximum(0.0, filled - dem_clean).astype(np.float32)
    return filled.astype(np.float32), depth


def compute_d8_flow(filled: np.ndarray) -> np.ndarray:
    """Compute D8 flow direction from filled elevation array.

    Direction codes: 1=E, 2=NE, 4=N, 8=NW, 16=W, 32=SW, 64=S, 128=SE, 0=Pit.
    """
    rows, cols = filled.shape
    flow_dir = np.zeros((rows, cols), dtype=np.uint8)

    max_drop = np.zeros((rows, cols), dtype=np.float32)

    for dr, dc, code, dist in D8_NEIGHBORS:
        # Shifted neighbor array
        r_start, r_end = max(0, dr), min(rows, rows + dr)
        c_start, c_end = max(0, dc), min(cols, cols + dc)
        orig_r_start, orig_r_end = max(0, -dr), min(rows, rows - dr)
        orig_c_start, orig_c_end = max(0, -dc), min(cols, cols - dc)

        diff = (
            filled[orig_r_start:orig_r_end, orig_c_start:orig_c_end]
            - filled[r_start:r_end, c_start:c_end]
        ) / dist

        mask = diff > max_drop[orig_r_start:orig_r_end, orig_c_start:orig_c_end]
        max_drop[orig_r_start:orig_r_end, orig_c_start:orig_c_end] = np.where(
            mask, diff, max_drop[orig_r_start:orig_r_end, orig_c_start:orig_c_end]
        )
        flow_dir[orig_r_start:orig_r_end, orig_c_start:orig_c_end] = np.where(
            mask, code, flow_dir[orig_r_start:orig_r_end, orig_c_start:orig_c_end]
        )

    return flow_dir


def compute_flow_accumulation(filled: np.ndarray, flow_dir: np.ndarray) -> np.ndarray:
    """Accumulate cell flow by routing along flow_dir in descending elevation order."""
    rows, cols = filled.shape
    acc = np.ones((rows, cols), dtype=np.int32)

    # Sort indices by elevation descending
    flat_indices = np.argsort(-filled.ravel())

    # Build neighbor offsets map
    dr_map = {1: 0, 2: -1, 4: -1, 8: -1, 16: 0, 32: 1, 64: 1, 128: 1}
    dc_map = {1: 1, 2: 1, 4: 0, 8: -1, 16: -1, 32: -1, 64: 0, 128: 1}

    for idx in flat_indices:
        r = idx // cols
        c = idx % cols
        code = int(flow_dir[r, c])
        if code in dr_map:
            nr = r + dr_map[code]
            nc = c + dc_map[code]
            if 0 <= nr < rows and 0 <= nc < cols:
                acc[nr, nc] += acc[r, c]

    return acc


def delineate_catchments(
    filled: np.ndarray,
    depression_depth: np.ndarray,
    flow_dir: np.ndarray,
    transform: Any,
    min_depth: float = MIN_DEPRESSION_DEPTH_M,
    min_area_km2: float = MIN_CATCHMENT_AREA_KM2,
) -> tuple[np.ndarray, list[dict]]:
    """Identify significant sinks and delineate their upstream catchments.

    Returns (catchment_labels, sinks_metadata).
    """
    rows, cols = filled.shape
    sink_mask = depression_depth >= min_depth

    # Label contiguous sink clusters
    labeled_sinks, num_sinks = ndimage.label(sink_mask)
    if num_sinks == 0:
        return np.zeros((rows, cols), dtype=np.int32), []

    # Map each cell to downstream sink via elevation order (descending)
    catchment_labels = np.zeros((rows, cols), dtype=np.int32)

    # Initialize sink cells with their sink cluster label
    catchment_labels[sink_mask] = labeled_sinks[sink_mask]

    # Approximate cell area in km2
    dx_deg = abs(transform[0])
    dy_deg = abs(transform[4])
    # Roughly 111 km per degree of latitude and longitude at ~13 N
    cell_area_km2 = (dx_deg * 111.0 * math.cos(math.radians(13.0))) * (dy_deg * 111.0)
    if cell_area_km2 <= 0:
        cell_area_km2 = 0.0009  # default 30m cell ~ 0.0009 km2

    # Flow routing: flow downstream from high to low
    dr_map = {1: 0, 2: -1, 4: -1, 8: -1, 16: 0, 32: 1, 64: 1, 128: 1}
    dc_map = {1: 1, 2: 1, 4: 0, 8: -1, 16: -1, 32: -1, 64: 0, 128: 1}

    # Route upstream: for each cell in elevation order (ascending), propagate label downstream
    sorted_asc = np.argsort(filled.ravel())
    for idx in sorted_asc:
        r = idx // cols
        c = idx % cols
        current_lbl = catchment_labels[r, c]
        if current_lbl > 0:
            continue
        code = int(flow_dir[r, c])
        if code in dr_map:
            nr = r + dr_map[code]
            nc = c + dc_map[code]
            if 0 <= nr < rows and 0 <= nc < cols:
                catchment_labels[r, c] = catchment_labels[nr, nc]

    # Collect metadata for valid sinks passing min_area_km2
    sinks_list: list[dict] = []
    reassigned_labels = np.zeros((rows, cols), dtype=np.int32)
    next_id = 1

    for s_id in range(1, num_sinks + 1):
        c_mask = catchment_labels == s_id
        cell_count = int(np.sum(c_mask))
        total_area_km2 = cell_count * cell_area_km2
        if total_area_km2 < min_area_km2:
            continue

        s_pixels = (labeled_sinks == s_id)
        max_d = float(np.max(depression_depth[s_pixels]))
        sink_rows, sink_cols = np.where(s_pixels)
        mean_r = float(np.mean(sink_rows))
        mean_c = float(np.mean(sink_cols))

        # Pixel to geographic coordinate using transform
        lon, lat = rasterio.transform.xy(transform, mean_r, mean_c)

        reassigned_labels[c_mask] = next_id
        sinks_list.append({
            "id": next_id,
            "row": int(mean_r),
            "col": int(mean_c),
            "depth_m": round(max_d, 3),
            "area_km2": round(total_area_km2, 5),
            "centroid_lat": round(lat, 5),
            "centroid_lon": round(lon, 5),
        })
        next_id += 1

    return reassigned_labels, sinks_list


def process_dem(dem_array: np.ndarray, transform: Any, crs: Any, cfg: Any = None) -> dict[str, Any]:
    """Execute complete DEM processing pipeline."""
    filled, depth = fill_depressions(dem_array)
    flow_dir = compute_d8_flow(filled)
    acc = compute_flow_accumulation(filled, flow_dir)
    labels, sinks = delineate_catchments(filled, depth, flow_dir, transform)

    # Print top-10 sinks as mandated in Person A definition of done
    print(
        f"[DEM Engine] Delineated {len(sinks)} significant sinks "
        f"(depth >= {MIN_DEPRESSION_DEPTH_M}m, area >= {MIN_CATCHMENT_AREA_KM2}km²):"
    )
    sorted_sinks = sorted(sinks, key=lambda s: s["depth_m"], reverse=True)
    for s in sorted_sinks[:10]:
        print(
            f"  sink id={s['id']}: depth={s['depth_m']:.2f} m, "
            f"area={s['area_km2']:.4f} km², "
            f"lat={s['centroid_lat']:.4f}, lon={s['centroid_lon']:.4f}"
        )

    return {
        "filled_array": filled,
        "depression_depth": depth,
        "flow_dir": flow_dir,
        "accumulation": acc,
        "sinks": sinks,
        "catchment_labels": labels,
    }
