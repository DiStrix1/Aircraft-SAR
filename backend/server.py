"""
Aircraft SAR — FastAPI backend
================================
Serves the React frontend's API endpoints:
  /api/aircraft        — available aircraft types
  /api/presets         — scenario presets
  /api/simulate        — run Monte Carlo simulation
  /api/weather         — fetch live/historical wind profile
  /api/search-pattern  — generate IAMSAR search pattern waypoints
  /api/sensitivity     — run sensitivity analysis
"""

from __future__ import annotations

import logging
import os
import random
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any

import numpy as np
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from calculations import (
    AIRCRAFT_DATA,
    haversine_distance,
    calculate_glide_distance,
    project_position,
)
from probability import (
    monte_carlo_simulation,
    generate_probability_zones,
    scenario_analysis,
)
from weather_data import (
    AF447_WIND_PROFILE,
    GW9525_WIND_PROFILE,
    QZ8501_WIND_PROFILE,
    get_wind_profile,
)
from search_patterns import (
    recommend_search_pattern,
    expanding_square,
    sector_search,
    parallel_track_search,
    creeping_line_ahead,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = FastAPI(title="Aircraft SAR API", version="3.0")

# CORS — restrict to configured origins in production, allow all in dev.
_ALLOWED_ORIGINS = os.environ.get("ALLOWED_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=_ALLOWED_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------
class AircraftType(BaseModel):
    id: str
    name: str
    glide_ratio: float
    cruise_speed: float
    category: str = ""
    max_altitude_ft: Optional[float] = None
    max_range_km: Optional[float] = None


class Preset(BaseModel):
    id: str
    name: str
    aircraft_type: str  # aircraft id
    latitude: float
    longitude: float
    heading: float
    airspeed: float
    altitude: float
    time_since_contact: float
    wind_speed: float
    wind_direction: float
    actual_lat: Optional[float] = None
    actual_lon: Optional[float] = None


class SimulateRequest(BaseModel):
    aircraft_type: str  # aircraft id
    latitude: float
    longitude: float
    heading: float
    airspeed: float
    altitude: float
    time_since_contact: float
    wind_speed: float
    wind_direction: float
    iterations: int = 3000
    heading_spread: float = 15.0
    scatter_min: float = 0.0
    scatter_max: float = 0.0
    descent_rate_override: float = 0
    weight_glide: float = 50
    weight_spiral: float = 20
    weight_dive: float = 20
    weight_breakup: float = 10
    weight_ditching: float = 0
    preset_id: Optional[str] = None


class ZoneData(BaseModel):
    points: List[List[float]]
    percentage: float


class AccuracyData(BaseModel):
    centroid_error_km: float
    within_50km: bool
    within_50km_pct: float


class SimulationResult(BaseModel):
    centroid: Dict[str, float]
    zones: Dict[str, ZoneData]
    impact_points: List[List[float]]
    glide_range_km: float
    search_area_km2: float
    classification: str
    severity: str
    accuracy: Optional[AccuracyData] = None
    recommended_pattern: str = ""


class SearchPatternResult(BaseModel):
    pattern: str
    waypoints: List[List[float]]
    center: List[float]


class WeatherLayer(BaseModel):
    altitude_ft: float
    wind_speed_kts: float
    wind_direction_deg: float


class WeatherResult(BaseModel):
    source: str
    valid_time: str
    layers: List[WeatherLayer]


class SensitivityEntry(BaseModel):
    parameter: str
    delta: float
    centroid_shift_km: float
    mean_radius_change_pct: float


class SensitivityRequest(BaseModel):
    aircraft_type: str
    latitude: float
    longitude: float
    heading: float
    airspeed: float
    altitude: float
    time_since_contact: float
    wind_speed: float
    wind_direction: float
    iterations: int = 300


# ---------------------------------------------------------------------------
# Aircraft ID ↔ name mapping
# ---------------------------------------------------------------------------
def _make_id(name: str) -> str:
    return name.lower().replace(" ", "_").replace("-", "_")


AIRCRAFT_ID_TO_NAME = {_make_id(name): name for name in AIRCRAFT_DATA}
AIRCRAFT_NAME_TO_ID = {name: _make_id(name) for name in AIRCRAFT_DATA}

# Load raw specs for extra fields (category, max_altitude_ft, max_range_km)
import json as _json
import os as _os
_SPECS_PATH = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "aircraft_specs.json")
with open(_SPECS_PATH) as _f:
    _RAW_SPECS = _json.load(_f)


# ---------------------------------------------------------------------------
# Presets
# ---------------------------------------------------------------------------
PRESETS: List[Preset] = [
    Preset(
        id="af447",
        name="Air France 447 (2009)",
        aircraft_type=AIRCRAFT_NAME_TO_ID.get("Airbus A330-300", "airbus_a330_300"),
        latitude=2.98, longitude=-30.59,
        heading=0, airspeed=460,
        altitude=35000, time_since_contact=4,
        wind_speed=40, wind_direction=270,
        actual_lat=3.04, actual_lon=-30.83,
    ),
    Preset(
        id="gw9525",
        name="Germanwings 9525 (2015)",
        aircraft_type=AIRCRAFT_NAME_TO_ID.get("Airbus A320-200", "airbus_a320_200"),
        latitude=44.15, longitude=7.10,
        heading=270, airspeed=350,
        altitude=38000, time_since_contact=8,
        wind_speed=20, wind_direction=330,
        actual_lat=44.28, actual_lon=6.44,
    ),
    Preset(
        id="ms804",
        name="EgyptAir 804 (2016)",
        aircraft_type=AIRCRAFT_NAME_TO_ID.get("Airbus A320-200", "airbus_a320_200"),
        latitude=33.68, longitude=28.79,
        heading=140, airspeed=440,
        altitude=37000, time_since_contact=2,
        wind_speed=15, wind_direction=290,
        actual_lat=33.68, actual_lon=29.25,
    ),
    Preset(
        id="qz8501",
        name="AirAsia QZ8501 (2014)",
        aircraft_type=AIRCRAFT_NAME_TO_ID.get("Airbus A320-200", "airbus_a320_200"),
        latitude=-3.37, longitude=109.69,
        heading=185, airspeed=430,
        altitude=32000, time_since_contact=3,
        wind_speed=25, wind_direction=270,
        actual_lat=-3.62, actual_lon=109.71,
    ),
    Preset(
        id="cessna_glide",
        name="Cessna 172S — Engine-Out Glide",
        aircraft_type=AIRCRAFT_NAME_TO_ID.get("Cessna 172S", "cessna_172s"),
        latitude=34.05, longitude=-118.25,
        heading=90, airspeed=110,
        altitude=8000, time_since_contact=10,
        wind_speed=15, wind_direction=240,
    ),
]

PRESET_SCENARIO_WEIGHTS = {
    "af447":       {"best_glide": 0.00, "spiral": 0.10, "dive": 0.80, "breakup": 0.10, "ditching": 0.00},
    "gw9525":      {"best_glide": 0.00, "spiral": 0.05, "dive": 0.90, "breakup": 0.05, "ditching": 0.00},
    "ms804":       {"best_glide": 0.10, "spiral": 0.30, "dive": 0.40, "breakup": 0.20, "ditching": 0.00},
    "qz8501":      {"best_glide": 0.00, "spiral": 0.70, "dive": 0.20, "breakup": 0.10, "ditching": 0.00},
    "cessna_glide": {"best_glide": 0.75, "spiral": 0.10, "dive": 0.05, "breakup": 0.00, "ditching": 0.10},
}

PRESET_OVERRIDES = {
    "af447":  {"heading_spread_deg": 180, "scatter_min_km": 2.0, "scatter_max_km": 8.0},
    "gw9525": {"heading_spread_deg": 15,  "scatter_min_km": 0.0, "scatter_max_km": 0.0},
    "ms804":  {"heading_spread_deg": 90,  "scatter_min_km": 1.0, "scatter_max_km": 4.0},
    "qz8501": {"heading_spread_deg": 120, "scatter_min_km": 1.0, "scatter_max_km": 3.0},
    "cessna_glide": {"heading_spread_deg": 30, "scatter_min_km": 0.0, "scatter_max_km": 0.0},
}

# Preset wind profiles (real/reconstructed data)
PRESET_WIND_PROFILES = {
    "af447":  AF447_WIND_PROFILE,
    "gw9525": GW9525_WIND_PROFILE,
    "qz8501": QZ8501_WIND_PROFILE,
}


# ---------------------------------------------------------------------------
# Convex hull helper
# ---------------------------------------------------------------------------
def _convex_hull(points):
    if len(points) <= 2:
        return list(points)
    pts = sorted(set(map(tuple, points)), key=lambda p: (p[1], p[0]))

    def cross(o, a, b):
        return (a[1] - o[1]) * (b[0] - o[0]) - (a[0] - o[0]) * (b[1] - o[1])

    lower = []
    for p in pts:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)
    upper = []
    for p in reversed(pts):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)
    hull = lower[:-1] + upper[:-1]
    if hull and hull[0] != hull[-1]:
        hull.append(hull[0])
    return hull


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.get("/api/aircraft", response_model=List[AircraftType])
def get_aircraft():
    result = []
    for name, data in AIRCRAFT_DATA.items():
        raw = _RAW_SPECS.get(name, {})
        result.append(AircraftType(
            id=_make_id(name),
            name=name,
            glide_ratio=data["glide_ratio"],
            cruise_speed=data["cruise_speed"],
            category=raw.get("category", ""),
            max_altitude_ft=raw.get("max_altitude_ft"),
            max_range_km=raw.get("max_range_km"),
        ))
    return result


@app.get("/api/presets", response_model=List[Preset])
def get_presets():
    return PRESETS


@app.post("/api/simulate", response_model=SimulationResult)
def simulate(req: SimulateRequest):
    # Resolve aircraft name from id
    aircraft_name = AIRCRAFT_ID_TO_NAME.get(req.aircraft_type)
    if not aircraft_name:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown aircraft id '{req.aircraft_type}'. "
                   f"Available: {list(AIRCRAFT_ID_TO_NAME.keys())}",
        )

    ac = AIRCRAFT_DATA[aircraft_name]

    # Build scenario weights from frontend slider percentages
    total_w = req.weight_glide + req.weight_spiral + req.weight_dive + req.weight_breakup + req.weight_ditching
    if total_w <= 0:
        total_w = 100.0
    scenario_weights = {
        "best_glide": req.weight_glide / total_w,
        "spiral":     req.weight_spiral / total_w,
        "dive":       req.weight_dive / total_w,
        "breakup":    req.weight_breakup / total_w,
        "ditching":   req.weight_ditching / total_w,
    }

    # Use preset-specific weights and overrides if a preset is selected
    heading_spread = req.heading_spread
    scatter_min = req.scatter_min
    scatter_max = req.scatter_max
    wind_profile = None
    run_seed: Optional[int] = None  # None = random for custom runs

    if req.preset_id:
        if req.preset_id in PRESET_SCENARIO_WEIGHTS:
            scenario_weights = PRESET_SCENARIO_WEIGHTS[req.preset_id]
        overrides = PRESET_OVERRIDES.get(req.preset_id, {})
        heading_spread = overrides.get("heading_spread_deg", heading_spread)
        scatter_min = overrides.get("scatter_min_km", scatter_min)
        scatter_max = overrides.get("scatter_max_km", scatter_max)
        wind_profile = PRESET_WIND_PROFILES.get(req.preset_id)
        run_seed = 42  # reproducible preset runs

    descent_override = req.descent_rate_override if req.descent_rate_override > 0 else None

    # Run Monte Carlo (seed only for presets)
    points = monte_carlo_simulation(
        iterations=req.iterations,
        last_lat=req.latitude,
        last_lon=req.longitude,
        heading_deg=req.heading,
        airspeed_kts=req.airspeed,
        altitude_ft=req.altitude,
        aircraft_type=aircraft_name,
        time_since_contact_min=req.time_since_contact,
        wind_speed_kts=req.wind_speed,
        wind_direction_deg=req.wind_direction,
        scenario_weights=scenario_weights,
        descent_rate_override=descent_override,
        heading_spread_deg=heading_spread,
        scatter_min_km=scatter_min,
        scatter_max_km=scatter_max,
        wind_profile=wind_profile,
        seed=run_seed,
    )

    # Centroid
    lats = np.array([p[0] for p in points])
    lons = np.array([p[1] for p in points])
    centroid = (float(lats.mean()), float(lons.mean()))

    # Zones
    zones = generate_probability_zones(points, centroid)
    total_pts = len(points)

    zone_data = {}
    for zone_name in ("HIGH", "MEDIUM", "LOW"):
        zone_pts = zones.get(zone_name, [])
        pct = round(len(zone_pts) / total_pts * 100) if total_pts > 0 else 0
        if len(zone_pts) >= 3:
            hull = _convex_hull(zone_pts)
        else:
            hull = zone_pts
        zone_data[zone_name.lower()] = ZoneData(
            points=[list(p) for p in hull],
            percentage=pct,
        )

    # Glide range
    glide_km = calculate_glide_distance(
        req.altitude, ac["glide_ratio"], req.airspeed,
        ac["best_glide_speed"], req.wind_speed, req.wind_direction, req.heading,
    )

    # Search area (area of the LOW zone convex hull, approximated)
    search_area = round(3.14159 * glide_km * glide_km * 0.25)

    # Recommended search pattern
    recommended = recommend_search_pattern(search_area, "HIGH", 1)

    # Scenario analysis
    scenario = scenario_analysis(req.altitude, req.airspeed, req.time_since_contact, req.wind_speed)

    # Accuracy (only for presets with known crash sites)
    accuracy = None
    if req.preset_id:
        preset = next((p for p in PRESETS if p.id == req.preset_id), None)
        if preset and preset.actual_lat is not None and preset.actual_lon is not None:
            centroid_err = haversine_distance(
                centroid[0], centroid[1],
                preset.actual_lat, preset.actual_lon,
            )
            dists = [
                haversine_distance(p[0], p[1], preset.actual_lat, preset.actual_lon)
                for p in points
            ]
            within_50_pct = sum(1 for d in dists if d <= 50) / len(dists) * 100
            accuracy = AccuracyData(
                centroid_error_km=round(centroid_err, 1),
                within_50km=within_50_pct >= 15,
                within_50km_pct=round(within_50_pct, 1),
            )

    # Subsample impact points for the frontend (300 max for performance)
    impact_sample = points if len(points) <= 300 else random.sample(points, 300)

    return SimulationResult(
        centroid={"lat": centroid[0], "lon": centroid[1]},
        zones=zone_data,
        impact_points=[list(p) for p in impact_sample],
        glide_range_km=round(glide_km, 1),
        search_area_km2=search_area,
        classification=scenario["scenario"],
        severity=scenario["severity"],
        accuracy=accuracy,
        recommended_pattern=recommended,
    )


@app.get("/api/weather", response_model=WeatherResult)
def get_weather(
    lat: float = Query(..., ge=-90, le=90, description="Latitude"),
    lon: float = Query(..., ge=-180, le=180, description="Longitude"),
    datetime_utc: str = Query(
        default=None,
        description="ISO 8601 datetime string (UTC). Defaults to now.",
    ),
    surface_wind_speed: float = Query(default=0.0, description="Surface wind speed (kts) for fallback"),
    surface_wind_dir: float = Query(default=0.0, description="Surface wind direction (°) for fallback"),
):
    """Fetch a wind profile from Open-Meteo for a given location and time.

    Falls back to the atmospheric model profile when Open-Meteo is unreachable.
    """
    if datetime_utc:
        try:
            dt = datetime.fromisoformat(datetime_utc.replace("Z", "+00:00"))
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid datetime_utc: '{datetime_utc}'")
    else:
        dt = datetime.now(timezone.utc)

    profile = get_wind_profile(
        lat, lon, dt,
        surface_wind_speed_kts=surface_wind_speed,
        surface_wind_dir_deg=surface_wind_dir,
    )

    if profile is None:
        raise HTTPException(
            status_code=503,
            detail="Weather data unavailable. Provide surface_wind_speed and surface_wind_dir for fallback.",
        )

    return WeatherResult(
        source=profile.source,
        valid_time=profile.valid_time,
        layers=[
            WeatherLayer(
                altitude_ft=l.altitude_ft,
                wind_speed_kts=round(l.wind_speed_kts, 1),
                wind_direction_deg=round(l.wind_direction_deg, 1),
            )
            for l in profile.layers
        ],
    )


@app.get("/api/search-pattern", response_model=SearchPatternResult)
def get_search_pattern(
    centroid_lat: float = Query(..., description="Centroid latitude"),
    centroid_lon: float = Query(..., description="Centroid longitude"),
    area_km2: float = Query(..., gt=0, description="Search area in km²"),
    heading: float = Query(default=0.0, description="Primary search heading (°)"),
    pattern: Optional[str] = Query(default=None, description="Pattern override (optional)"),
    resources: int = Query(default=1, ge=1, description="Number of search assets"),
):
    """Return IAMSAR search pattern waypoints for a given search area.

    If *pattern* is not specified, the best pattern is recommended
    based on area size.
    """
    center = (centroid_lat, centroid_lon)
    recommended = pattern or recommend_search_pattern(area_km2, "HIGH", resources)
    radius_km = (area_km2 / 3.14159) ** 0.5  # approximate radius from area

    if recommended == "Expanding Square":
        waypoints = expanding_square(center, initial_leg_km=max(radius_km * 0.2, 1.0), turns=12)
    elif recommended == "Sector Search":
        waypoints = sector_search(center, radius_km=radius_km, sectors=8)
    elif recommended == "Creeping Line Ahead":
        waypoints = creeping_line_ahead(
            center, length_km=radius_km * 2,
            spacing_km=max(radius_km * 0.15, 1.0),
            heading_deg=heading, legs=8,
        )
    else:  # Parallel Track (default for large areas)
        waypoints = parallel_track_search(
            center,
            width_km=radius_km * 2,
            height_km=radius_km * 2,
            track_spacing_km=max(radius_km * 0.15, 2.0),
            heading_deg=heading,
        )

    return SearchPatternResult(
        pattern=recommended,
        waypoints=[list(wp) for wp in waypoints],
        center=[centroid_lat, centroid_lon],
    )


@app.post("/api/sensitivity", response_model=List[SensitivityEntry])
def run_sensitivity(req: SensitivityRequest):
    """Run a lightweight sensitivity analysis on the simulation inputs.

    Perturbs each key parameter (heading, airspeed, wind speed, altitude)
    by ±10/25% and measures the effect on the centroid position.
    Uses 300 iterations per run to keep the response time reasonable.
    """
    from convergence_analysis import spatial_statistics

    aircraft_name = AIRCRAFT_ID_TO_NAME.get(req.aircraft_type)
    if not aircraft_name:
        raise HTTPException(status_code=400, detail=f"Unknown aircraft id '{req.aircraft_type}'")

    base = dict(
        iterations=req.iterations,
        last_lat=req.latitude,
        last_lon=req.longitude,
        heading_deg=req.heading,
        airspeed_kts=req.airspeed,
        altitude_ft=req.altitude,
        aircraft_type=aircraft_name,
        time_since_contact_min=req.time_since_contact,
        wind_speed_kts=req.wind_speed,
        wind_direction_deg=req.wind_direction,
        seed=99,
    )

    # compute baseline
    import copy
    base_pts = monte_carlo_simulation(**base)
    base_centroid, base_r, _ = spatial_statistics(base_pts)

    perturbations = {
        "heading_deg":    [-30, 30],
        "airspeed_kts":   [-50, 50],
        "wind_speed_kts": [-15, 15],
        "altitude_ft":    [-5000, 5000],
    }

    results: List[SensitivityEntry] = []
    for param, deltas in perturbations.items():
        for delta in deltas:
            modified = copy.deepcopy(base)
            modified[param] = modified[param] + delta
            pts = monte_carlo_simulation(**modified)
            centroid, r, _ = spatial_statistics(pts)
            shift = haversine_distance(base_centroid[0], base_centroid[1], centroid[0], centroid[1])
            r_pct = (r - base_r) / base_r * 100 if base_r > 0 else 0.0
            results.append(SensitivityEntry(
                parameter=param,
                delta=delta,
                centroid_shift_km=round(shift, 2),
                mean_radius_change_pct=round(r_pct, 1),
            ))

    # Sort by absolute centroid shift (most influential first)
    results.sort(key=lambda e: abs(e.centroid_shift_km), reverse=True)
    return results
