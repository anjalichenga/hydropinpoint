# Edge-case checklist

- Dry day: Live page states that runoff-driven sizes are zero.
- Source down: fetchers return cached real data or a visible degraded-mode error.
- Empty box/no hotspots: tables and maps render without indexing assumptions.
- Rate limit: Nominatim and OSRM are limited to about one request per second.
- Missing mapped drain: capacity is shown as unknown; no surcharge ratio is claimed.
- Scenario: labelled SCENARIO and never combined with LIVE or HISTORICAL REPLAY values.