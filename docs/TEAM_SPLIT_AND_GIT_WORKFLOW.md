# HydroPinpoint: Team Split and Git Workflow

Two people, A and B. A owns rain to runoff (terrain and hydrology). B owns runoff to pipe, plus data tools, agent, app and deploy. The only thing both touch is `contracts.py`.

## 1. Ownership

| Area | A (terrain and hydrology) | B (hydraulics, tools, agent, app) |
| --- | --- | --- |
| Fetch | DEM, WorldCover, Open-Meteo forecast and archive | Overpass, Nominatim/Photon, OSRM, DataMeet wards, cache layer |
| Engine | `dem`, `landcover`, `rainfall`, `hydrology`, `scoring` | `hydraulics`, `pipeline.py` (the join) |
| Product | Replay run, hit-rate vs random baseline, `docs/validation.md` | Tool wrappers, LangGraph agent, validator, citation checker, Streamlit (4 pages), deploy, edge cases |
| Docs | Terrain, runoff and validation sections of README | Architecture diagram, agent and UI sections of README, deck skeleton |
| Explains to judges | Terrain, catchments, runoff, validation | Pipe sizing, agent graph, guardrails |

Shared and agreed by both: `contracts.py`, `config.py` structure (A edits the HYDROLOGY block, B edits the HYDRAULICS, AGENT and UI blocks), Makefile, CI, `docs/` plan files.

## 2. Repo layout

```
hydropinpoint/
  contracts.py            # SHARED typed models, both approve changes
  config.py               # every assumption, source standard in a comment
  fetch/
    dem.py landcover.py rainfall.py        # A
    osm.py geocode.py routing.py wards.py cache.py   # B
  engine/
    dem.py landcover.py rainfall.py hydrology.py scoring.py   # A
    hydraulics.py                                        # B
  pipeline.py             # B owns, calls A's compute_terrain / compute_runoff then B's size_drains
  replay/                 # A
  tools/                  # B: hotspots, scenario, facilities, wards, route, replay
  agent/                  # B: planner, executor, validator, reasoner, writer, citation_checker
  app/                    # B: Streamlit pages Live, Ask, Replay, Sources
tests/
  test_contracts.py       # shared
  test_a_*.py             # A
  test_b_*.py             # B
docs/
  validation.md           # A
  TEAM_SPLIT_AND_GIT_WORKFLOW.md
Makefile  .github/workflows/ci.yml  CODEOWNERS
```

## 3. The contract (`contracts.py`)

Write it together in about 30 minutes, merge to `main`, tag `sync-0-contract`. Pydantic models:

- `BoundingBox(west, south, east, north)`
- `RainfallSeries(points, hourly_mm_per_h, times, source, fetched_at, grid_values_identical)`
- `Hotspot(id, centroid, catchment_area_km2, depression_depth_m, imperviousness, runoff_coeff_C, flow_path_slope_S, susceptibility_rank, hourly_Q_m3s)`
- `DrainSizing(hotspot_id, hourly_required_D_m, slope_floor_applied, mapped_drain_size_m | None)`
- `EngineResult(hotspots, sizings, rainfall, dem_vintage, landcover_vintage, notes)`
- `ToolResult(value, source, fetched_at, cached: bool, error: str | None)`

Rules: units are in the field name or docstring (mm/h, km², m³/s, m). Every tool returns `ToolResult`, so the validator and citation checker work on all of them. After sync-0, any change to this file needs both approvals, enforced by CODEOWNERS.

Interfaces fixed at sync-0:

- A exposes `compute_terrain(box) -> list[Hotspot]` (static fields) and `compute_runoff(hotspots, rain: RainfallSeries) -> list[Hotspot]` (fills `hourly_Q_m3s`).
- B exposes `size_drains(hotspots) -> list[DrainSizing]` and `pipeline.run(box) -> EngineResult`.

## 4. No dummy data

The rules ban mock data. So:

- Unit tests only use pure-function cases with hand-calculated answers (for example, Manning pipe size for a known Q, S, n) and schema checks.
- Integration checks run on real fetched data at runtime. Any local sample outputs go in `.cache/` (git-ignored).
- Committing a cache of real timestamped responses is an open question for the organizers. Do not commit one until they answer.

## 5. Branching and commit rules

- `main` is always runnable. No direct pushes after sync-0.
- Branch names: `a/<topic>` and `b/<topic>`, for example `a/dem-fill`, `b/overpass-fetch`. Keep them short-lived (a day at most).
- Merge by pull request. The other person reviews every PR. That review is how each of you learns the other half, which the "every member can explain the code" rule needs.
- Use rebase-then-merge or merge commits, not squash, so the history shows the early, frequent commits the rules ask for.
- Commit small and often. Prefix: `a:`, `b:`, or `shared:`. Example: `a: fill depressions, report depth per sink`.
- Only `shared:` commits may touch `contracts.py`, Makefile or CI.
- Every PR must pass `make check` in CI before merge.

`make check` runs: lint, `pytest tests/`, `python -m hydropinpoint.check_contracts` (imports every module, calls each public interface on a tiny real window if the cache exists, validates return types against `contracts.py`), and `python -m hydropinpoint.pipeline --smoke` once A's first run exists.

## 6. Sync gates (compatibility checks)

At every gate, both people do the same routine:

1. Both merge their open PRs to `main`.
2. Both `git pull`, then run `make check` and the gate command below. Both must pass on their own machine.
3. Each person spends five minutes explaining their half to the other.
4. Tag: `git tag sync-N-name && git push --tags`.
5. If a check fails, the owner of the failing side fixes it. If the cause is the contract, change it together in a `shared:` PR first.

| Gate | When | What must be true | Gate command |
| --- | --- | --- | --- |
| sync-0 contract | before any branching | `contracts.py` merged, CI green, interfaces agreed | `pytest tests/test_contracts.py` |
| sync-1 go/no-go | about 90 min in | A: Bengaluru DEM and WorldCover read, fill and accumulation run, real depression depths print. B: Open-Meteo, Overpass, Nominatim, OSRM, DataMeet each answer or the fallback works, trial deploy loads | `python -m hydropinpoint.gonogo` prints every row of the go/no-go table |
| sync-2 first end-to-end | A's first rough real run | A returns real hotspots with hourly Q and slope. B's `size_drains` consumes them unchanged and `pipeline.run` returns a valid `EngineResult` | `python -m hydropinpoint.pipeline --smoke` |
| sync-3 engine done | end of phase 3 | Top hotspots print with Q, required diameter, source and timestamp. Killing one source degrades, not crashes | `python -m hydropinpoint.pipeline --top 3` |
| sync-4 agent | end of phase 4 | The three example questions are answered with every number matched by the citation checker | `python -m hydropinpoint.agent.demo_questions` |
| sync-5 app | end of phase 5 | Full demo runs locally on live data, banner appears when a source is killed | `streamlit run app/main.py` plus the demo script |
| sync-6 replay | end of phase 6 | Replay page runs, hit-rate vs baseline reported, every reference locality has a source URL | `python -m hydropinpoint.replay.run` |
| sync-7 freeze | before deploy | Feature freeze. Live URL works. Each edge case (dry day, source down, empty box) shows a message | `docs/edge_cases.md` checklist |
| sync-8 submission | last | Submission checklist complete, repo public, README and deck done | checklist in the build plan |

## 7. Order of work between syncs

- Both: sync-0 first.
- B starts with the data layer (`cache.py`, Overpass, Nominatim, OSRM, wards) and `hydraulics.py`. Neither needs A.
- A starts with the DEM fetch, fill, flow accumulation and catchments. If A is stuck at go/no-go, B pairs on the blocker before returning to their own track.
- A ships a rough real end-to-end run as early as possible. B should not wait for polished scoring.
- B ships the Nominatim tool before A needs it for the replay. Until then A uses a throwaway script in `scratch/` (git-ignored).
- Feature freeze comes before phase 7.
