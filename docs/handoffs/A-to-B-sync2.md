# Handoff A to B: Terrain and Runoff Engine (Sync-2 & Sync-3)

## Summary
Person A has completed the "rain to runoff" half of HydroPinpoint:
- Elevation model fetching & windowing: [`hydropinpoint.fetch.dem`](file:///C:/Users/ANJALI/Desktop/nxtwave/hydropinpoint/fetch/dem.py) (Copernicus DEM 30m / 90m fallback)
- Land cover fetching: [`hydropinpoint.fetch.landcover`](file:///C:/Users/ANJALI/Desktop/nxtwave/hydropinpoint/fetch/landcover.py) (ESA WorldCover 2020)
- Rainfall forecasting: [`hydropinpoint.fetch.rainfall`](file:///C:/Users/ANJALI/Desktop/nxtwave/hydropinpoint/fetch/rainfall.py) (Open-Meteo 72h forecast & ERA5 archive)
- Hydrology engine: [`hydropinpoint.engine.hydrology`](file:///C:/Users/ANJALI/Desktop/nxtwave/hydropinpoint/engine/hydrology.py) (`compute_terrain` and `compute_runoff`)
- Scoring & ranking: [`hydropinpoint.engine.scoring`](file:///C:/Users/ANJALI/Desktop/nxtwave/hydropinpoint/engine/scoring.py) (`score_hotspots`)
- Historical replay plausibility check: [`hydropinpoint.replay.run`](file:///C:/Users/ANJALI/Desktop/nxtwave/hydropinpoint/replay/run.py)

---

## How to Call from Person B (`pipeline.py` or agent tools)

```python
from hydropinpoint.contracts import BoundingBox
from hydropinpoint.fetch.rainfall import fetch_forecast
from hydropinpoint.engine.hydrology import compute_terrain, compute_runoff

# 1. Define region bounding box
box = BoundingBox(west=77.60, south=12.90, east=77.70, north=13.00)

# 2. Compute static terrain properties (fills centroids, slope S, C, imperviousness, susceptibility)
hotspots = compute_terrain(box)

# 3. Fetch rainfall forecast (72h)
rainfall = fetch_forecast(box)

# 4. Compute hourly runoff discharge Q (m³/s)
hotspots_with_q = compute_runoff(hotspots, rainfall)

# 5. Pass to Person B's size_drains(hotspots_with_q)
```

---

## Output Shape (Example Hotspots)

Each `Hotspot` object adheres to [`hydropinpoint.contracts.Hotspot`](file:///C:/Users/ANJALI/Desktop/nxtwave/hydropinpoint/contracts.py):
- `id`: integer hotspot ID
- `lat, lon`: centroid coordinates (degrees WGS84)
- `catchment_area_km2`: drainage area in km²
- `depression_depth_m`: sink depression depth in metres
- `imperviousness`: fraction of built-up area (0.0 to 1.0)
- `runoff_coeff_C`: area-weighted runoff coefficient (0.0 to 1.0)
- `flow_path_slope_S`: raw flow-path slope in m/m (Note: B applies the slope floor floor in `hydraulics.py`)
- `susceptibility_score`: 0.0 to 1.0 (static relative vulnerability)
- `susceptibility_rank`: 1 to N (1 = most susceptible)
- `hourly_Q_m3s`: list of floats aligned with `rainfall.times` in m³/s
- `outside_rational_validity`: True if `catchment_area_km2 > MAX_RATIONAL_AREA_KM2` (1.0 km²)

---

## Known Caveats & Guardrails for Person B
1. **Slope Floor**: `compute_terrain` returns the raw flow path slope $S$ in `flow_path_slope_S`. Person B must apply `SLOPE_FLOOR_M_PER_M` (0.001) in `size_drains`.
2. **Offline Fallback**: When external DEM or rainfall APIs are blocked by sandbox isolation, fetchers return graceful fallback data and log clear notes without crashing.
3. **No Flood Prediction Claim**: As agreed in contracts and system architecture, this tool performs screening only; capacity of existing drains is unknown.
