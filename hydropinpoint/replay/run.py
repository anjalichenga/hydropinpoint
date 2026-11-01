"""replay/run.py – plausibility check against 5 September 2022 Bengaluru flood reports.

Owner: Person A.

Usage:
    python -m hydropinpoint.replay.run

What it does:
1. Fetches Open-Meteo ERA5 archive rainfall for 5 Sept 2022 (label: HISTORICAL REPLAY).
2. Calls compute_terrain + compute_runoff for the demo box using that archive rainfall.
3. Geocodes the reference flooded localities (from docs/validation.md) using either
   B's Nominatim tool (if available) or the throwaway script in scratch/.
4. Counts how many reference localities fall within a top-K hotspot catchment
   (hit-rate) and compares against a random-cell baseline (N_RANDOM_TRIALS trials).
5. Prints a table of results and hit-rate vs baseline.
6. All reference localities and their source URLs are listed in docs/validation.md.

Notes:
    - This is a PLAUSIBILITY CHECK, not a validation of the live forecast.
    - The reference localities are approximate; geocoding uncertainty is stated.
    - The demo box must be chosen to cover the geocoded localities, not from memory.
"""
from __future__ import annotations

# Implementation by Person A.


def main() -> None:
    raise NotImplementedError("replay.run not yet implemented – Person A")


if __name__ == "__main__":
    main()
