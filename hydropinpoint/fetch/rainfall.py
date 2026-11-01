"""fetch/rainfall.py – Open-Meteo forecast and archive fetcher.

Owner: Person A.

Public API:
    fetch_forecast(box: BoundingBox) -> RainfallSeries
        Hourly 72-h forecast for the nine grid points around the box centre.
        Prints the nine values first. If identical, returns one RainCell and
        sets grid_values_identical=True. Label: "LIVE".

    fetch_archive(box: BoundingBox, date: str) -> RainfallSeries
        Open-Meteo ERA5 (or best available model) archive for *date* (YYYY-MM-DD).
        Label: "HISTORICAL REPLAY".
        Note: resolution is approximately 9–25 km; the model name is recorded in
        the source field so it can be shown to the user.

Notes:
    - No API key required for Open-Meteo.
    - Retries 3 times with back-off.
    - On failure, returns a RainfallSeries with error note in the source field
      and all mm_per_h values as 0.0, or raises if the caller cannot continue.
"""
from __future__ import annotations

from hydropinpoint.contracts import BoundingBox, RainfallSeries


def fetch_forecast(box: BoundingBox) -> RainfallSeries:
    """Fetch 72-h hourly rainfall forecast for *box* from Open-Meteo."""
    raise NotImplementedError("fetch_forecast not yet implemented – Person A")


def fetch_archive(box: BoundingBox, date: str) -> RainfallSeries:
    """Fetch Open-Meteo archive rainfall for *box* on *date* (YYYY-MM-DD)."""
    raise NotImplementedError("fetch_archive not yet implemented – Person A")
