# Validation: 5 September 2022 Bengaluru Flood Plausibility Check

**This is a plausibility check, not a flood prediction or capacity validation.**

HydroPinpoint checks whether the top-ranked hotspots (by susceptibility score, derived
from terrain and land cover) overlap with localities reported as flooded on 5 Sept 2022.
We compare against a random-cell baseline over N trials.

## Reference flooded localities

Localities and source URLs will be added here by Person A once geocoded.

| Locality | Approx. lat | Approx. lon | Source URL |
|----------|------------|------------|------------|
| (to be filled) | | | |

## Methodology

- Archive rainfall: Open-Meteo ERA5, 5 Sept 2022, label "HISTORICAL REPLAY".
- Hotspot detection: same pipeline as the live tool (DEM, WorldCover, Rational Method).
- A locality "matches" a hotspot if its geocoded point falls within the catchment polygon.
- Baseline: N_RANDOM_TRIALS random placements of the same number of points within the
  bounding box; hit-rate is the fraction that fall in a top-K catchment by chance.

## Caveats

- The DEM and WorldCover are 2021/2020 vintages; land cover may have changed since 2022.
- Open-Meteo ERA5 resolution is approximately 9–25 km; local intensity variation is lost.
- Reported localities are approximate and may refer to roads or areas, not point locations.
- Absence of a match does not mean the tool is wrong: the locality may be outside the box,
  or the flood may have been caused by overland flow not captured by the Rational Method.
