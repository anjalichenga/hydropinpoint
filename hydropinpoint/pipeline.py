"""End-to-end join between Person A's runoff engine and Person B's hydraulics."""
from __future__ import annotations

import argparse
import importlib
import math
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from functools import lru_cache
from typing import Any

from hydropinpoint.config import DEFAULT_BOX, OSM_MATCH_RADIUS_M
from hydropinpoint.contracts import BoundingBox, EngineResult, Hotspot, RainfallSeries
from hydropinpoint.engine.hydraulics import size_drains
from hydropinpoint.fetch.osm import fetch_osm


class IntegrationUnavailableError(RuntimeError):
    """Raised while Person A's required module has not landed yet."""


def _function(module_name: str, names: tuple[str, ...]) -> Callable[..., Any]:
    try:
        module = importlib.import_module(module_name)
    except ModuleNotFoundError as exc:
        raise IntegrationUnavailableError(f"missing Person A module: {module_name}") from exc
    for name in names:
        function = getattr(module, name, None)
        if callable(function):
            return function
    raise IntegrationUnavailableError(f"{module_name} must expose one of: {', '.join(names)}")


def _live_rain(box: BoundingBox) -> RainfallSeries:
    fetch = _function(
        "hydropinpoint.fetch.rainfall",
        ("fetch_rainfall", "fetch_forecast", "get_forecast"),
    )
    value = fetch(box)
    if hasattr(value, "value"):
        if value.error:
            raise IntegrationUnavailableError(f"rainfall fetch failed: {value.error}")
        value = value.value
    return RainfallSeries.model_validate(value)


def _haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius_m = 6_371_000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * radius_m * math.asin(math.sqrt(a))


def _match_mapped_drains(hotspots: list[Hotspot], sizings: list[Any], records: list[dict]) -> None:
    drains = [
        record for record in records
        if record.get("kind") in {"drain", "culvert"} and record.get("mapped_size_m")
    ]
    hotspot_by_id = {hotspot.id: hotspot for hotspot in hotspots}
    for sizing in sizings:
        hotspot = hotspot_by_id[sizing.hotspot_id]
        candidates = [
            (record, _haversine_m(hotspot.lat, hotspot.lon, record["lat"], record["lon"]))
            for record in drains
        ]
        candidates = [candidate for candidate in candidates if candidate[1] <= OSM_MATCH_RADIUS_M]
        if not candidates:
            continue
        mapped = min(candidates, key=lambda candidate: candidate[1])[0]
        sizing.mapped_drain_size_m = float(mapped["mapped_size_m"])
        peak_required = max(sizing.hourly_required_D_m, default=0.0)
        sizing.mapped_narrower_than_required = sizing.mapped_drain_size_m < peak_required
        sizing.capacity_note = "mapped OSM width/diameter compared with required circular diameter"


def _vintage(module_name: str, attribute: str) -> str:
    try:
        return str(getattr(importlib.import_module(module_name), attribute))
    except (ModuleNotFoundError, AttributeError):
        return "vintage unavailable from source module"


def run(box: BoundingBox) -> EngineResult:
    compute_terrain = _function("hydropinpoint.engine.hydrology", ("compute_terrain",))
    compute_runoff = _function("hydropinpoint.engine.hydrology", ("compute_runoff",))
    with ThreadPoolExecutor(max_workers=3) as pool:
        rain_future = pool.submit(_live_rain, box)
        terrain_future = pool.submit(compute_terrain, box)
        osm_future = pool.submit(fetch_osm, box)
        rain = rain_future.result()
        terrain = [Hotspot.model_validate(row) for row in terrain_future.result()]
        osm = osm_future.result()
    hotspots = [Hotspot.model_validate(row) for row in compute_runoff(terrain, rain)]
    sizings = size_drains(hotspots)
    notes: list[str] = []

    if osm.value is not None:
        _match_mapped_drains(hotspots, sizings, osm.value)
    if osm.error:
        notes.append(osm.error)
    if osm.cached:
        notes.append(f"OSM data served from cache; fetched at {osm.fetched_at.isoformat()}")

    return EngineResult(
        box=box,
        hotspots=hotspots,
        sizings=sizings,
        rainfall=rain,
        dem_vintage=_vintage("hydropinpoint.fetch.dem", "DEM_VINTAGE"),
        landcover_vintage=_vintage("hydropinpoint.fetch.landcover", "LANDCOVER_VINTAGE"),
        notes=notes,
        generated_at=datetime.now(UTC),
    )


@lru_cache(maxsize=4)
def _run_cached(
    west: float,
    south: float,
    east: float,
    north: float,
    time_bucket: int,
) -> EngineResult:
    del time_bucket
    return run(BoundingBox(west=west, south=south, east=east, north=north))


def run_cached(box: BoundingBox = DEFAULT_BOX) -> EngineResult:
    """Reuse a pipeline result for 15 minutes across UI pages and agent questions."""
    time_bucket = int(time.time() // 900)
    return _run_cached(box.west, box.south, box.east, box.north, time_bucket)


def _print_top(result: EngineResult, count: int) -> None:
    sizing_by_id = {sizing.hotspot_id: sizing for sizing in result.sizings}
    ranked = sorted(result.hotspots, key=lambda hotspot: hotspot.susceptibility_rank)[:count]
    for hotspot in ranked:
        sizing = sizing_by_id[hotspot.id]
        print(
            f"#{hotspot.susceptibility_rank} hotspot={hotspot.id} "
            f"peak_Q_m3s={max(hotspot.hourly_Q_m3s, default=0):.4f} "
            f"required_D_m={max(sizing.hourly_required_D_m, default=0):.3f} "
            f"rain_source={result.rainfall.source} "
            f"fetched_at={result.rainfall.fetched_at.isoformat()}"
        )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--top", type=int, default=0)
    args = parser.parse_args()
    try:
        result = run(DEFAULT_BOX)
    except IntegrationUnavailableError as exc:
        print(f"pipeline unavailable until Person A's modules land: {exc}")
        return 2
    if args.smoke:
        EngineResult.model_validate(result.model_dump())
        print(f"smoke: ok ({len(result.hotspots)} real hotspots)")
    if args.top:
        _print_top(result, args.top)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

