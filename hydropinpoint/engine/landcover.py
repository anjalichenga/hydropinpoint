"""engine/landcover.py – runoff coefficient and imperviousness per catchment.

Owner: Person A.

Public API:
    compute_landcover_stats(catchment_labels, landcover_array, transform) -> list[dict]
        For each catchment label (sink id), computes:
            imperviousness   float  0..1  (fraction of built-up cells, class 50)
            runoff_coeff_C   float  0..1  (area-weighted C from config.py coefficients)
        Returns a list of dicts keyed by sink id.

Notes:
    - Both arrays must be on the same grid (reproject landcover to DEM grid if needed).
    - C coefficients come from config.RUNOFF_COEFF_BY_CLASS; default from
      config.RUNOFF_COEFF_DEFAULT for unknown classes.
    - The mix (weighted average) approach is standard for heterogeneous catchments.
"""
from __future__ import annotations


def compute_landcover_stats(catchment_labels, landcover_array, transform):
    """Return imperviousness and runoff coefficient per catchment."""
    raise NotImplementedError("compute_landcover_stats not yet implemented – Person A")
