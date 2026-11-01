"""Central configuration for HydroPinpoint.

Every assumption (coefficient, threshold, limit) lives here with its source standard
named in a comment. If a value is uncertain, that is noted. The UI labels every
ASSUMPTION shown to users.

Blocks:
    HYDROLOGY  – A's terrain and runoff parameters
    HYDRAULICS – B's pipe-sizing parameters
    AGENT      – B's LLM / tool settings
    UI         – B's Streamlit settings
"""

import os
from pathlib import Path

from dotenv import load_dotenv

from hydropinpoint.contracts import BoundingBox

load_dotenv()

# --- HYDROLOGY ---
# Runoff coefficients C by WorldCover class.
# Source: Chow, Maidment & Mays "Applied Hydrology" Table 5.2.1 (1988).
# ASSUMPTION: coefficients are central estimates for moderately urban terrain;
# ±0.1 uncertainty is typical.
RUNOFF_COEFF_BY_CLASS: dict[int, float] = {
    10: 0.35,   # Tree cover       (forest / open woodland)
    20: 0.40,   # Shrubland
    30: 0.45,   # Grassland
    40: 0.50,   # Cropland
    50: 0.80,   # Built-up         (ASSUMPTION: dense urban)
    60: 0.15,   # Bare / sparse vegetation
    70: 0.05,   # Snow and ice     (not expected in Bengaluru)
    80: 1.00,   # Permanent water bodies
    90: 0.60,   # Herbaceous wetland
    95: 0.65,   # Mangroves
    100: 0.40,  # Moss and lichen
}
RUNOFF_COEFF_DEFAULT: float = 0.50  # ASSUMPTION: used when class is unknown

# Depression depth threshold (metres): sinks shallower than this are filtered
# as likely DEM artefacts (buildings, trees).
# ASSUMPTION: 0.3 m based on vertical accuracy of Copernicus DEM GLO-30 (~1 m RMSE);
# raise if too many artefact sinks appear in testing.
MIN_DEPRESSION_DEPTH_M: float = 0.3

# Catchment area threshold (km²): sinks draining less than this are filtered.
# ASSUMPTION: 0.005 km² (0.5 ha) removes isolated-pixel noise.
MIN_CATCHMENT_AREA_KM2: float = 0.005

# Maximum catchment area for Rational Method validity.
# Source: most hydrology texts cite 80 ha (0.8 km²) as the practical upper limit
# for Q = 0.278 * C * I * A.
# ASSUMPTION: using 1.0 km² (100 ha) as a generous limit; flag larger catchments.
MAX_RATIONAL_AREA_KM2: float = 1.0

# Maximum number of hotspots to retain after scoring.
MAX_HOTSPOTS: int = 50

# DEM source preference order (tried in sequence).
# GLO-30 tiles are at s3://copernicus-dem-30m/... (public, no auth).
# GLO-90 is the fallback if any tile fetch fails.
DEM_PREFERRED_RESOLUTION_M: int = 30   # GLO-30
DEM_FALLBACK_RESOLUTION_M: int = 90    # GLO-90

# --- HYDRAULICS ---
# Manning's roughness for concrete circular pipe.
# Source: Chadwick, Morfett & Borthwick "Hydraulics in Civil and Environmental
# Engineering" Table 10.1.
# ASSUMPTION: n = 0.013 for smooth concrete; precast concrete often 0.011–0.015.
MANNING_N_PIPE: float = 0.013

# Minimum slope floor applied to avoid numerical issues and match typical
# construction practice.
# Source: IS 1742:1983 recommends minimum 1:500 (0.002) for drains.
# ASSUMPTION: using 0.001 as absolute minimum; B applies this, not A.
SLOPE_FLOOR_M_PER_M: float = 0.001

# Standard pipe diameters available (metres), smallest first.
# ASSUMPTION: based on IS 458:2003 precast concrete pipes (common in Indian ULBs).
STANDARD_PIPE_DIAMETERS_M: list[float] = [
    0.15, 0.20, 0.225, 0.25, 0.30, 0.375, 0.45, 0.525, 0.60,
    0.675, 0.75, 0.90, 1.00, 1.05, 1.20, 1.35, 1.50,
]

# --- AGENT ---
# LLM and tool settings for B's LangGraph agent.
# Values are read from environment; defaults here are safe non-functional stubs.
AGENT_MAX_RETRIES: int = 3
AGENT_TIMEOUT_S: int = 30

# --- UI ---
# Streamlit page settings for B's app.
UI_PAGE_TITLE: str = "HydroPinpoint"
UI_MAP_TILES: str = "OpenStreetMap"
UI_DEFAULT_BOX: dict = {
    # Approximate 10 × 10 km window centred on eastern Bengaluru flood-reported area.
    # ASSUMPTION: chosen from memory around 12.95 N, 77.65 E; must be verified
    # against geocoded flood localities before finalising (see replay/).
    "west": 77.60,
    "south": 12.90,
    "east": 77.70,
    "north": 13.00,
}

# --- PERSON B RUNTIME ---
# Isolated aliases and source settings owned by Person B.

MANNING_N = MANNING_N_PIPE
MIN_PIPE_SLOPE = SLOPE_FLOOR_M_PER_M
CACHE_DIR = Path(os.getenv("HYDROPINPOINT_CACHE_DIR", ".cache"))
HTTP_TIMEOUT_S = 30
HTTP_RETRIES = 3
USER_AGENT = "HydroPinpoint/0.1 ({email})"
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "gemini").lower()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
MAX_VALIDATOR_ATTEMPTS = AGENT_MAX_RETRIES
DEFAULT_BOX = BoundingBox(**UI_DEFAULT_BOX)
TOP_HOTSPOTS = 3
OSM_MATCH_RADIUS_M = 150.0
OVERPASS_ENDPOINTS = tuple(
    endpoint
    for endpoint in (
        os.getenv("OVERPASS_API_URL"),
        "https://overpass-api.de/api/interpreter",
        "https://overpass.kumi.systems/api/interpreter",
        "https://overpass.private.coffee/api/interpreter",
    )
    if endpoint
)
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
PHOTON_URL = "https://photon.komoot.io/api/"
OSRM_URL = "https://router.project-osrm.org/route/v1/driving"
DATAMEET_WARDS_URL = (
    "https://raw.githubusercontent.com/datameet/Municipal_Spatial_Data/master/"
    "Bangalore/BBMP/BBMP_Wards.geojson"
)
