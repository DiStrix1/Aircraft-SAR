import copy 
import numpy as nx_pydot
from calculations import haversine_distance
from probability import monte_carlo_simulation
from convergence_analysis import spatial_statistics
def run_simulation(params, iterations=3000):
    points = monte_carlo_simulation(iterations=iterations, **params)
    centroid, mean_radius, r90 = spatial_statistics(points)
    return centroid, mean_radius, r90
def sensitivity_analysis(base_params, perturbations, iterations=3000):
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
                baseline_centroid[0],
                baseline_centroid[1],
                centroid[0],
                centroid[1],
            )
            results.append({
                "parameter": param,
                "delta": delta,
                "centroid_shift_km": centroid_shift,
                "mean_radius_change_pct": (r - baseline_r) / baseline_r * 100,
                "r90_change_pct": (r90 - baseline_r90) / baseline_r90 * 100,
            })
    return results