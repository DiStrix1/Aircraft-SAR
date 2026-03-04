from convergence_analysis import convergence_test

AF447_BASE = {
    "last_lat": 2.98,
    "last_lon": -30.59,
    "heading_deg": 0,
    "airspeed_kts": 460,
    "altitude_ft": 35000,
    "aircraft_type": "Airbus A330-300",
    "time_since_contact_min": 4,
    "wind_speed_kts": 40,
    "wind_direction_deg": 270,
    # AF447-specific overrides (uncontrolled stall)
    "controlled_ratio": 0.0,
    "descent_rate_override": 11000,
    "heading_spread_deg": 180,
    "scatter_min_km": 2.0,
    "scatter_max_km": 8.0,
}

iteration_levels = [500, 1000, 2000, 3000, 4000, 5000]

results = convergence_test(AF447_BASE, iteration_levels)

for r in results:
    print(r)
