import numpy as np 
from calculations import haversine_distance
from probability import monte_carlo_simulation
def spatial_statistics(points):
    lats = np.array([p[0] for p in points])
    lons = np.array([p[1] for p in points])
    centroid = (lats.mean(), lons.mean())
    distances = np.array([
        haversine_distance(p[0], p[1], centroid[0], centroid[1])
        for p in points
    ])
    mean_radius = distances.mean()
    r90 = np.percentile(distances, 90)
    return centroid, mean_radius, r90
def convergence_test(base_params, iteration_levels):
    results = []
    prev_mean_radius = None
    for n in iteration_levels:
        points = monte_carlo_simulation(iterations=n, **base_params)
        centroid, mean_radius, r90 = spatial_statistics(points)
        delta = None
        if prev_mean_radius is not None:
            delta = abs(mean_radius - prev_mean_radius)/prev_mean_radius * 100
        results.append({
            "iterations": n,
            "centroid": centroid,
            "mean_radius_km": mean_radius,
            "r90_km": r90,
            "delta_percent": delta
        })
        prev_mean_radius = mean_radius
    return results