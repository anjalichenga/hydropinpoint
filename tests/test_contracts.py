"""tests/test_contracts.py – sync-0 gate: model construction and field-unit checks.

Run with: pytest tests/test_contracts.py
No network, no real data.
"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from hydropinpoint.contracts import (
    BoundingBox,
    DrainSizing,
    EngineResult,
    Hotspot,
    RainCell,
    RainfallSeries,
    ToolResult,
)

NOW = datetime.now(tz=timezone.utc)


# ---------------------------------------------------------------------------
# ToolResult
# ---------------------------------------------------------------------------

def test_tool_result_success():
    tr = ToolResult(value=42, source="test-source", fetched_at=NOW)
    assert tr.value == 42
    assert tr.cached is False
    assert tr.error is None


def test_tool_result_error():
    tr = ToolResult(value=None, source="test-source", fetched_at=NOW, error="timeout")
    assert tr.value is None
    assert tr.error == "timeout"


def test_tool_result_cached():
    tr = ToolResult(value={"x": 1}, source="cache", fetched_at=NOW, cached=True)
    assert tr.cached is True


# ---------------------------------------------------------------------------
# RainfallSeries
# ---------------------------------------------------------------------------

def make_rain(label="LIVE") -> RainfallSeries:
    cell = RainCell(lat=12.95, lon=77.65, mm_per_h=[1.0, 2.0])
    return RainfallSeries(
        times=[NOW, NOW],
        cells=[cell],
        source="Open-Meteo forecast",
        fetched_at=NOW,
        grid_values_identical=True,
        label=label,
    )


def test_rainfall_live():
    rain = make_rain("LIVE")
    assert rain.label == "LIVE"
    assert len(rain.cells) == 1
    assert rain.grid_values_identical is True


def test_rainfall_historical():
    rain = make_rain("HISTORICAL REPLAY")
    assert rain.label == "HISTORICAL REPLAY"


def test_rainfall_invalid_label():
    with pytest.raises(Exception):
        RainfallSeries(
            times=[NOW],
            cells=[],
            source="x",
            fetched_at=NOW,
            grid_values_identical=False,
            label="WRONG",  # type: ignore[arg-type]
        )


# ---------------------------------------------------------------------------
# Hotspot
# ---------------------------------------------------------------------------

def make_hotspot(**overrides) -> Hotspot:
    defaults = dict(
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
    )
    defaults.update(overrides)
    return Hotspot(**defaults)


def test_hotspot_defaults():
    h = make_hotspot()
    assert h.hourly_Q_m3s == []
    assert h.outside_rational_validity is False
    assert h.rain_cell_index == 0


def test_hotspot_with_q():
    h = make_hotspot(hourly_Q_m3s=[0.1, 0.2, 0.3])
    assert len(h.hourly_Q_m3s) == 3


def test_hotspot_outside_validity():
    h = make_hotspot(outside_rational_validity=True)
    assert h.outside_rational_validity is True


def test_hotspot_fields_present():
    """All required fields from contracts.py must exist."""
    required = [
        "id", "lat", "lon",
        "catchment_area_km2", "depression_depth_m",
        "imperviousness", "runoff_coeff_C", "flow_path_slope_S",
        "susceptibility_score", "susceptibility_rank",
        "hourly_Q_m3s", "outside_rational_validity",
    ]
    fields = set(Hotspot.model_fields.keys())
    for f in required:
        assert f in fields, f"Hotspot missing field: {f}"


# ---------------------------------------------------------------------------
# DrainSizing
# ---------------------------------------------------------------------------

def test_drain_sizing_defaults():
    ds = DrainSizing(hotspot_id=1, hourly_required_D_m=[0.2], slope_floor_applied=False)
    assert ds.capacity_note == "existing capacity unknown"
    assert ds.mapped_drain_size_m is None
    assert ds.mapped_narrower_than_required is None


def test_drain_sizing_with_mapped():
    ds = DrainSizing(
        hotspot_id=1,
        hourly_required_D_m=[0.3],
        slope_floor_applied=True,
        mapped_drain_size_m=0.25,
        mapped_narrower_than_required=True,
    )
    assert ds.mapped_narrower_than_required is True


# ---------------------------------------------------------------------------
# BoundingBox
# ---------------------------------------------------------------------------

def test_bounding_box():
    box = BoundingBox(west=77.60, south=12.90, east=77.70, north=13.00)
    assert box.west < box.east
    assert box.south < box.north


# ---------------------------------------------------------------------------
# EngineResult
# ---------------------------------------------------------------------------

def test_engine_result_round_trip():
    box = BoundingBox(west=77.60, south=12.90, east=77.70, north=13.00)
    rain = make_rain()
    h = make_hotspot(hourly_Q_m3s=[0.1])
    ds = DrainSizing(hotspot_id=1, hourly_required_D_m=[0.2], slope_floor_applied=False)
    er = EngineResult(
        box=box,
        hotspots=[h],
        sizings=[ds],
        rainfall=rain,
        dem_vintage="Copernicus DEM GLO-30 2021",
        landcover_vintage="ESA WorldCover 2020",
        generated_at=NOW,
    )
    dumped = er.model_dump()
    assert dumped["dem_vintage"] == "Copernicus DEM GLO-30 2021"
    assert dumped["notes"] == []
    assert dumped["hotspots"][0]["id"] == 1
    assert dumped["sizings"][0]["capacity_note"] == "existing capacity unknown"


def test_engine_result_with_notes():
    box = BoundingBox(west=77.60, south=12.90, east=77.70, north=13.00)
    rain = make_rain()
    er = EngineResult(
        box=box,
        hotspots=[],
        sizings=[],
        rainfall=rain,
        dem_vintage="Copernicus DEM GLO-30 2021",
        landcover_vintage="ESA WorldCover 2020",
        generated_at=NOW,
        notes=["GLO-90 fallback used for tile N13E077"],
    )
    assert "GLO-90 fallback" in er.notes[0]
