# HydroPinpoint

HydroPinpoint is an explainable urban flood-screening prototype for Bengaluru. It
combines open terrain, land-cover and rainfall data to identify low-lying
micro-catchments, estimate runoff and required drain diameter, and answer questions
through a source-aware LangGraph and Gemini assistant.

> **Live demo:** [Add the deployed Streamlit URL here](https://YOUR-APP-NAME.streamlit.app)

> **Safety note:** HydroPinpoint is a planning and screening aid. It is not an
> operational flood forecast, emergency-warning system or drainage-capacity model.

## Hackathon problem

Rapidly growing cities often lack a single, accessible view of terrain depressions,
rainfall exposure and drainage requirements. HydroPinpoint turns public datasets into
an interactive screening map that helps users quickly investigate likely hotspots and
understand why each location was ranked.

## What it does

- Screens roughly 38 x 39 km of the Bengaluru metropolitan area by default.
- Detects terrain depressions and delineates their micro-catchments.
- Combines Copernicus DEM and ESA WorldCover data with live Open-Meteo rainfall.
- Estimates runoff using the Rational Method and sizes circular drains with Manning's
  equation.
- Shows ranked hotspots on a key-free OpenStreetMap basemap.
- Optionally compares mapped OSM drain width or diameter when Overpass is available.
- Provides a LangGraph-based Gemini assistant with numeric citation checking.
- Replays the 5 September 2022 Bengaluru flood event for historical plausibility.

## Architecture

```text
Copernicus DEM + ESA WorldCover + Open-Meteo rainfall
                         |
                         v
        terrain sinks -> catchments -> runoff estimates
                         |
                         v
              Manning drain-size screening
                         |
          +--------------+---------------+
          |                              |
          v                              v
  Streamlit map and tables     LangGraph + Gemini agent
                                      |
                                      v
                         numeric citation guardrail
```

## Historical replay result

The current 5 September 2022 replay matches 3 of 7 press-reported flood localities
within 750 m:

| Metric | Result |
|---|---:|
| Model hit rate | 42.9% (3/7) |
| Random baseline | 8.1% |
| Signal-to-random ratio | 5.26x |

This is an early plausibility result, not proof of predictive accuracy. See
[`docs/validation.md`](docs/validation.md) for methodology and caveats.

## Data sources

| Data | Source | Purpose |
|---|---|---|
| Elevation | Copernicus DEM GLO-30/GLO-90 | Depression and catchment detection |
| Land cover | ESA WorldCover 2020 | Imperviousness and runoff coefficients |
| Live rainfall | Open-Meteo | Current runoff screening |
| Historical rainfall | Open-Meteo ERA5 archive | September 2022 replay |
| Drainage and facilities | OpenStreetMap/Overpass | Optional mapped context |
| Ward boundaries | DataMeet | Administrative context |
| Routes | OSRM | Shelter-to-hospital route tool |
| Basemap | OpenStreetMap | Interactive map tiles; no key required |

## Local deployment

### Prerequisites

- Python 3.11 recommended
- Git
- An internet connection for the public datasets
- A Gemini API key for AI answers; the rest of the application works without it

The first terrain run downloads and caches large raster tiles, so it can take several
minutes and requires free disk space.

### Windows PowerShell

```powershell
git clone https://github.com/anjalichenga/hydropinpoint.git
cd hydropinpoint

py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

Copy-Item .env.example .env
```

Open `.env`, add the configuration described below, and start the app:

```powershell
python -m streamlit run app/main.py
```

### macOS or Linux

```bash
git clone https://github.com/anjalichenga/hydropinpoint.git
cd hydropinpoint

python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

cp .env.example .env
python -m streamlit run app/main.py
```

The application will normally open at `http://localhost:8501`.

## Environment configuration

Create `.env` from `.env.example`. Never commit the completed `.env` file.

```env
CONTACT_EMAIL=your-real-email@example.com

LLM_PROVIDER=gemini
GEMINI_API_KEY=your-gemini-api-key
GEMINI_MODEL=gemini-3.5-flash-lite
GEMINI_FALLBACK_MODEL=gemini-2.5-flash-lite

HYDROPINPOINT_CACHE_DIR=.cache

HYDROPINPOINT_BOX_WEST=77.45
HYDROPINPOINT_BOX_SOUTH=12.80
HYDROPINPOINT_BOX_EAST=77.80
HYDROPINPOINT_BOX_NORTH=13.15

# Optional private or self-hosted Overpass endpoint
OVERPASS_API_URL=
```

Create a Gemini key at [Google AI Studio](https://aistudio.google.com/app/apikey).
OpenStreetMap tiles do not need an API key. Public Overpass instances can be rate
limited; when they are unavailable, the app continues with mapped drain capacity
labelled as unknown.

## Run checks

Run all commands inside the virtual environment:

```bash
python -m ruff check hydropinpoint tests app
python -m pytest -m "not network" tests
python -m hydropinpoint.check_contracts
```

Optional network smoke test:

```bash
python -m hydropinpoint.pipeline --smoke
```

Historical replay:

```bash
python -m hydropinpoint.replay.run
```

## Docker deployment

```bash
docker build -t hydropinpoint .
docker run --env-file .env -p 8501:8501 hydropinpoint
```

Open `http://localhost:8501`.

## Streamlit Community Cloud

1. Push the project to GitHub.
2. Open [Streamlit Community Cloud](https://share.streamlit.io).
3. Select the repository, the `main` branch and `app/main.py` as the entry point.
4. Choose Python 3.11.
5. Copy the `.env` values into **Advanced settings -> Secrets** using TOML syntax.
6. Deploy, then replace the live-demo placeholder at the top of this README.

Example Streamlit secrets:

```toml
CONTACT_EMAIL = "your-real-email@example.com"
GEMINI_API_KEY = "your-gemini-api-key"
GEMINI_MODEL = "gemini-3.5-flash-lite"
GEMINI_FALLBACK_MODEL = "gemini-2.5-flash-lite"
```

## Project structure

```text
app/main.py                    Streamlit Cloud entry point
hydropinpoint/app/             User interface
hydropinpoint/agent/           LangGraph workflow and citation guardrail
hydropinpoint/engine/          Terrain, hydrology, scoring and hydraulics
hydropinpoint/fetch/           Public-data fetchers and real-response cache
hydropinpoint/tools/           Agent-facing tools
hydropinpoint/replay/          Historical plausibility replay
tests/                         Offline unit and contract tests
docs/                          Validation, assumptions and team handoffs
```

## Known limitations

- DEM buildings and vegetation can create false terrain depressions.
- Rainfall grids are too coarse to represent every street-level cloudburst.
- OSM frequently lacks drain width or diameter, so existing capacity may be unknown.
- The Rational Method is a screening approximation and has catchment-size limits.
- Public endpoints can be slow or rate limited; successful real responses are cached.
- The historical dataset currently contains only seven reported localities from one
  event and requires broader validation before operational use.

## Team ownership

| Area | Responsibility |
|---|---|
| Terrain, hydrology and historical validation | Person A |
| Hydraulics, tools, agent, interface and deployment | Person B |

See `docs/` for the validation notes, assumptions and implementation handoffs.
