"""check_contracts.py – import-time and schema-level sanity checks.

Run with: python -m hydropinpoint.check_contracts

CI calls this via `make contracts`. It must not need network access.

What it checks:
1. Every sub-package module that exists can be imported without error.
2. The public interface functions that exist have the agreed signatures.
3. A ToolResult and EngineResult round-trip through Pydantic with minimal data
   (schema / type check only; no real data required).
"""
from __future__ import annotations

import importlib
import inspect
import sys
from datetime import UTC, datetime

# ---------------------------------------------------------------------------
# 1. Module import checks
# ---------------------------------------------------------------------------

# Modules that should exist at scaffold time (stubs are fine).
EXPECTED_MODULES = [
    "hydropinpoint.contracts",
    "hydropinpoint.config",
    "hydropinpoint.fetch",
    "hydropinpoint.engine",
    "hydropinpoint.replay",
    "hydropinpoint.tools",
    "hydropinpoint.agent",
    "hydropinpoint.app",
]

# Modules that will exist once A/B implement them (skip if absent at scaffold).
OPTIONAL_MODULES = [
    "hydropinpoint.fetch.dem",
    "hydropinpoint.fetch.landcover",
    "hydropinpoint.fetch.rainfall",
    "hydropinpoint.fetch.osm",
    "hydropinpoint.fetch.geocode",
    "hydropinpoint.fetch.routing",
    "hydropinpoint.fetch.wards",
    "hydropinpoint.fetch.cache",
    "hydropinpoint.engine.dem",
    "hydropinpoint.engine.landcover",
    "hydropinpoint.engine.rainfall",
    "hydropinpoint.engine.hydrology",
    "hydropinpoint.engine.scoring",
    "hydropinpoint.engine.hydraulics",
    "hydropinpoint.pipeline",
]


def check_imports() -> list[str]:
    """Return a list of error strings (empty = all OK)."""
    errors: list[str] = []
    for name in EXPECTED_MODULES:
        try:
            importlib.import_module(name)
        except Exception as exc:
            errors.append(f"REQUIRED import failed: {name}: {exc}")
    for name in OPTIONAL_MODULES:
        try:
            importlib.import_module(name)
        except ModuleNotFoundError:
            pass  # not yet implemented; that is fine
        except Exception as exc:
            errors.append(f"OPTIONAL import error (module exists but broken): {name}: {exc}")
    return errors


# ---------------------------------------------------------------------------
# 2. Interface signature checks
# ---------------------------------------------------------------------------

INTERFACE_SIGNATURES = {
    # (module, function_name): (param_names_in_order,)
    "hydropinpoint.engine.hydrology": {
        "compute_terrain": ["box"],
        "compute_runoff": ["hotspots", "rain"],
    },
    "hydropinpoint.engine.hydraulics": {
        "size_drains": ["hotspots"],
    },
    "hydropinpoint.pipeline": {
        "run": ["box"],
    },
}


def check_signatures() -> list[str]:
    """Return error strings for any implemented function with wrong signature."""
    errors: list[str] = []
    for mod_name, funcs in INTERFACE_SIGNATURES.items():
        try:
            mod = importlib.import_module(mod_name)
        except ModuleNotFoundError:
            continue  # not yet implemented
        except Exception as exc:
            errors.append(f"Cannot import {mod_name}: {exc}")
            continue
        for fn_name, expected_params in funcs.items():
            fn = getattr(mod, fn_name, None)
            if fn is None:
                continue  # not yet implemented
            sig = inspect.signature(fn)
            actual = list(sig.parameters.keys())
            if actual != expected_params:
                errors.append(
                    f"Signature mismatch: {mod_name}.{fn_name}. "
                    f"Expected params {expected_params}, got {actual}."
                )
    return errors


# ---------------------------------------------------------------------------
# 3. Model round-trip (schema check, no real data)
# ---------------------------------------------------------------------------

def check_model_roundtrip() -> list[str]:
    """Build minimal instances of ToolResult and EngineResult and round-trip them."""
    errors: list[str] = []
    try:
        from hydropinpoint.contracts import (
            BoundingBox,
            DrainSizing,
            EngineResult,
            Hotspot,
            RainCell,
            RainfallSeries,
            ToolResult,
        )
        now = datetime.now(tz=UTC)

        # ToolResult round-trip
        tr = ToolResult(value={"test": 1}, source="unit-test", fetched_at=now)
        assert tr.model_dump()["source"] == "unit-test", "ToolResult dump failed"

        # ToolResult with error
        tr_err = ToolResult(value=None, source="unit-test", fetched_at=now, error="timeout")
        assert tr_err.error == "timeout"

        # Minimal EngineResult
        box = BoundingBox(west=77.60, south=12.90, east=77.70, north=13.00)
        rain_cell = RainCell(lat=12.95, lon=77.65, mm_per_h=[0.0])
        rain = RainfallSeries(
            times=[now],
            cells=[rain_cell],
            source="unit-test",
            fetched_at=now,
            grid_values_identical=True,
            label="LIVE",
        )
        hotspot = Hotspot(
            id=1,
            lat=12.95,
            lon=77.65,
            catchment_area_km2=0.1,
            depression_depth_m=0.5,
            imperviousness=0.7,
            runoff_coeff_C=0.8,
            flow_path_slope_S=0.005,
            susceptibility_score=0.9,
            susceptibility_rank=1,
            hourly_Q_m3s=[0.0],
        )
        sizing = DrainSizing(
            hotspot_id=1,
            hourly_required_D_m=[0.2],
            slope_floor_applied=False,
        )
        er = EngineResult(
            box=box,
            hotspots=[hotspot],
            sizings=[sizing],
            rainfall=rain,
            dem_vintage="Copernicus DEM GLO-30 2021",
            landcover_vintage="ESA WorldCover 2020",
            generated_at=now,
        )
        dumped = er.model_dump()
        assert dumped["dem_vintage"] == "Copernicus DEM GLO-30 2021"
        assert dumped["hotspots"][0]["id"] == 1
        assert dumped["sizings"][0]["capacity_note"] == "existing capacity unknown"

    except Exception as exc:
        errors.append(f"Model round-trip failed: {exc}")
    return errors


# ---------------------------------------------------------------------------
# 4. Field-unit docstring presence check
# ---------------------------------------------------------------------------

def check_field_units() -> list[str]:
    """Verify that key Hotspot fields carry a unit comment or docstring."""
    # This is a lightweight structural check: we confirm the module imports cleanly
    # and the class has the fields the contract requires (Pydantic will error if not).
    errors: list[str] = []
    try:
        from hydropinpoint.contracts import Hotspot
        required_fields = [
            "id", "lat", "lon",
            "catchment_area_km2", "depression_depth_m",
            "imperviousness", "runoff_coeff_C", "flow_path_slope_S",
            "susceptibility_score", "susceptibility_rank",
            "hourly_Q_m3s", "outside_rational_validity",
        ]
        actual = set(Hotspot.model_fields.keys())
        missing = [f for f in required_fields if f not in actual]
        if missing:
            errors.append(f"Hotspot missing fields: {missing}")
    except Exception as exc:
        errors.append(f"Hotspot field check failed: {exc}")
    return errors


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    all_errors: list[str] = []
    all_errors += check_imports()
    all_errors += check_signatures()
    all_errors += check_model_roundtrip()
    all_errors += check_field_units()

    if all_errors:
        print("check_contracts FAILED:")
        for e in all_errors:
            print(f"  ERROR: {e}")
        return 1

    print("check_contracts OK: all imports, signatures and model round-trips passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
