"""
Aircraft SAR – Monte Carlo probability engine
===============================================
Provides:
  • monte_carlo_simulation  – runs N random-variation simulations
  • generate_probability_zones – classifies points into HIGH / MEDIUM / LOW
  • scenario_analysis – evaluates the most-likely scenario type
"""

from __future__ import annotations
import math
import random
from typing import List, Tuple, Dict

from calculations import (
    AIRCRAFT_DATA,
    KNOTS_TO_KMH,
    FEET_TO_KM,
    haversine_distance,
    destination_point,
    calculate_glide_distance,
    project_position,
    wind_speed_at_altitude,
    project_glide_position_multilayer,
    multi_layer_wind_drift,
)

LatLon = Tuple[float, float]

# Number of altitude layers for multi-layer wind drift calculations.
_WIND_LAYERS: int = 10

# ---------------------------------------------------------------------------
# Descent archetypes — descriptions for UI display
# ---------------------------------------------------------------------------
SCENARIO_DESCRIPTIONS: Dict[str, str] = {
    "best_glide": (
        "Best-Glide (Engine Out) — Pilot maintains best glide speed and heading. "
        "Steady controlled descent at best L/D ratio with predictable trajectory."
    ),
    "spiral": (
        "Spiral / Spin (Loss of Control) — Aircraft enters descending spiral. "
        "Very steep descent (5,000–15,000 fpm), limited horizontal travel, "
        "mostly vertical with significant wind drift."
    ),
    "dive": (
        "High-Speed Dive (Structural Failure / Upset) — Aircraft descends at "
        "very high speed (10,000–30,000 fpm). Minimal horizontal distance, "
        "impacts close to the failure point."
    ),
    "breakup": (
        "In-Flight Breakup — Aircraft breaks apart at altitude. Debris falls "
        "in multiple classes (heavy/medium/light) with very different drift "
        "characteristics, producing the widest search area."
    ),
}

# Default scenario weights when none are specified
DEFAULT_SCENARIO_WEIGHTS: Dict[str, float] = {
    "best_glide": 0.50,
    "spiral": 0.20,
    "dive": 0.20,
    "breakup": 0.10,
}


def _pick_scenario(weights: Dict[str, float]) -> str:
    """Randomly select a scenario based on normalised weights."""
    names = list(weights.keys())
    vals = [weights[n] for n in names]
    total = sum(vals)
    if total <= 0:
        return "dive"  # safe fallback
    r = random.random() * total
    cumulative = 0.0
    for name, val in zip(names, vals):
        cumulative += val
        if r <= cumulative:
            return name
    return names[-1]


def _convert_controlled_ratio(
    controlled_ratio: float, altitude_ft: float
) -> Dict[str, float]:
    """Convert old-API controlled_ratio into scenario_weights for backward compat."""
    glide_w = controlled_ratio
    remaining = 1.0 - controlled_ratio
    if altitude_ft > 25_000:
        # High altitude: more likely dive than spiral
        return {
            "best_glide": glide_w,
            "spiral": remaining * 0.15,
            "dive": remaining * 0.70,
            "breakup": remaining * 0.15,
        }
    elif altitude_ft > 10_000:
        return {
            "best_glide": glide_w,
            "spiral": remaining * 0.35,
            "dive": remaining * 0.45,
            "breakup": remaining * 0.20,
        }
    else:
        # Low altitude: spiral more likely
        return {
            "best_glide": glide_w,
            "spiral": remaining * 0.50,
            "dive": remaining * 0.30,
            "breakup": remaining * 0.20,
        }


# ---------------------------------------------------------------------------
# Monte Carlo simulation
# ---------------------------------------------------------------------------
def monte_carlo_simulation(
    iterations: int,
    last_lat: float,
    last_lon: float,
    heading_deg: float,
    airspeed_kts: float,
    altitude_ft: float,
    aircraft_type: str,
    time_since_contact_min: float,
    wind_speed_kts: float,
    wind_direction_deg: float,
    # --- optional overrides for special scenarios (e.g. AF447) ---
    controlled_ratio: float = 0.7,
    descent_rate_override: float | None = None,
    heading_spread_deg: float = 15.0,
    scatter_min_km: float = 0.0,
    scatter_max_km: float = 0.0,
    scenario_weights: Dict[str, float] | None = None,
    wind_profile=None,
) -> List[LatLon]:
    """Run *iterations* randomised simulations and return a list of (lat, lon) impact points.

    Uses four descent archetypes (best_glide, spiral, dive, breakup) with
    multi-layer wind at each altitude band.

    Parameters
    ----------
    controlled_ratio : float
        Legacy parameter. If *scenario_weights* is None, this is converted
        into archetype weights automatically.
    descent_rate_override : float | None
        If set, overrides the aircraft's default descent rate (fpm).
    heading_spread_deg : float
        Maximum random deviation applied to heading (±).
    scatter_min_km / scatter_max_km : float
        Additional random scatter applied to every impact point.
    scenario_weights : dict | None
        Optional dict mapping archetype names to relative weights, e.g.
        ``{"best_glide": 0.0, "spiral": 0.1, "dive": 0.8, "breakup": 0.1}``.
        If None, *controlled_ratio* is used to derive weights.
    wind_profile : WindProfile | None
        Optional real wind data from weather_data module. When provided,
        all multi-layer wind calculations use interpolated real data
        instead of the atmospheric profile model.
    """
    if aircraft_type not in AIRCRAFT_DATA:
        raise ValueError(
            f"Unknown aircraft type '{aircraft_type}'. "
            f"Available: {list(AIRCRAFT_DATA.keys())}"
        )

    ac = AIRCRAFT_DATA[aircraft_type]
    glide_ratio = ac["glide_ratio"]
    best_glide_speed = ac["best_glide_speed"]
    default_descent_rate = ac.get("descent_rate_fpm", 2800)
    descent_rate = descent_rate_override if descent_rate_override is not None else default_descent_rate

    # Resolve scenario weights
    if scenario_weights is not None:
        weights = scenario_weights
    else:
        weights = _convert_controlled_ratio(controlled_ratio, altitude_ft)

    points: List[LatLon] = []

    for _ in range(iterations):
        # ── Common random perturbations ──────────────────────────────
        h_var = heading_deg + random.uniform(-heading_spread_deg, heading_spread_deg)
        s_var = airspeed_kts * random.uniform(0.90, 1.10)
        w_var = wind_speed_kts * random.uniform(0.70, 1.30)
        w_dir_var = wind_direction_deg + random.uniform(-10, 10)

        # Random engine-failure timing
        failure_frac = random.uniform(0.0, 1.0)
        powered_time_min = time_since_contact_min * failure_frac

        # Phase 1 — powered flight until failure
        lat, lon = project_position(
            last_lat, last_lon, h_var, s_var, w_var, w_dir_var, powered_time_min
        )
        remaining_alt = altitude_ft

        # Phase 2 — select descent archetype and simulate
        scenario = _pick_scenario(weights)

        if scenario == "best_glide":
            # ── Best-Glide: controlled descent at best L/D ───────────
            lat, lon = project_glide_position_multilayer(
                lat, lon, h_var,
                remaining_alt, glide_ratio, best_glide_speed,
                w_var, w_dir_var,
                descent_rate_fpm=descent_rate,
                layers=_WIND_LAYERS,
                wind_profile=wind_profile,
            )

        elif scenario == "spiral":
            # ── Spiral / Spin: steep descent, mostly vertical ────────
            spiral_rate = random.uniform(5_000, 15_000)  # fpm
            if spiral_rate > 0:
                descent_time_min = remaining_alt / spiral_rate
            else:
                descent_time_min = 0.0

            # Minimal forward travel — aircraft is spinning, not flying
            residual_speed_kts = s_var * 0.08  # ~8% residual
            lat, lon = project_position(
                lat, lon, h_var, residual_speed_kts,
                0.0, 0.0, descent_time_min,
            )

            # Significant wind drift through altitude column
            lateral_drift_km = multi_layer_wind_drift(
                w_var, w_dir_var, h_var,
                remaining_alt, spiral_rate, descent_time_min,
                layers=_WIND_LAYERS,
                wind_profile=wind_profile,
            )
            drift_bearing = (h_var + 90) % 360 if lateral_drift_km >= 0 else (h_var - 90) % 360
            lat, lon = destination_point(lat, lon, drift_bearing, abs(lateral_drift_km))

        elif scenario == "dive":
            # ── High-Speed Dive: near-vertical, fast impact ──────────
            dive_rate = random.uniform(10_000, 30_000)  # fpm
            if dive_rate > 0:
                descent_time_min = remaining_alt / dive_rate
            else:
                descent_time_min = 0.0

            # Very little forward travel
            residual_speed_kts = s_var * 0.05  # ~5% residual
            lat, lon = project_position(
                lat, lon, h_var, residual_speed_kts,
                0.0, 0.0, descent_time_min,
            )

            # Minimal wind drift — descent is too fast
            lateral_drift_km = multi_layer_wind_drift(
                w_var, w_dir_var, h_var,
                remaining_alt, dive_rate, descent_time_min,
                layers=_WIND_LAYERS,
                wind_profile=wind_profile,
            )
            drift_bearing = (h_var + 90) % 360 if lateral_drift_km >= 0 else (h_var - 90) % 360
            lat, lon = destination_point(lat, lon, drift_bearing, abs(lateral_drift_km))

        else:  # breakup
            # ── In-Flight Breakup: multiple debris classes ───────────
            debris_class = random.choices(
                ["heavy", "medium", "light"],
                weights=[0.3, 0.4, 0.3],
            )[0]

            if debris_class == "heavy":
                # Engines, landing gear — fast fall, little drift
                fall_rate = random.uniform(15_000, 30_000)
                wind_sensitivity = 0.3  # 30% of actual wind effect
            elif debris_class == "medium":
                # Fuselage sections — moderate
                fall_rate = random.uniform(6_000, 15_000)
                wind_sensitivity = 0.7
            else:
                # Panels, insulation — slow fall, large drift
                fall_rate = random.uniform(2_000, 6_000)
                wind_sensitivity = 1.5  # amplified wind effect

            if fall_rate > 0:
                descent_time_min = remaining_alt / fall_rate
            else:
                descent_time_min = 0.0

            # No forward flight — debris is ballistic
            # Only wind-driven lateral drift
            lateral_drift_km = multi_layer_wind_drift(
                w_var * wind_sensitivity, w_dir_var, h_var,
                remaining_alt, fall_rate, descent_time_min,
                layers=_WIND_LAYERS,
                wind_profile=wind_profile,
            )
            drift_bearing = (h_var + 90) % 360 if lateral_drift_km >= 0 else (h_var - 90) % 360
            lat, lon = destination_point(lat, lon, drift_bearing, abs(lateral_drift_km))

        # ── Optional scatter ─────────────────────────────────────────
        if scatter_max_km > 0:
            scatter_dist = random.uniform(scatter_min_km, scatter_max_km)
            scatter_bearing = random.uniform(0, 360)
            lat, lon = destination_point(lat, lon, scatter_bearing, scatter_dist)

        points.append((lat, lon))

    return points


# ---------------------------------------------------------------------------
# Probability-zone classification
# ---------------------------------------------------------------------------
def generate_probability_zones(
    points: List[LatLon],
    center: LatLon,
) -> Dict[str, List[LatLon]]:
    """Classify *points* into HIGH / MEDIUM / LOW probability zones based on
    distance from *center*.

    Uses the 33rd and 67th percentile of distances as boundaries.
    """
    if not points:
        return {"HIGH": [], "MEDIUM": [], "LOW": []}

    distances = [
        haversine_distance(p[0], p[1], center[0], center[1]) for p in points
    ]
    sorted_dists = sorted(distances)
    p33 = sorted_dists[int(len(sorted_dists) * 0.33)]
    p67 = sorted_dists[int(len(sorted_dists) * 0.67)]

    zones: Dict[str, List[LatLon]] = {"HIGH": [], "MEDIUM": [], "LOW": []}
    for pt, d in zip(points, distances):
        if d <= p33:
            zones["HIGH"].append(pt)
        elif d <= p67:
            zones["MEDIUM"].append(pt)
        else:
            zones["LOW"].append(pt)
    return zones


# ---------------------------------------------------------------------------
# Scenario analysis
# ---------------------------------------------------------------------------
def scenario_analysis(
    altitude_ft: float,
    airspeed_kts: float,
    time_since_contact_min: float,
    wind_speed_kts: float,
) -> Dict[str, object]:
    """Return a simple scenario classification with metadata."""
    if altitude_ft > 25_000:
        scenario = "High-Altitude Emergency"
    elif altitude_ft > 10_000:
        scenario = "Mid-Altitude Emergency"
    else:
        scenario = "Low-Altitude Emergency"

    severity = "CRITICAL" if time_since_contact_min > 120 else "HIGH" if time_since_contact_min > 30 else "MODERATE"

    return {
        "scenario": scenario,
        "severity": severity,
        "altitude_category": "HIGH" if altitude_ft > 25000 else "MID" if altitude_ft > 10000 else "LOW",
        "wind_factor": "SIGNIFICANT" if wind_speed_kts > 30 else "MODERATE" if wind_speed_kts > 15 else "LIGHT",
    }
