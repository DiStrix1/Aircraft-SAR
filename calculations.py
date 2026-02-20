"""
Aircraft SAR – Flight-physics calculation engine
=================================================
Provides:
  • Haversine great-circle distance
  • Destination-point projection
  • Glide-range estimation (with wind correction)
  • Fuel-range estimation
  • Wind-drift & multi-layer wind model
  • Position projection helpers
"""

from __future__ import annotations
import math
import json
import os
from typing import Tuple, List

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
EARTH_RADIUS_KM: float = 6371.0
KNOTS_TO_KMH: float = 1.852
FEET_TO_KM: float = 0.0003048

# ---------------------------------------------------------------------------
# Aircraft look-up table (loaded from aircraft_specs.json)
# ---------------------------------------------------------------------------
_SPECS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "aircraft_specs.json")
with open(_SPECS_PATH, "r") as _f:
    _RAW_SPECS = json.load(_f)

# Build the AIRCRAFT_DATA dict that the rest of the code-base expects.
# Keys expected per aircraft: glide_ratio, cruise_speed, best_glide_speed,
# descent_rate_fpm, fuel_burn_kg_hr
AIRCRAFT_DATA: dict = {}
for _name, _spec in _RAW_SPECS.items():
    AIRCRAFT_DATA[_name] = {
        "glide_ratio": _spec["glide_ratio"],
        "cruise_speed": _spec["cruise_speed_kts"],
        "best_glide_speed": _spec["best_glide_speed_kts"],
        "descent_rate_fpm": _spec.get("descent_rate_fpm", 2800),
        "fuel_burn_kg_hr": _spec.get("fuel_burn_kg_hr", 0),
    }


# ---------------------------------------------------------------------------
# Core geometry helpers
# ---------------------------------------------------------------------------
def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Return great-circle distance in **km** between two lat/lon points."""
    φ1, φ2 = math.radians(lat1), math.radians(lat2)
    Δφ = math.radians(lat2 - lat1)
    Δλ = math.radians(lon2 - lon1)
    a = math.sin(Δφ / 2) ** 2 + math.cos(φ1) * math.cos(φ2) * math.sin(Δλ / 2) ** 2
    return EARTH_RADIUS_KM * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def destination_point(lat: float, lon: float, bearing_deg: float, distance_km: float) -> Tuple[float, float]:
    """Return (lat, lon) after travelling *distance_km* along *bearing_deg* from (lat, lon)."""
    φ1 = math.radians(lat)
    λ1 = math.radians(lon)
    θ = math.radians(bearing_deg)
    δ = distance_km / EARTH_RADIUS_KM  # angular distance

    φ2 = math.asin(
        math.sin(φ1) * math.cos(δ) + math.cos(φ1) * math.sin(δ) * math.cos(θ)
    )
    λ2 = λ1 + math.atan2(
        math.sin(θ) * math.sin(δ) * math.cos(φ1),
        math.cos(δ) - math.sin(φ1) * math.sin(φ2),
    )
    return math.degrees(φ2), math.degrees(λ2)


# ---------------------------------------------------------------------------
# Glide-range estimation
# ---------------------------------------------------------------------------
def calculate_glide_distance(
    altitude_ft: float,
    glide_ratio: float,
    airspeed_kts: float,
    best_glide_speed_kts: float,
    wind_speed_kts: float,
    wind_direction_deg: float,
    heading_deg: float,
) -> float:
    """Return estimated glide distance in **km**.

    Accounts for:
      - speed efficiency (ratio of actual speed to best-glide speed)
      - wind component along the flight heading
    """
    altitude_km = altitude_ft * FEET_TO_KM
    # Speed efficiency factor (flying at best-glide speed yields 1.0)
    speed_efficiency = min(airspeed_kts / best_glide_speed_kts, 1.0) if best_glide_speed_kts else 1.0

    base_glide_km = altitude_km * glide_ratio * speed_efficiency

    # Wind component along heading (positive = tailwind)
    relative_wind_angle = math.radians(wind_direction_deg - heading_deg)
    wind_component_kts = wind_speed_kts * math.cos(relative_wind_angle)
    wind_component_kmh = wind_component_kts * KNOTS_TO_KMH

    # Approximate descent time (hours)
    best_glide_kmh = best_glide_speed_kts * KNOTS_TO_KMH
    descent_time_hr = (base_glide_km / best_glide_kmh) if best_glide_kmh else 0

    wind_adjustment_km = wind_component_kmh * descent_time_hr

    return max(base_glide_km + wind_adjustment_km, 0.0)


# ---------------------------------------------------------------------------
# Fuel-range estimation
# ---------------------------------------------------------------------------
def calculate_fuel_range(
    fuel_remaining_kg: float,
    fuel_burn_rate_kg_per_hr: float,
    groundspeed_kts: float,
) -> float:
    """Return distance in **km** that can be flown with remaining fuel."""
    if fuel_remaining_kg <= 0 or fuel_burn_rate_kg_per_hr <= 0:
        return 0.0
    endurance_hr = fuel_remaining_kg / fuel_burn_rate_kg_per_hr
    return groundspeed_kts * KNOTS_TO_KMH * endurance_hr


# ---------------------------------------------------------------------------
# Wind drift
# ---------------------------------------------------------------------------
def calculate_wind_drift(
    wind_speed_kts: float,
    wind_direction_deg: float,
    heading_deg: float,
    time_minutes: float,
) -> float:
    """Return **lateral** wind drift in km (perpendicular to heading)."""
    relative_angle = math.radians(wind_direction_deg - heading_deg)
    crosswind_kts = wind_speed_kts * math.sin(relative_angle)
    crosswind_kmh = crosswind_kts * KNOTS_TO_KMH
    return crosswind_kmh * (time_minutes / 60.0)


# ---------------------------------------------------------------------------
# Position projection
# ---------------------------------------------------------------------------
def project_position(
    lat: float,
    lon: float,
    heading_deg: float,
    airspeed_kts: float,
    wind_speed_kts: float,
    wind_direction_deg: float,
    time_minutes: float,
) -> Tuple[float, float]:
    """Project an aircraft position forward in time, accounting for wind.

    Returns (new_lat, new_lon).
    """
    if time_minutes <= 0:
        return lat, lon

    time_hr = time_minutes / 60.0

    # Ground speed vector (aircraft TAS + wind)
    heading_rad = math.radians(heading_deg)
    wind_dir_rad = math.radians(wind_direction_deg)

    # Aircraft velocity components (north, east)
    vn_aircraft = airspeed_kts * math.cos(heading_rad)
    ve_aircraft = airspeed_kts * math.sin(heading_rad)

    # Wind velocity components (wind FROM → blowing TO opposite direction)
    vn_wind = wind_speed_kts * math.cos(wind_dir_rad)
    ve_wind = wind_speed_kts * math.sin(wind_dir_rad)

    vn = vn_aircraft + vn_wind
    ve = ve_aircraft + ve_wind

    groundspeed_kts_total = math.sqrt(vn ** 2 + ve ** 2)
    ground_track_rad = math.atan2(ve, vn)
    ground_track_deg = math.degrees(ground_track_rad) % 360

    distance_km = groundspeed_kts_total * KNOTS_TO_KMH * time_hr

    return destination_point(lat, lon, ground_track_deg, distance_km)


# ---------------------------------------------------------------------------
# Multi-layer wind model — atmospheric profile
# ---------------------------------------------------------------------------

# Empirically-calibrated altitude/multiplier pairs for wind speed.
# Multiplier is relative to the SURFACE wind speed the user provides.
# Based on standard atmospheric wind profiles (ISA + typical mid-latitude).
_WIND_PROFILE_TABLE: list[tuple[float, float]] = [
    #  (altitude_ft, speed_multiplier)
    (0,        1.0),    # surface reference
    (1_000,    1.1),    # surface boundary layer
    (2_000,    1.2),    # top of boundary layer
    (5_000,    1.5),    # lower troposphere
    (10_000,   2.0),    # mid-lower troposphere
    (18_000,   2.8),    # mid troposphere
    (25_000,   3.5),    # upper troposphere approach
    (30_000,   4.5),    # jet stream entry
    (35_000,   5.0),    # jet stream core (typical peak)
    (40_000,   4.8),    # above jet core, slight decrease
    (45_000,   4.2),    # lower stratosphere, decreasing
]

# Wind direction veering with altitude (Northern Hemisphere).
# (altitude_ft, clockwise_rotation_deg) relative to surface direction.
_WIND_VEER_TABLE: list[tuple[float, float]] = [
    (0,        0.0),
    (2_000,    10.0),    # boundary layer Ekman spiral
    (5_000,    20.0),    # lower free atmosphere
    (10_000,   28.0),    # approaching geostrophic
    (20_000,   35.0),    # roughly geostrophic
    (30_000,   38.0),    # upper troposphere
    (45_000,   40.0),    # stabilises above tropopause
]


def _interpolate_table(
    table: list[tuple[float, float]], altitude_ft: float
) -> float:
    """Linearly interpolate a value from an (altitude, value) lookup table."""
    if altitude_ft <= table[0][0]:
        return table[0][1]
    if altitude_ft >= table[-1][0]:
        return table[-1][1]

    for i in range(len(table) - 1):
        alt_lo, val_lo = table[i]
        alt_hi, val_hi = table[i + 1]
        if alt_lo <= altitude_ft <= alt_hi:
            frac = (altitude_ft - alt_lo) / (alt_hi - alt_lo)
            return val_lo + frac * (val_hi - val_lo)

    return table[-1][1]  # fallback


def wind_speed_at_altitude(
    base_wind_speed_kts: float,
    base_altitude_ft: float = 0.0,
    target_altitude_ft: float = 0.0,
) -> float:
    """Estimate wind speed at *target_altitude_ft* using a piecewise
    atmospheric profile.

    Uses linear interpolation between empirically-calibrated altitude layers
    covering surface → boundary layer → troposphere → jet stream → lower
    stratosphere.  Replaces the old 1/7 power-law which was only valid
    below ~2,000 ft.

    *base_altitude_ft* is accepted for backward compatibility but the
    profile is always anchored to the surface (the user-provided wind is
    treated as the surface observation).
    """
    if base_wind_speed_kts <= 0:
        return 0.0
    if target_altitude_ft <= 0:
        return base_wind_speed_kts

    multiplier = _interpolate_table(_WIND_PROFILE_TABLE, target_altitude_ft)
    return base_wind_speed_kts * multiplier


def wind_direction_at_altitude(
    base_direction_deg: float,
    target_altitude_ft: float,
) -> float:
    """Estimate wind direction at altitude, accounting for Ekman veering.

    Wind direction veers (rotates clockwise in the Northern Hemisphere)
    with altitude due to friction reduction and geostrophic adjustment.
    Total veering is typically 30-40° from surface to upper troposphere.

    Returns direction in degrees [0, 360).
    """
    if target_altitude_ft <= 0:
        return base_direction_deg % 360

    veer_deg = _interpolate_table(_WIND_VEER_TABLE, target_altitude_ft)
    return (base_direction_deg + veer_deg) % 360


def multi_layer_wind_drift(
    wind_speed_kts: float,
    wind_direction_deg: float,
    heading_deg: float,
    start_altitude_ft: float,
    descent_rate_fpm: float,
    time_minutes: float,
    layers: int = 5,
    wind_profile=None,
) -> float:
    """Compute cumulative lateral drift through multiple altitude layers.

    At each layer, both wind **speed** and **direction** are adjusted for
    the current altitude.  If *wind_profile* (a ``WindProfile`` instance from
    ``weather_data``) is provided, real wind data is interpolated; otherwise
    the atmospheric profile model is used.
    """
    if time_minutes <= 0 or descent_rate_fpm <= 0:
        return 0.0

    # Lazy import to avoid circular dependency at module level
    _wind_at_alt = None
    if wind_profile is not None:
        from weather_data import wind_at_altitude as _waa
        _wind_at_alt = lambda alt: _waa(wind_profile, alt)

    layer_time = time_minutes / layers
    total_drift = 0.0
    current_alt = start_altitude_ft

    for _ in range(layers):
        if _wind_at_alt is not None:
            layer_wind_spd, layer_wind_dir = _wind_at_alt(current_alt)
        else:
            layer_wind_spd = wind_speed_at_altitude(wind_speed_kts, 0.0, current_alt)
            layer_wind_dir = wind_direction_at_altitude(wind_direction_deg, current_alt)
        drift = calculate_wind_drift(layer_wind_spd, layer_wind_dir, heading_deg, layer_time)
        total_drift += drift
        current_alt = max(current_alt - descent_rate_fpm * layer_time, 0)

    return total_drift


def project_glide_position_multilayer(
    lat: float,
    lon: float,
    heading_deg: float,
    altitude_ft: float,
    glide_ratio: float,
    best_glide_speed_kts: float,
    wind_speed_kts: float,
    wind_direction_deg: float,
    descent_rate_fpm: float = 2800,
    layers: int = 5,
    wind_profile=None,
) -> Tuple[float, float]:
    """Project an aircraft's glide endpoint using a multi-layer wind model.

    At each altitude layer, wind speed and direction are adjusted.  If
    *wind_profile* is provided, real wind data is used; otherwise the
    atmospheric profile model is applied.

    Returns (final_lat, final_lon).
    """
    if altitude_ft <= 0 or descent_rate_fpm <= 0:
        return lat, lon

    _wind_at_alt = None
    if wind_profile is not None:
        from weather_data import wind_at_altitude as _waa
        _wind_at_alt = lambda alt: _waa(wind_profile, alt)

    layer_alt = altitude_ft / layers
    current_alt = altitude_ft
    cur_lat, cur_lon = lat, lon

    for _ in range(layers):
        mid_alt = current_alt - layer_alt / 2

        # Wind at this altitude band
        if _wind_at_alt is not None:
            layer_wind_spd, layer_wind_dir = _wind_at_alt(mid_alt)
        else:
            layer_wind_spd = wind_speed_at_altitude(wind_speed_kts, 0.0, mid_alt)
            layer_wind_dir = wind_direction_at_altitude(wind_direction_deg, mid_alt)

        # Glide distance for this altitude band
        layer_glide_km = calculate_glide_distance(
            layer_alt, glide_ratio, best_glide_speed_kts, best_glide_speed_kts,
            layer_wind_spd, layer_wind_dir, heading_deg,
        )

        # Forward projection
        cur_lat, cur_lon = destination_point(cur_lat, cur_lon, heading_deg, layer_glide_km)

        # Lateral drift for this layer
        layer_time_min = layer_alt / descent_rate_fpm
        layer_drift_km = calculate_wind_drift(
            layer_wind_spd, layer_wind_dir, heading_deg, layer_time_min
        )
        drift_bearing = (heading_deg + 90) % 360 if layer_drift_km >= 0 else (heading_deg - 90) % 360
        cur_lat, cur_lon = destination_point(cur_lat, cur_lon, drift_bearing, abs(layer_drift_km))

        current_alt -= layer_alt

    return cur_lat, cur_lon


