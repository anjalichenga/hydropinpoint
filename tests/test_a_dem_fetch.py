"""tests/test_a_dem_fetch.py - Unit tests for Copernicus DEM fetcher helpers.

Owner: Person A.
No network calls. Hand-calculated values and pure logic tests.
"""
from __future__ import annotations

from hydropinpoint.contracts import BoundingBox
from hydropinpoint.fetch.dem import tile_id_str, tile_url, tiles_for_box


def test_tile_id_str_glo30():
    name = tile_id_str(12, 77, 30)
    assert name == "Copernicus_DSM_COG_10_N12_00_E077_00_DEM"


def test_tile_id_str_glo90():
    name = tile_id_str(12, 77, 90)
    assert name == "Copernicus_DSM_COG_30_N12_00_E077_00_DEM"


def test_tile_id_str_southern_western_hemisphere():
    name = tile_id_str(-5, -60, 30)
    assert name == "Copernicus_DSM_COG_10_S05_00_W060_00_DEM"


def test_tile_url():
    url = tile_url("Copernicus_DSM_COG_10_N12_00_E077_00_DEM", 30)
    assert url == "https://copernicus-dem-30m.s3.amazonaws.com/Copernicus_DSM_COG_10_N12_00_E077_00_DEM/Copernicus_DSM_COG_10_N12_00_E077_00_DEM.tif"


def test_tiles_for_single_box():
    # Box entirely inside N12 E077
    box = BoundingBox(west=77.60, south=12.90, east=77.70, north=12.98)
    tiles = tiles_for_box(box)
    assert tiles == [(12, 77)]


def test_tiles_for_crossing_latitude_box():
    # Box crossing 13.0 N
    box = BoundingBox(west=77.60, south=12.95, east=77.70, north=13.05)
    tiles = tiles_for_box(box)
    assert (12, 77) in tiles
    assert (13, 77) in tiles
    assert len(tiles) == 2
