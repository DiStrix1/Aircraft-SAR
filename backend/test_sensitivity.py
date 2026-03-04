from sensitivity_analysis import sensitivity_analysis

BASE_PARAMS = {
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

PERTURBATIONS = {
    "heading_deg": [-5, 5],
    "airspeed_kts": [-20, 20],
    "altitude_ft": [-2000, 2000],
    "wind_speed_kts": [-10, 10],
}

results = sensitivity_analysis(BASE_PARAMS, PERTURBATIONS)

for r in results:
    print(r)
