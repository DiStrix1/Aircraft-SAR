"""
Production Validation Test Suite -- Aircraft SAR Intelligence System
=====================================================================
Tests the system against 5 real-world aviation incidents with publicly
documented crash coordinates.  Each scenario uses tuned parameters
(scenario weights, heading spread, scatter) that match the known
circumstances of the incident.

Run:
    python test_production.py

Exit code 0 = all scenarios PASS, 1 = at least one FAIL.
"""

import sys
import random
import numpy as np

from calculations import haversine_distance
from probability import monte_carlo_simulation, generate_probability_zones
from weather_data import AF447_WIND_PROFILE, build_manual_profile

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
SEED = 42
ITERS = 3000          # iterations per scenario (balance speed vs accuracy)
SEP = "=" * 72
THIN = "-" * 72

# Pass / fail thresholds
MAX_CENTROID_ERROR_KM = 80       # centroid must be within this of actual
MIN_COVERAGE_50KM_PCT = 15       # at least this % of points within 50 km
CRASH_IN_HIGH_MED = True         # crash site must fall in HIGH or MEDIUM


# ---------------------------------------------------------------------------
# Scenario definitions
# ---------------------------------------------------------------------------
SCENARIOS = [
    {
        "name": "AF447 -- Airbus A330 Stall/Dive over Atlantic (2009)",
        "description": (
            "Air France 447 stalled at FL350 over the Atlantic and entered "
            "an uncontrolled descent.  Uses historical ERA5 wind profile "
            "and dive-heavy scenario weights."
        ),
        "actual": (3.0400, -30.8300),
        "sim_kwargs": {
            "last_lat": 2.98, "last_lon": -30.59,
            "heading_deg": 0, "airspeed_kts": 460,
            "altitude_ft": 35_000, "aircraft_type": "Airbus A330-300",
            "time_since_contact_min": 4,
            "wind_speed_kts": 40, "wind_direction_deg": 270,
            "scenario_weights": {
                "best_glide": 0.00, "spiral": 0.10,
                "dive": 0.80,       "breakup": 0.10,
            },
            "heading_spread_deg": 180,
            "scatter_min_km": 2.0, "scatter_max_km": 8.0,
            "wind_profile": AF447_WIND_PROFILE,
        },
    },
    {
        "name": "Germanwings 9525 -- A320 Deliberate Descent (2015)",
        "description": (
            "Copilot deliberately descended the aircraft from FL380 into "
            "the French Alps.  Heading was maintained (270 deg), descent "
            "rate was high and controlled.  Last ATC contact east of crash."
        ),
        "actual": (44.2800, 6.4400),
        "sim_kwargs": {
            "last_lat": 44.15, "last_lon": 7.10,
            "heading_deg": 270, "airspeed_kts": 350,
            "altitude_ft": 38_000, "aircraft_type": "Airbus A320-200",
            "time_since_contact_min": 8,
            "wind_speed_kts": 20, "wind_direction_deg": 330,
            "scenario_weights": {
                "best_glide": 0.00, "spiral": 0.05,
                "dive": 0.90,       "breakup": 0.05,
            },
            "heading_spread_deg": 15,
            "scatter_min_km": 0.0, "scatter_max_km": 0.0,
        },
    },
    {
        "name": "EgyptAir 804 -- A320 Loss over Mediterranean (2016)",
        "description": (
            "Aircraft disappeared from radar at FL370 over the eastern "
            "Mediterranean.  Wreckage found ~40 km from last radar point.  "
            "Cause involved fire/smoke leading to loss of control."
        ),
        "actual": (33.6800, 29.2500),
        "sim_kwargs": {
            "last_lat": 33.68, "last_lon": 28.79,
            "heading_deg": 140, "airspeed_kts": 440,
            "altitude_ft": 37_000, "aircraft_type": "Airbus A320-200",
            "time_since_contact_min": 2,
            "wind_speed_kts": 15, "wind_direction_deg": 290,
            "scenario_weights": {
                "best_glide": 0.10, "spiral": 0.30,
                "dive": 0.40,       "breakup": 0.20,
            },
            "heading_spread_deg": 90,
            "scatter_min_km": 1.0, "scatter_max_km": 4.0,
        },
    },
    {
        "name": "AirAsia QZ8501 -- A320 Stall/Spiral over Java Sea (2014)",
        "description": (
            "Aircraft stalled while climbing to avoid weather over the "
            "Java Sea, entered a steep spiral descent.  Wreckage found "
            "south of last known position."
        ),
        "actual": (-3.6200, 109.7100),
        "sim_kwargs": {
            "last_lat": -3.37, "last_lon": 109.69,
            "heading_deg": 185, "airspeed_kts": 430,
            "altitude_ft": 32_000, "aircraft_type": "Airbus A320-200",
            "time_since_contact_min": 3,
            "wind_speed_kts": 25, "wind_direction_deg": 270,
            "scenario_weights": {
                "best_glide": 0.00, "spiral": 0.70,
                "dive": 0.20,       "breakup": 0.10,
            },
            "heading_spread_deg": 120,
            "scatter_min_km": 1.0, "scatter_max_km": 3.0,
        },
    },
    {
        "name": "Cessna 172S -- Engine-Out Glide at 8,000 ft (Sanity Check)",
        "description": (
            "Synthetic scenario: Cessna 172S loses engine at 8,000 ft "
            "east of Los Angeles.  Controlled glide at best glide speed.  "
            "No actual crash site -- validates physics plausibility."
        ),
        "actual": None,  # no real crash to compare
        "sim_kwargs": {
            "last_lat": 34.05, "last_lon": -118.25,
            "heading_deg": 90, "airspeed_kts": 110,
            "altitude_ft": 8_000, "aircraft_type": "Cessna 172S",
            "time_since_contact_min": 10,
            "wind_speed_kts": 15, "wind_direction_deg": 240,
            "scenario_weights": {
                "best_glide": 0.85, "spiral": 0.10,
                "dive": 0.05,       "breakup": 0.00,
            },
            "heading_spread_deg": 30,
        },
        # physics check: glide ratio 9 x 8000 ft = 72,000 ft = ~22 km max
        "max_expected_glide_km": 30,
    },
]


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------
def run_scenario(scenario: dict) -> dict:
    """Run one scenario, print results, return metrics."""
    name = scenario["name"]
    desc = scenario["description"]
    actual = scenario.get("actual")
    sim_kw = scenario["sim_kwargs"]

    print(f"\n{SEP}")
    print(f"  SCENARIO: {name}")
    print(f"  {desc}")
    print(SEP)

    random.seed(SEED)
    np.random.seed(SEED)

    points = monte_carlo_simulation(iterations=ITERS, **sim_kw)
    lats = np.array([p[0] for p in points])
    lons = np.array([p[1] for p in points])
    centroid = (float(lats.mean()), float(lons.mean()))
    zones = generate_probability_zones(points, centroid)

    lat_spread = (lats.max() - lats.min()) * 111
    lon_spread = (lons.max() - lons.min()) * 111 * np.cos(np.radians(centroid[0]))
    area_km2 = np.pi * (np.std(lats) * 111) * (
        np.std(lons) * 111 * np.cos(np.radians(centroid[0]))
    )
    centroid_offset = haversine_distance(
        sim_kw["last_lat"], sim_kw["last_lon"], centroid[0], centroid[1]
    )

    print(f"\n  Centroid:              ({centroid[0]:.4f}, {centroid[1]:.4f})")
    print(f"  Centroid offset:       {centroid_offset:.1f} km from last known")
    print(f"  Point spread:          {lat_spread:.0f} km (N-S)  x  {lon_spread:.0f} km (E-W)")
    print(f"  Est. search area:      {area_km2:,.0f} km2")
    print(f"  Iterations:            {ITERS}")

    wp = sim_kw.get("wind_profile")
    print(f"  Wind source:           {wp.source if wp else 'atmospheric model (manual)'}")

    sw = sim_kw.get("scenario_weights", {})
    sw_str = "  ".join(f"{k}:{v:.0%}" for k, v in sw.items())
    print(f"  Scenario weights:      {sw_str}")

    print(f"\n  Zone distribution:")
    print(f"    HIGH:    {len(zones['HIGH']):>5} points  ({len(zones['HIGH'])/ITERS*100:.1f}%)")
    print(f"    MEDIUM:  {len(zones['MEDIUM']):>5} points  ({len(zones['MEDIUM'])/ITERS*100:.1f}%)")
    print(f"    LOW:     {len(zones['LOW']):>5} points  ({len(zones['LOW'])/ITERS*100:.1f}%)")

    result = {
        "name": name,
        "centroid": centroid,
        "area_km2": area_km2,
        "centroid_offset_km": centroid_offset,
        "zones": {k: len(v) for k, v in zones.items()},
        "passed": True,
        "checks": [],
    }

    if actual:
        centroid_err = haversine_distance(centroid[0], centroid[1], actual[0], actual[1])
        dists = [haversine_distance(p[0], p[1], actual[0], actual[1]) for p in points]
        closest = min(dists)

        within_5  = sum(1 for d in dists if d <= 5)
        within_10 = sum(1 for d in dists if d <= 10)
        within_25 = sum(1 for d in dists if d <= 25)
        within_50 = sum(1 for d in dists if d <= 50)
        pct_50 = within_50 / ITERS * 100

        # Check if actual crash falls inside HIGH or MEDIUM zone
        crash_in_high = any(
            haversine_distance(p[0], p[1], actual[0], actual[1]) <= 25
            for p in zones["HIGH"]
        )
        crash_in_med = any(
            haversine_distance(p[0], p[1], actual[0], actual[1]) <= 25
            for p in zones["MEDIUM"]
        )

        print(f"\n  -- Validation Against Actual Crash Site --")
        print(f"  Actual site:           ({actual[0]:.4f}, {actual[1]:.4f})")
        print(f"  Centroid error:        {centroid_err:.2f} km")
        print(f"  Closest point:         {closest:.2f} km")
        print(f"  Within  5 km:          {within_5:>5}/{ITERS}  ({within_5/ITERS*100:.1f}%)")
        print(f"  Within 10 km:          {within_10:>5}/{ITERS}  ({within_10/ITERS*100:.1f}%)")
        print(f"  Within 25 km:          {within_25:>5}/{ITERS}  ({within_25/ITERS*100:.1f}%)")
        print(f"  Within 50 km:          {within_50:>5}/{ITERS}  ({within_50/ITERS*100:.1f}%)")
        print(f"  Crash in HIGH zone:    {'YES' if crash_in_high else 'no'}")
        print(f"  Crash in MEDIUM zone:  {'YES' if crash_in_med else 'no'}")

        # Pass / fail checks
        c1 = centroid_err <= MAX_CENTROID_ERROR_KM
        c2 = pct_50 >= MIN_COVERAGE_50KM_PCT
        c3 = crash_in_high or crash_in_med

        result["centroid_error_km"] = centroid_err
        result["closest_km"] = closest
        result["pct_within_50km"] = pct_50

        result["checks"].append(("Centroid error <= 80 km", c1, f"{centroid_err:.1f} km"))
        result["checks"].append(("Coverage >= 15% within 50 km", c2, f"{pct_50:.1f}%"))
        result["checks"].append(("Crash in HIGH/MEDIUM zone", c3, f"H={crash_in_high} M={crash_in_med}"))

        if not (c1 and c2 and c3):
            result["passed"] = False

        verdict = "PASS" if result["passed"] else "FAIL"
        symbol = "[OK]" if result["passed"] else "[!!]"
        print(f"\n  {symbol} VERDICT: {verdict}")
        for label, ok, val in result["checks"]:
            mark = "PASS" if ok else "FAIL"
            print(f"      [{mark}]  {label}  -->  {val}")

    else:
        # Physics plausibility check (Cessna scenario)
        max_glide = scenario.get("max_expected_glide_km", 999)
        if centroid_offset > max_glide * 3:
            result["passed"] = False
            result["checks"].append(("Centroid offset plausible", False, f"{centroid_offset:.1f} km"))
        else:
            result["checks"].append(("Centroid offset plausible", True, f"{centroid_offset:.1f} km"))

        print(f"\n  -- Physics Plausibility Check --")
        print(f"  Max expected glide:    ~{max_glide} km")
        print(f"  Centroid offset:       {centroid_offset:.1f} km")
        verdict = "PASS" if result["passed"] else "FAIL"
        symbol = "[OK]" if result["passed"] else "[!!]"
        print(f"  {symbol} VERDICT: {verdict}  (offset within plausible range)")

    print()
    return result


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    print()
    print(SEP)
    print("  AIRCRAFT SAR -- PRODUCTION VALIDATION TEST SUITE")
    print(f"  Iterations per scenario: {ITERS}   |   Seed: {SEED}")
    print(SEP)

    results = []
    for sc in SCENARIOS:
        results.append(run_scenario(sc))

    # --- Summary table ---
    print(f"\n{SEP}")
    print("  SUMMARY")
    print(SEP)
    print()
    print(f"  {'#':<3} {'Scenario':<55} {'Centroid Err':>12} {'50km Cov':>9} {'Result':>8}")
    print(f"  {'-'*3} {'-'*55} {'-'*12} {'-'*9} {'-'*8}")

    all_pass = True
    for i, r in enumerate(results, 1):
        name_short = r["name"][:55]
        err = f"{r.get('centroid_error_km', 0):.1f} km" if r.get("centroid_error_km") else "N/A"
        cov = f"{r.get('pct_within_50km', 0):.0f}%" if r.get("pct_within_50km") else "N/A"
        status = "PASS" if r["passed"] else "** FAIL **"
        if not r["passed"]:
            all_pass = False
        print(f"  {i:<3} {name_short:<55} {err:>12} {cov:>9} {status:>8}")

    print()
    if all_pass:
        print("  [OK]  ALL SCENARIOS PASSED")
    else:
        print("  [!!]  SOME SCENARIOS FAILED -- review above for details")
    print(SEP)
    print()

    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
