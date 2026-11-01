"""tests/test_a_landcover_fetch.py - Unit tests for ESA WorldCover helpers.

Owner: Person A.
No network. Hand-calculated tile coordinates.
"""
from __future__ import annotations

from hydropinpoint.contracts import BoundingBox
from hydropinpoint.fetch.landcover import (
    BUILT_UP_CLASS_CODE,
    worldcover_tile_id,
    worldcover_tile_url,
    worldcover_tiles_for_box,
)


def test_built_up_code():
    assert BUILT_UP_CLASS_CODE == 50


def test_worldcover_tile_id():
    # Bengaluru ~12.95 N, 77.65 E
    tile = worldcover_tile_id(12.95, 77.65)
    assert tile == "N12E075"


def test_worldcover_tile_url():
    url = worldcover_tile_url("N12E075")
    assert url == "https://esa-worldcover.s3.eu-central-1.amazonaws.com/v100/2020/map/ESA_WorldCover_10m_2020_v100_N12E075_Map.tif"


def test_worldcover_tiles_for_box():
    # 10x10 km box inside Bengaluru
    box = BoundingBox(west=77.60, south=12.90, east=77.70, north=13.00)
    tiles = worldcover_tiles_for_box(box)
    assert tiles == ["N12E075"]
