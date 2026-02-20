"""
AF447 Historical Validation
----------------------------
Air France 447 (A330-300) entered an aerodynamic stall at FL350
and descended nearly vertically at ~11,000 fpm.
This test validates the model against the known crash site.

Key overrides for this scenario:
  - controlled_ratio = 0.0     (100% uncontrolled stall, no glide)
  - descent_rate_override = 11000 fpm  (stall descent, not normal 2800)
  - heading_spread_deg = 180   (heading was erratic / unknown)
  - scatter 2-8 km             (uncontrolled impact scatter)
  - time_since_contact_min = 4 (aircraft fell rapidly after stall)
"""
import random
import numpy as np

from calculations import haversine_distance
from probability import monte_carlo_simulation, generate_probability_zones
from weather_data import AF447_WIND_PROFILE

# Reproducible results
random.seed(42)
np.random.seed(42)

# --- AF447 known data ---
AF447_ACTUAL = (3.04, -30.83)  # Actual crash coordinates

AF447_INPUT = {
    "last_lat": 2.98,
    "last_lon": -30.59,
    "heading_deg": 0,                   # Last known ~northbound
    "airspeed_kts": 460,
    "altitude_ft": 35000,
    "aircraft_type": "Airbus A330-300",
    "time_since_contact_min": 4,        # Rapid descent after stall onset
    "wind_speed_kts": 40,
    "wind_direction_deg": 270,          # Westerly wind
}

# AF447-specific overrides (uncontrolled stall scenario)
AF447_OVERRIDES = {
    "scenario_weights": {
        "best_glide": 0.0,      # No controlled glide — full stall
        "spiral": 0.10,         # Some chance of spiral
        "dive": 0.80,           # Primary: high-speed dive from stall
        "breakup": 0.10,        # Some debris scatter possible
    },
    "heading_spread_deg": 180,          # Heading was completely unknown
    "scatter_min_km": 2.0,             # Uncontrolled impact scatter
    "scatter_max_km": 8.0,
}

# --- Run simulation ---
points = monte_carlo_simulation(
    iterations=5000,
    **AF447_INPUT,
    **AF447_OVERRIDES,
    wind_profile=AF447_WIND_PROFILE,
)

lats = np.array([p[0] for p in points])
lons = np.array([p[1] for p in points])
centroid = (float(lats.mean()), float(lons.mean()))

# --- Metrics ---
centroid_error_km = haversine_distance(
    centroid[0], centroid[1],
    AF447_ACTUAL[0], AF447_ACTUAL[1],
)

zones = generate_probability_zones(points, centroid)

distances = [
    haversine_distance(p[0], p[1], AF447_ACTUAL[0], AF447_ACTUAL[1])
    for p in points
]
min_dist = min(distances)
closest_point = points[distances.index(min_dist)]

# Check if actual crash falls within N km of any simulation point
def coverage_check(pts, target, radius_km):
    return sum(
        1 for p in pts
        if haversine_distance(p[0], p[1], target[0], target[1]) < radius_km
    )

hits_5km = coverage_check(points, AF447_ACTUAL, 5)
hits_10km = coverage_check(points, AF447_ACTUAL, 10)
hits_25km = coverage_check(points, AF447_ACTUAL, 25)
hits_50km = coverage_check(points, AF447_ACTUAL, 50)

# Zone containment
def in_zone(zone_points, target, radius_km=10):
    return any(
        haversine_distance(p[0], p[1], target[0], target[1]) < radius_km
        for p in zone_points
    )

# --- Output ---
print("=" * 50)
print("  AF447 HISTORICAL VALIDATION RESULTS")
print("=" * 50)
print()
print(f"  Predicted centroid:  ({centroid[0]:.4f}, {centroid[1]:.4f})")
print(f"  Actual crash site:   ({AF447_ACTUAL[0]:.4f}, {AF447_ACTUAL[1]:.4f})")
print(f"  Centroid error:      {centroid_error_km:.2f} km")
print()
print(f"  Closest point:       ({closest_point[0]:.4f}, {closest_point[1]:.4f})")
print(f"  Closest distance:    {min_dist:.2f} km")
print()
print("  Coverage (points within radius of crash site):")
print(f"    Within  5 km:  {hits_5km:>5d} / {len(points)}  ({hits_5km/len(points)*100:.1f}%)")
print(f"    Within 10 km:  {hits_10km:>5d} / {len(points)}  ({hits_10km/len(points)*100:.1f}%)")
print(f"    Within 25 km:  {hits_25km:>5d} / {len(points)}  ({hits_25km/len(points)*100:.1f}%)")
print(f"    Within 50 km:  {hits_50km:>5d} / {len(points)}  ({hits_50km/len(points)*100:.1f}%)")
print()
print(f"  In HIGH zone (10km):   {in_zone(zones['HIGH'], AF447_ACTUAL, 10)}")
print(f"  In MEDIUM zone (10km): {in_zone(zones['MEDIUM'], AF447_ACTUAL, 10)}")
print()
print("  Zone distribution:")
print(f"    HIGH:   {len(zones['HIGH']):>5d} points")
print(f"    MEDIUM: {len(zones['MEDIUM']):>5d} points")
print(f"    LOW:    {len(zones['LOW']):>5d} points")
print()

# Accuracy verdict
if centroid_error_km < 50:
    verdict = "EXCELLENT — centroid within 50 km"
elif centroid_error_km < 100:
    verdict = "GOOD — centroid within 100 km"
elif centroid_error_km < 200:
    verdict = "ACCEPTABLE — centroid within 200 km"
else:
    verdict = "NEEDS IMPROVEMENT — centroid > 200 km"

print(f"  VERDICT: {verdict}")
print("=" * 50)
