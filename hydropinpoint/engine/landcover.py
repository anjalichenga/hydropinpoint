"""engine/landcover.py - Runoff coefficient C and imperviousness per catchment.

Owner: Person A.

Public API:
    compute_landcover_stats(catchment_labels, landcover_array, transform)
        For each catchment label (> 0), computes:
            imperviousness   float 0..1 (fraction of built-up cells, WorldCover class 50)
            runoff_coeff_C   float 0..1 (area-weighted C from config.py coefficients)
        Returns a dict mapping sink id -> {"imperviousness": ..., "runoff_coeff_C": ...}
"""
from __future__ import annotations

from typing import Any

import numpy as np
from scipy import ndimage

from hydropinpoint.config import (
    RUNOFF_COEFF_BY_CLASS,
    RUNOFF_COEFF_DEFAULT,
)

BUILT_UP_CLASS_CODE = 50


def compute_landcover_stats(
    catchment_labels: np.ndarray,
    landcover_array: np.ndarray,
    transform: Any = None,
) -> dict[int, dict[str, float]]:
    """Compute imperviousness and area-weighted runoff coefficient C for each catchment."""
    stats: dict[int, dict[str, float]] = {}

    # If DEM and WorldCover grids differ in resolution/dimensions, align landcover to DEM grid
    if landcover_array.shape != catchment_labels.shape:
        zoom_factors = (
            catchment_labels.shape[0] / landcover_array.shape[0],
            catchment_labels.shape[1] / landcover_array.shape[1],
        )
        aligned_lc = ndimage.zoom(landcover_array, zoom_factors, order=0)
    else:
        aligned_lc = landcover_array

    unique_labels = np.unique(catchment_labels)
    # Exclude 0 (unassigned / non-catchment cells)
    valid_labels = [int(lbl) for lbl in unique_labels if lbl > 0]

    for lbl in valid_labels:
        mask = (catchment_labels == lbl)
        total_cells = int(np.sum(mask))
        if total_cells == 0:
            stats[lbl] = {"imperviousness": 0.0, "runoff_coeff_C": RUNOFF_COEFF_DEFAULT}
            continue

        classes_in_catchment = aligned_lc[mask]
        built_up_count = int(np.sum(classes_in_catchment == BUILT_UP_CLASS_CODE))
        imperviousness = built_up_count / total_cells

        # Area-weighted runoff coefficient C
        unique_classes, counts = np.unique(classes_in_catchment, return_counts=True)
        weighted_c_sum = 0.0
        for cls_code, count in zip(unique_classes, counts, strict=False):
            c_val = RUNOFF_COEFF_BY_CLASS.get(int(cls_code), RUNOFF_COEFF_DEFAULT)
            weighted_c_sum += c_val * count

        avg_c = weighted_c_sum / total_cells

        stats[lbl] = {
            "imperviousness": round(float(imperviousness), 3),
            "runoff_coeff_C": round(float(avg_c), 3),
        }

    return stats
