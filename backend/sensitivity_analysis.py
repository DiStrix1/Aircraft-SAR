"""
Aircraft SAR – Sensitivity analysis
=====================================
Measures how each input parameter affects the simulation output.
Run directly to see sensitivity table, or import for programmatic use.
"""

import copy
import numpy as np
from calculations import haversine_distance
from probability import monte_carlo_simulation
from convergence_analysis import spatial_statistics


def run_simulation(params, iterations=3000):
    """Run a single simulation and return spatial statistics."""
    points = monte_carlo_simulation(iterations=iterations, **params)
    centroid, mean_radius, r90 = spatial_statistics(points)
    return centroid, mean_radius, r90


def sensitivity_analysis(base_params, perturbations, iterations=3000):
    """Perturb each parameter and measure the effect on simulation output.

    Parameters
    ----------
    base_params : dict
        Baseline simulation parameters.
    perturbations : dict
        Mapping of parameter name -> list of delta values to test.
    iterations : int
        Iterations per simulation run.

    Returns
    -------
    list[dict]
        One entry per perturbation with centroid shift, radius change, etc.
    """
    baseline_centroid, baseline_r, baseline_r90 = run_simulation(
        base_params, iterations
    )
    results = []
    for param, deltas in perturbations.items():
        for delta in deltas:
            modified = copy.deepcopy(base_params)
            modified[param] += delta
            centroid, r, r90 = run_simulation(modified, iterations)
            centroid_shift = haversine_distance(
                baseline_centroid[0], baseline_centroid[1],
                centroid[0], centroid[1],
            )
            radius_pct = (r - baseline_r) / baseline_r * 100 if baseline_r > 0 else 0
            r90_pct = (r90 - baseline_r90) / baseline_r90 * 100 if baseline_r90 > 0 else 0
            results.append({
                "parameter": param,
                "delta": delta,
                "centroid_shift_km": centroid_shift,
                "mean_radius_change_pct": radius_pct,
                "r90_change_pct": r90_pct,
            })
    return results


if __name__ == "__main__":
    params = {
        "last_lat": 2.98,
        "last_lon": -30.59,
        "heading_deg": 0,
        "airspeed_kts": 460,
        "altitude_ft": 35000,
        "aircraft_type": "Airbus A330-300",
        "time_since_contact_min": 4,
        "wind_speed_kts": 40,
        "wind_direction_deg": 270,
    }
    perturbations = {
        "heading_deg": [-30, -15, 15, 30],
        "airspeed_kts": [-50, -25, 25, 50],
        "wind_speed_kts": [-20, -10, 10, 20],
        "altitude_ft": [-5000, -2000, 2000, 5000],
    }
    results = sensitivity_analysis(params, perturbations, iterations=1000)

    print("\n  Sensitivity Analysis")
    print("  " + "-" * 70)
    print(f"  {'Parameter':<20} {'Delta':>8} {'Shift (km)':>10} {'R chg %':>8} {'R90 chg %':>10}")
    print("  " + "-" * 70)
    for r in results:
        print(
            f"  {r['parameter']:<20} {r['delta']:>+8.0f} "
            f"{r['centroid_shift_km']:>10.1f} {r['mean_radius_change_pct']:>+8.1f} "
            f"{r['r90_change_pct']:>+10.1f}"
        )