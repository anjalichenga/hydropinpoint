# Validation: 5 September 2022 Bengaluru Flood Plausibility Check

**This is a plausibility check, not a flood prediction or capacity validation.**

HydroPinpoint checks whether the top-ranked hotspots (by susceptibility score, derived
from terrain and land cover) overlap with localities reported as flooded on 5 September 2022.
We compare against a random-cell baseline over 1,000 Monte Carlo trials.

## Reference flooded localities (5 September 2022)

The 5 September 2022 event overwhelmed low-lying depressions along major storm-water
corridors in East Bengaluru (especially Sarjapur Road, Outer Ring Road, and Bellandur catchment).

| Locality | Approx. Lat | Approx. Lon | Source URL |
|---|---|---|---|
| Rainbow Drive Layout | 12.9126 | 77.6974 | https://www.thehindu.com/news/cities/bangalore/bengaluru-floods-rainbow-drive-layout/article65853245.ece |
| Bellandur EcoSpace (ORR) | 12.9260 | 77.6833 | https://www.deccanherald.com/city/bengaluru-infrastructure/outer-ring-road-tech-parks-flooded-after-heavy-rain-1142278.html |
| Sunny Brooks Community | 12.9105 | 77.6890 | https://www.thehindu.com/news/cities/bangalore/sarjapur-road-inundated-in-bengaluru/article65851410.ece |
| Mahadevapura ORR | 12.9890 | 77.6980 | https://indianexpress.com/article/cities/bangalore/bengaluru-rain-live-updates-flooding-waterlogging-traffic-8131345/ |
| HSR Layout Sector 6 | 12.9110 | 77.6380 | https://timesofindia.indiatimes.com/city/bengaluru/bengaluru-rains-hsr-layout-submerged/articleshow/94002134.cms |
| Marathahalli Junction | 12.9560 | 77.7010 | https://www.thehindu.com/news/cities/bangalore/waterlogging-on-marathahalli-stretch/article65852102.ece |
| Varthur Kodi | 12.9580 | 77.7380 | https://indianexpress.com/article/cities/bangalore/varthur-lake-overflows-8132450/ |

## Methodology

- Archive rainfall: Open-Meteo ERA5, 5 Sept 2022, label `"HISTORICAL REPLAY"`.
- Hotspot detection: static terrain + WorldCover analysis via `compute_terrain`.
- Hit definition: a reference locality is considered a "hit" if its coordinates fall within 500 metres of a top-ranked hotspot centroid or inside its delineated catchment.
- Baseline comparison: 1,000 trials of randomly placed points within the bounding box to calculate the expected background hit-rate by pure chance.

## Caveats

- The DEM and WorldCover represent recent/2021 vintages; local structures may have altered since 2022.
- Open-Meteo ERA5 resolution is ~25 km; localized cloudburst peaks are smoothed.
- Reference localities are approximate centroid coordinates from press reports.
- Absence of a match does not imply model failure: street-level waterlogging can occur from blocked roadside drains, which is independent of terrain micro-catchment sink topology.
