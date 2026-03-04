"""
Aircraft SAR – Standard SAR search patterns
=============================================
Provides waypoint generators for the four standard IAMSAR search patterns:
  * Expanding Square  -- point datum, small area
  * Sector Search     -- pie-slice from datum
  * Parallel Track    -- grid search for large areas
  * Creeping Line     -- linear sweep from high-probability end

Also provides a recommendation engine that selects the best pattern based
on area size and probability concentration.
"""

from __future__ import annotations

from typing import List, Tuple

from calculations import destination_point

LatLon = Tuple[float, float]


# ---------------------------------------------------------------------------
# Expanding Square
# ---------------------------------------------------------------------------
def expanding_square(
    center: LatLon,
    initial_leg_km: float,
    turns: int = 8,
) -> List[LatLon]:
    """Generate an expanding-square search pattern from a point datum.

    Starts at *center* and spirals outward with each pair of turns increasing
    the leg length by *initial_leg_km*.

    Parameters
    ----------
    center : LatLon
        Search datum (start point).
    initial_leg_km : float
        First leg length in km.  Must be positive.
    turns : int
        Number of turns (corners).  More turns = larger search area.

    Returns
    -------
    list[LatLon]
        Waypoints defining the search track.
    """
    if initial_leg_km <= 0:
        return [center]
    turns = max(1, turns)

    waypoints = [center]
    leg = initial_leg_km
    heading = 0.0
    lat, lon = center

    for i in range(1, turns + 1):
        lat, lon = destination_point(lat, lon, heading, leg)
        waypoints.append((lat, lon))
        heading = (heading + 90) % 360
        if i % 2 == 0:
            leg += initial_leg_km

    return waypoints


# ---------------------------------------------------------------------------
# Sector Search
# ---------------------------------------------------------------------------
def sector_search(
    center: LatLon,
    radius_km: float,
    sectors: int = 6,
) -> List[LatLon]:
    """Generate a pie-slice (sector) search pattern radiating from *center*.

    Parameters
    ----------
    center : LatLon
        Datum at the centre of the search.
    radius_km : float
        Length of each sector spoke in km.  Must be positive.
    sectors : int
        Number of pie slices (spokes).

    Returns
    -------
    list[LatLon]
        Waypoints: alternates between centre and outer spoke tips.
    """
    if radius_km <= 0:
        return [center]
    sectors = max(1, sectors)

    waypoints = [center]
    angle_step = 360.0 / sectors

    for i in range(sectors):
        bearing = i * angle_step
        outer = destination_point(center[0], center[1], bearing, radius_km)
        waypoints.append(outer)
        waypoints.append(center)

    return waypoints


# ---------------------------------------------------------------------------
# Parallel Track
# ---------------------------------------------------------------------------
def parallel_track_search(
    center: LatLon,
    width_km: float,
    height_km: float,
    track_spacing_km: float,
    heading_deg: float,
) -> List[LatLon]:
    """Generate a parallel-track (grid) search pattern for large areas.

    Parameters
    ----------
    center : LatLon
        Centre of the search box.
    width_km / height_km : float
        Dimensions of the search box.
    track_spacing_km : float
        Distance between parallel legs.  Must be positive.
    heading_deg : float
        Primary search heading in degrees.

    Returns
    -------
    list[LatLon]
        Start/end waypoints for each track leg.
    """
    if track_spacing_km <= 0 or width_km <= 0 or height_km <= 0:
        return [center]

    tracks = max(1, int(width_km / track_spacing_km))
    waypoints: List[LatLon] = []
    # Perpendicular direction to place parallel legs
    offset_bearing = (heading_deg + 90) % 360
    # Backward heading to extend each leg symmetrically from the center row
    back_bearing = (heading_deg + 180) % 360

    for i in range(tracks + 1):
        # Lateral offset so legs are symmetric around center
        offset = (i - tracks / 2) * track_spacing_km
        # Mid-point of this leg (on the center horizontal axis)
        mid = destination_point(center[0], center[1], offset_bearing, offset)
        # Extend leg height_km/2 in BOTH directions from mid-point
        start = destination_point(mid[0], mid[1], back_bearing, height_km / 2)
        end   = destination_point(mid[0], mid[1], heading_deg,  height_km / 2)
        # Alternate start/end for lawnmower pattern continuity
        if i % 2 == 0:
            waypoints.append(start)
            waypoints.append(end)
        else:
            waypoints.append(end)
            waypoints.append(start)

    return waypoints


# ---------------------------------------------------------------------------
# Creeping Line Ahead
# ---------------------------------------------------------------------------
def creeping_line_ahead(
    center: LatLon,
    length_km: float,
    spacing_km: float,
    heading_deg: float,
    legs: int,
) -> List[LatLon]:
    """Generate a creeping-line-ahead search pattern centered on *center*.

    Parameters
    ----------
    center : LatLon
        Centre of the search area (not the start corner).
    length_km : float
        Length of each sweep leg.
    spacing_km : float
        Lateral distance between legs.
    heading_deg : float
        Primary sweep heading.
    legs : int
        Number of sweep legs.

    Returns
    -------
    list[LatLon]
        Waypoints defining the creeping-line track.
    """
    if length_km <= 0 or spacing_km <= 0:
        return [center]
    legs = max(1, legs)

    # Compute the start corner by offsetting back from center so pattern is centered
    total_width = spacing_km * (legs - 1)
    back_bearing = (heading_deg + 180) % 360
    left_bearing  = (heading_deg - 90) % 360
    # Move to the leftmost starting corner
    start_mid = destination_point(center[0], center[1], back_bearing, length_km / 2)
    lat, lon = destination_point(start_mid[0], start_mid[1], left_bearing, total_width / 2)

    waypoints = [(lat, lon)]
    current_heading = heading_deg

    for i in range(legs):
        lat, lon = destination_point(lat, lon, current_heading, length_km)
        waypoints.append((lat, lon))
        lateral_heading = (current_heading + 90) % 360 if i % 2 == 0 else (current_heading - 90) % 360
        lat, lon = destination_point(lat, lon, lateral_heading, spacing_km)
        waypoints.append((lat, lon))
        current_heading = (current_heading + 180) % 360

    return waypoints


# ---------------------------------------------------------------------------
# Pattern recommendation engine
# ---------------------------------------------------------------------------
def recommend_search_pattern(
    area_sq_km: float,
    probability_concentration: str,
    resources: int,
) -> str:
    """Recommend the most appropriate IAMSAR search pattern.

    Parameters
    ----------
    area_sq_km : float
        Estimated search area in km squared.
    probability_concentration : str
        Highest zone containing most points ("HIGH", "MEDIUM", "LOW").
    resources : int
        Number of search assets available (currently unused but reserved).

    Returns
    -------
    str
        Name of the recommended pattern.
    """
    if area_sq_km < 25:
        return "Sector Search" if probability_concentration == "HIGH" else "Expanding Square"
    if area_sq_km <= 250:
        return "Creeping Line Ahead" if probability_concentration == "HIGH" else "Parallel Track"
    return "Parallel Track"
