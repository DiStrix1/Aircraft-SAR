from __future__ import annotations
from typing import List, Tuple
from calculations import destination_point
LatLon = Tuple[float, float]

def expanding_square(
    center: LatLon,
    initial_leg_km: float,
    turns: int = 8,
) -> List[LatLon]:
    """Expanding sq search from a point datum"""
    waypoints = [center]
    leg = initial_leg_km
    heading = 0
    lat, lon = center
    for i in range(1, turns+1):
        lat,lon = destination_point(lat,lon,heading,leg)
        waypoints.append((lat,lon))
        heading = (heading+90)%360
        if i%2==0:
            leg+=initial_leg_km
    return waypoints

def sector_search(
    center: LatLon,
    radius_km: float,
    sectors: int = 6,
) -> List[LatLon]:
    """Pie-slice from datum"""
    waypoints = [center]
    angle_step = 360/sectors
    for i in range(sectors):
        bearing = i*angle_step
        outer = destination_point(center[0],center[1],bearing,radius_km)
        waypoints.append(outer)
        waypoints.append(center)
    return waypoints

def parallel_track_search(center: LatLon, width_km: float, height_km: float, track_spacing_km: float, heading_deg: float,) -> List[LatLon]:
    """Grid search for large areas"""
    tracks = int(width_km//track_spacing_km)
    waypoints: List[LatLon] = []
    offset_bearing = (heading_deg + 90) % 360
    for i in range(tracks+1):
        offset = (i-tracks/2)*track_spacing_km
        start = destination_point(center[0],center[1],offset_bearing,offset)
        end = destination_point(start[0], start[1], heading_deg, height_km)
        waypoints.append(start)
        waypoints.append(end)
    return waypoints

def creeping_line_ahead(
    start_point: LatLon,
    length_km: float,
    spacing_km: float,
    heading_deg: float,
    legs: int,
) -> List[LatLon]:
    """Creeping line search from high-prob end"""
    waypoints = [start_point]
    lat, lon = start_point
    for i in range(legs):
        lat, lon = destination_point(lat, lon, heading_deg, length_km)
        waypoints.append((lat, lon))
        lateral_heading = (heading_deg + 90) % 360 if i % 2 == 0 else (heading_deg - 90) % 360
        lat, lon = destination_point(lat, lon, lateral_heading, spacing_km)
        waypoints.append((lat, lon))
        heading_deg = (heading_deg+180)%360
    return waypoints

def recommend_search_pattern(
    area_sq_km: float,
    probability_concentration: str,
    resources: int,
) -> str:
    """Recomendation of the Search Algorithms"""
    if area_sq_km <25:
        return "Sector Search" if probability_concentration == "HIGH" else  "Expanding Square"
    if 25 <= area_sq_km <= 250:
        return "Creeping Line Ahead" if probability_concentration == "HIGH" else "Parallel Track"
    if area_sq_km > 250:
        return "Parallel Track"
    return "Expanding Square"
