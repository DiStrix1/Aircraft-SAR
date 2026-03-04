"""
Aircraft SAR – Convergence analysis
=====================================
Measures how the simulation stabilises as iteration count increases.
Run directly to see convergence table, or import for programmatic use.
"""

import numpy as np
from calculations import haversine_distance
from probability import monte_carlo_simulation


def spatial_statistics(points):
    """Compute centroid, mean radius, and 90th-percentile radius."""
    lats = np.array([p[0] for p in points])
    lons = np.array([p[1] for p in points])
    centroid = (float(lats.mean()), float(lons.mean()))
    distances = np.array([
        haversine_distance(p[0], p[1], centroid[0], centroid[1])
        for p in points
    ])
    mean_radius = float(distances.mean())
    r90 = float(np.percentile(distances, 90))
    return centroid, mean_radius, r90


def convergence_test(base_params, iteration_levels):
    """Run the simulation at increasing iteration counts and track stability."""
    results = []
    prev_mean_radius = None
    for n in iteration_levels:
        points = monte_carlo_simulation(iterations=n, **base_params)
        centroid, mean_radius, r90 = spatial_statistics(points)
        delta = None
        if prev_mean_radius is not None and prev_mean_radius > 0:
            delta = abs(mean_radius - prev_mean_radius) / prev_mean_radius * 100
        results.append({
            "iterations": n,
            "centroid": centroid,
            "mean_radius_km": mean_radius,
            "r90_km": r90,
            "delta_percent": delta,
        })
        prev_mean_radius = mean_radius
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
    levels = [100, 300, 500, 1000, 2000, 3000]
    results = convergence_test(params, levels)

    print("\n  Convergence Analysis")
    print("  " + "-" * 60)
    print(f"  {'Iters':>6}  {'Mean R (km)':>11}  {'R90 (km)':>9}  {'Delta %':>8}")
    print("  " + "-" * 60)
    for r in results:
        delta_str = f"{r['delta_percent']:.2f}%" if r["delta_percent"] is not None else "  --"
        print(f"  {r['iterations']:>6}  {r['mean_radius_km']:>11.2f}  {r['r90_km']:>9.2f}  {delta_str:>8}")