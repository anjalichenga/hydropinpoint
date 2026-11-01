# HydroPinpoint

A flood-hotspot screening tool for the wider Bengaluru metropolitan area.

HydroPinpoint finds low-lying micro-catchments from an open elevation model, estimates
the runoff each would receive from the live rainfall forecast, and estimates the drain
size each would need. An agent answers questions about it.

## Limitations (what this tool is NOT)

- **Not a flood predictor.** Results are a screening / plausibility signal only.
- **No surcharge or capacity ratio.** Existing drain capacity is not openly available;
  no claim is made about whether a drain will overflow.
- **Rational Method validity.** Q is computed only for catchments below the configured
  maximum area; larger catchments are flagged, not silently calculated.
- **DEM artefacts.** The elevation model includes buildings and trees; small sinks may
  be artefacts filtered by configured depth and area thresholds.
- **Rainfall resolution.** Open-Meteo grid spacing is 9–25 km depending on the model;
  all hotspots in the same grid cell receive the same intensity.
- **All assumptions** (runoff coefficients, thresholds) are labelled ASSUMPTION in the
  UI and their source standards are named in `hydropinpoint/config.py`.

## Quickstart

```bash
cp .env.example .env          # fill in CONTACT_EMAIL (for Nominatim)
pip install -r requirements.txt
make check                    # lint + tests (no network)
python -m hydropinpoint.pipeline --smoke   # needs network
streamlit run app/main.py
```

## Team

| Person | Area |
|--------|------|
| A | Terrain, hydrology (DEM → runoff) |
| B | Hydraulics, tools, agent, Streamlit app, deploy |

See `docs/TEAM_SPLIT_AND_GIT_WORKFLOW.md` for the full split and git protocol.

## Architecture

See `docs/` for the build plan, validation results, and handoff notes between A and B.
