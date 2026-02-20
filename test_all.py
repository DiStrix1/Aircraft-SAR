"""
Comprehensive Test Suite for Aircraft-SAR Project
Tests all modules: calculations, probability, search_patterns, visualization
"""

import unittest
import math
import sys

# Test calculations module
from calculations import (
    EARTH_RADIUS_KM, KNOTS_TO_KMH, FEET_TO_KM, AIRCRAFT_DATA,
    haversine_distance, destination_point, calculate_glide_distance,
    calculate_fuel_range, calculate_wind_drift, project_position,
    wind_speed_at_altitude, multi_layer_wind_drift,
    project_glide_position_multilayer,
)

# Test probability module
from probability import (
    monte_carlo_simulation, generate_probability_zones, scenario_analysis
)

# Test search_patterns module
from search_patterns import (
    expanding_square, sector_search, parallel_track_search,
    creeping_line_ahead, recommend_search_pattern
)

# Test visualization module
from visualization import (
    create_base_map, add_last_known_position, add_projected_path,
    add_range_circle, add_probability_heatmap, add_search_pattern, finalize_map
)


class TestConstants(unittest.TestCase):
    """Test that constants are correctly defined"""
    
    def test_earth_radius(self):
        self.assertAlmostEqual(EARTH_RADIUS_KM, 6371.0, places=1)
    
    def test_knots_to_kmh(self):
        self.assertAlmostEqual(KNOTS_TO_KMH, 1.852, places=3)
    
    def test_feet_to_km(self):
        self.assertAlmostEqual(FEET_TO_KM, 0.0003048, places=6)
    
    def test_aircraft_data_exists(self):
        self.assertIn("Cessna 172S", AIRCRAFT_DATA)
        self.assertIn("Boeing 737-800", AIRCRAFT_DATA)
        self.assertIn("Boeing 777-200ER", AIRCRAFT_DATA)
        self.assertIn("Airbus A320-200", AIRCRAFT_DATA)
        self.assertIn("Piper PA-28-181", AIRCRAFT_DATA)
    
    def test_aircraft_data_has_required_fields(self):
        for aircraft, data in AIRCRAFT_DATA.items():
            self.assertIn("glide_ratio", data, f"{aircraft} missing glide_ratio")
            self.assertIn("cruise_speed", data, f"{aircraft} missing cruise_speed")
            self.assertIn("best_glide_speed", data, f"{aircraft} missing best_glide_speed")


class TestHaversineDistance(unittest.TestCase):
    """Test haversine distance calculations"""
    
    def test_same_point(self):
        """Distance between same point should be 0"""
        dist = haversine_distance(0, 0, 0, 0)
        self.assertAlmostEqual(dist, 0, places=5)
    
    def test_known_distance(self):
        """Test with known distance between two cities approx"""
        # London to Paris approx 344 km
        dist = haversine_distance(51.5074, -0.1278, 48.8566, 2.3522)
        self.assertGreater(dist, 300)
        self.assertLess(dist, 400)
    
    def test_antipodal_points(self):
        """Test distance between antipodal points (max ~20,000 km)"""
        dist = haversine_distance(0, 0, 0, 180)
        self.assertAlmostEqual(dist, math.pi * EARTH_RADIUS_KM, delta=10)


class TestDestinationPoint(unittest.TestCase):
    """Test destination point calculation"""
    
    def test_zero_distance(self):
        """Zero distance should return same point"""
        lat, lon = destination_point(10.0, 20.0, 45, 0)
        self.assertAlmostEqual(lat, 10.0, places=5)
        self.assertAlmostEqual(lon, 20.0, places=5)
    
    def test_north_movement(self):
        """Moving north should increase latitude"""
        lat, lon = destination_point(0, 0, 0, 100)
        self.assertGreater(lat, 0)
        self.assertAlmostEqual(lon, 0, places=3)
    
    def test_east_movement(self):
        """Moving east should increase longitude"""
        lat, lon = destination_point(0, 0, 90, 100)
        self.assertAlmostEqual(lat, 0, places=3)
        self.assertGreater(lon, 0)
    
    def test_south_movement(self):
        """Moving south should decrease latitude"""
        lat, lon = destination_point(10, 0, 180, 100)
        self.assertLess(lat, 10)


class TestGlideDistance(unittest.TestCase):
    """Test glide distance calculations"""
    
    def test_basic_glide(self):
        """Test basic glide distance calculation"""
        dist = calculate_glide_distance(
            altitude_ft=10000,
            glide_ratio=10,
            airspeed_kts=100,
            best_glide_speed_kts=100,
            wind_speed_kts=0,
            wind_direction_deg=0,
            heading_deg=0
        )
        # 10000 ft = 3.048 km, glide ratio 10 means ~30 km
        self.assertGreater(dist, 25)
        self.assertLess(dist, 35)
    
    def test_zero_altitude(self):
        """Zero altitude should give zero glide distance"""
        dist = calculate_glide_distance(
            altitude_ft=0,
            glide_ratio=10,
            airspeed_kts=100,
            best_glide_speed_kts=100,
            wind_speed_kts=0,
            wind_direction_deg=0,
            heading_deg=0
        )
        self.assertAlmostEqual(dist, 0, places=2)
    
    def test_tailwind_increases_glide(self):
        """Tailwind should increase glide distance"""
        no_wind = calculate_glide_distance(10000, 10, 100, 100, 0, 0, 0)
        tailwind = calculate_glide_distance(10000, 10, 100, 100, 20, 0, 0)
        self.assertGreater(tailwind, no_wind)
    
    def test_headwind_decreases_glide(self):
        """Headwind should decrease glide distance"""
        no_wind = calculate_glide_distance(10000, 10, 100, 100, 0, 0, 0)
        headwind = calculate_glide_distance(10000, 10, 100, 100, 20, 180, 0)
        self.assertLess(headwind, no_wind)


class TestFuelRange(unittest.TestCase):
    """Test fuel range calculations"""
    
    def test_basic_fuel_range(self):
        """Test basic fuel range calculation"""
        range_km = calculate_fuel_range(
            fuel_remaining_kg=100,
            fuel_burn_rate_kg_per_hr=50,
            groundspeed_kts=100
        )
        # 2 hours at 100 kts = 200 nm = 370 km
        self.assertGreater(range_km, 350)
        self.assertLess(range_km, 400)
    
    def test_zero_fuel(self):
        """Zero fuel should give zero range"""
        range_km = calculate_fuel_range(0, 50, 100)
        self.assertAlmostEqual(range_km, 0, places=2)
    
    def test_zero_burn_rate(self):
        """Zero burn rate should return zero to avoid division by zero"""
        range_km = calculate_fuel_range(100, 0, 100)
        self.assertAlmostEqual(range_km, 0, places=2)
    
    def test_negative_values_return_zero(self):
        """Negative burn rate should return zero"""
        range_km = calculate_fuel_range(100, -50, 100)
        self.assertAlmostEqual(range_km, 0, places=2)


class TestWindDrift(unittest.TestCase):
    """Test wind drift calculations"""
    
    def test_no_wind(self):
        """No wind should mean no drift"""
        drift = calculate_wind_drift(0, 0, 0, 60)
        self.assertAlmostEqual(drift, 0, places=5)
    
    def test_crosswind(self):
        """Pure crosswind should cause maximum drift"""
        drift = calculate_wind_drift(20, 90, 0, 60)  # West wind, heading north
        self.assertNotEqual(drift, 0)
    
    def test_headwind_no_lateral_drift(self):
        """Headwind should cause no lateral drift"""
        drift = calculate_wind_drift(20, 180, 0, 60)  # South wind, heading north
        self.assertAlmostEqual(drift, 0, places=3)


class TestProjectPosition(unittest.TestCase):
    """Test position projection"""
    
    def test_no_wind_movement(self):
        """Test position projection without wind"""
        new_lat, new_lon = project_position(0, 0, 0, 100, 0, 0, 60)
        self.assertGreater(new_lat, 0)  # Should move north
    
    def test_with_wind(self):
        """Test position projection with wind"""
        no_wind_lat, no_wind_lon = project_position(0, 0, 0, 100, 0, 0, 60)
        with_wind_lat, with_wind_lon = project_position(0, 0, 0, 100, 20, 90, 60)
        # West wind should push aircraft east
        self.assertGreater(with_wind_lon, no_wind_lon)


class TestMonteCarloSimulation(unittest.TestCase):
    """Test Monte Carlo simulation"""
    
    def test_returns_correct_count(self):
        """Should return correct number of iterations"""
        points = monte_carlo_simulation(
            iterations=100,
            last_lat=12.0,
            last_lon=77.0,
            heading_deg=90,
            airspeed_kts=120,
            altitude_ft=10000,
            aircraft_type="Cessna 172S",
            time_since_contact_min=60,
            wind_speed_kts=15,
            wind_direction_deg=270
        )
        self.assertEqual(len(points), 100)
    
    def test_points_are_tuples(self):
        """Each point should be a (lat, lon) tuple"""
        points = monte_carlo_simulation(
            iterations=10,
            last_lat=12.0,
            last_lon=77.0,
            heading_deg=90,
            airspeed_kts=120,
            altitude_ft=10000,
            aircraft_type="Cessna 172S",
            time_since_contact_min=60,
            wind_speed_kts=15,
            wind_direction_deg=270
        )
        for point in points:
            self.assertIsInstance(point, tuple)
            self.assertEqual(len(point), 2)
    
    def test_invalid_aircraft_raises_error(self):
        """Invalid aircraft type should raise ValueError"""
        with self.assertRaises(ValueError):
            monte_carlo_simulation(
                iterations=10,
                last_lat=12.0,
                last_lon=77.0,
                heading_deg=90,
                airspeed_kts=120,
                altitude_ft=10000,
                aircraft_type="Invalid Aircraft",
                time_since_contact_min=60,
                wind_speed_kts=15,
                wind_direction_deg=270
            )


class TestProbabilityZones(unittest.TestCase):
    """Test probability zone generation"""
    
    def test_zones_classification(self):
        """Test that zones are correctly classified"""
        points = [(0, 0), (0.1, 0.1), (0.5, 0.5), (1.0, 1.0)]
        zones = generate_probability_zones(points, (0, 0))
        self.assertIn("HIGH", zones)
        self.assertIn("MEDIUM", zones)
        self.assertIn("LOW", zones)
    
    def test_all_points_classified(self):
        """All points should be classified into a zone"""
        points = [(0, 0), (0.1, 0.1), (0.5, 0.5), (1.0, 1.0)]
        zones = generate_probability_zones(points, (0, 0))
        total = len(zones["HIGH"]) + len(zones["MEDIUM"]) + len(zones["LOW"])
        self.assertEqual(total, len(points))


class TestSearchPatterns(unittest.TestCase):
    """Test search pattern generation"""
    
    def test_expanding_square_returns_waypoints(self):
        """Expanding square should return waypoints"""
        waypoints = expanding_square((12.0, 77.0), 5.0, turns=8)
        self.assertGreater(len(waypoints), 0)
        self.assertEqual(waypoints[0], (12.0, 77.0))  # Should start at center
    
    def test_sector_search_returns_waypoints(self):
        """Sector search should return waypoints"""
        waypoints = sector_search((12.0, 77.0), 10.0, sectors=6)
        self.assertGreater(len(waypoints), 0)
    
    def test_parallel_track_returns_waypoints(self):
        """Parallel track should return waypoints"""
        waypoints = parallel_track_search((12.0, 77.0), 20.0, 30.0, 5.0, 0)
        self.assertGreater(len(waypoints), 0)
    
    def test_creeping_line_returns_waypoints(self):
        """Creeping line ahead should return waypoints"""
        waypoints = creeping_line_ahead((12.0, 77.0), 10.0, 2.0, 0, 4)
        self.assertGreater(len(waypoints), 0)
    
    def test_recommend_pattern_small_area(self):
        """Small area should recommend Sector Search or Expanding Square"""
        pattern = recommend_search_pattern(10, "HIGH", 1)
        self.assertIn(pattern, ["Sector Search", "Expanding Square"])
    
    def test_recommend_pattern_large_area(self):
        """Large area should recommend Parallel Track"""
        pattern = recommend_search_pattern(500, "HIGH", 1)
        self.assertEqual(pattern, "Parallel Track")


class TestVisualization(unittest.TestCase):
    """Test visualization functions"""
    
    def test_create_base_map(self):
        """Should create a folium map"""
        import folium
        fmap = create_base_map((12.0, 77.0))
        self.assertIsInstance(fmap, folium.Map)
    
    def test_add_last_known_position(self):
        """Should add marker without error"""
        fmap = create_base_map((12.0, 77.0))
        add_last_known_position(fmap, (12.0, 77.0))
        # No assertion needed - just verify no exception
    
    def test_add_projected_path(self):
        """Should add polyline without error"""
        fmap = create_base_map((12.0, 77.0))
        add_projected_path(fmap, [(12.0, 77.0), (12.5, 77.5)])
        # No assertion needed - just verify no exception
    
    def test_add_range_circle(self):
        """Should add circle without error"""
        fmap = create_base_map((12.0, 77.0))
        add_range_circle(fmap, (12.0, 77.0), 50.0, "Test Circle", "blue")
        # No assertion needed - just verify no exception
    
    def test_add_probability_heatmap(self):
        """Should add heatmap without error"""
        fmap = create_base_map((12.0, 77.0))
        points = [(12.0, 77.0), (12.1, 77.1), (12.2, 77.2)]
        add_probability_heatmap(fmap, points)
        # No assertion needed - just verify no exception
    
    def test_add_search_pattern(self):
        """Should add search pattern without error"""
        fmap = create_base_map((12.0, 77.0))
        waypoints = [(12.0, 77.0), (12.1, 77.1), (12.2, 77.2)]
        add_search_pattern(fmap, waypoints, "Test Pattern")
        # No assertion needed - just verify no exception
    
    def test_finalize_map(self):
        """Should finalize map and return it"""
        import folium
        fmap = create_base_map((12.0, 77.0))
        result = finalize_map(fmap)
        self.assertIsInstance(result, folium.Map)


class TestEdgeCases(unittest.TestCase):
    """Test edge cases and boundary conditions"""
    
    def test_extreme_latitude(self):
        """Test with extreme latitude values"""
        lat, lon = destination_point(89.0, 0, 0, 100)
        self.assertLessEqual(lat, 90)
    
    def test_negative_coordinates(self):
        """Test with negative coordinates"""
        dist = haversine_distance(-33.8688, 151.2093, -34.0, 151.0)  # Sydney area
        self.assertGreater(dist, 0)
    
    def test_zero_time(self):
        """Zero time should return original position"""
        lat, lon = project_position(10, 20, 90, 100, 0, 0, 0)
        self.assertAlmostEqual(lat, 10, places=5)
        self.assertAlmostEqual(lon, 20, places=5)


if __name__ == "__main__":
    # Run tests with verbosity
    unittest.main(verbosity=2)
