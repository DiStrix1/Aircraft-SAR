"""
Aircraft SAR – Map visualization layer
========================================
Provides Folium-based map building blocks for the SAR application:
  * Base map creation with dark theme and measurement tools
  * Last-known-position marker
  * Projected flight-path overlay
  * Glide-range circle
  * Probability heatmap layer
  * Zone polygon overlays (convex hulls for HIGH / MEDIUM / LOW)
  * Search-pattern waypoint overlay
  * Layer-control finaliser
"""

from __future__ import annotations

import math
from typing import List, Tuple, Dict

import folium
from folium.plugins import HeatMap, MeasureControl

LatLon = Tuple[float, float]


# ---------------------------------------------------------------------------
# Base map
# ---------------------------------------------------------------------------
def create_base_map(center: LatLon, zoom_start: int = 7) -> folium.Map:
    """Create the base Folium map with SAR-friendly defaults.

    Uses a dark CartoDB base layer for high contrast against bright markers
    and heatmaps.  Includes a measurement control for distance/area queries.
    """
    fmap = folium.Map(
        location=center,
        zoom_start=zoom_start,
        tiles="CartoDB dark_matter",
        control_scale=True,
    )
    fmap.add_child(MeasureControl())
    return fmap


# ---------------------------------------------------------------------------
# Markers and overlays
# ---------------------------------------------------------------------------
def add_last_known_position(fmap: folium.Map, position: LatLon) -> None:
    """Add a red plane icon at the last known position."""
    folium.Marker(
        location=position,
        tooltip="Last Known Position",
        icon=folium.Icon(color="red", icon="plane", prefix="fa"),
    ).add_to(fmap)


def add_projected_path(fmap: folium.Map, path: List[LatLon]) -> None:
    """Add a dashed cyan polyline showing the projected flight path."""
    if len(path) < 2:
        return
    folium.PolyLine(
        locations=path,
        color="cyan",
        weight=3,
        dash_array="5,5",
        tooltip="Projected Flight Path",
    ).add_to(fmap)


def add_range_circle(
    fmap: folium.Map,
    center: LatLon,
    radius_km: float,
    label: str,
    color: str,
) -> None:
    """Add a transparent circle showing a range boundary."""
    if radius_km <= 0:
        return
    folium.Circle(
        location=center,
        radius=radius_km * 1000,
        color=color,
        fill=False,
        tooltip=label,
    ).add_to(fmap)


# ---------------------------------------------------------------------------
# Heatmap
# ---------------------------------------------------------------------------
def add_probability_heatmap(
    fmap: folium.Map,
    points: List[LatLon],
) -> None:
    """Add a heatmap layer from simulated impact points."""
    if not points:
        return
    heat_layer = HeatMap(
        data=points,
        radius=15,
        blur=25,
        max_zoom=8,
        name="Probability Heatmap",
    )
    heat_layer.add_to(fmap)


# ---------------------------------------------------------------------------
# Zone polygon overlays (convex hulls)
# ---------------------------------------------------------------------------
def _convex_hull(points: List[LatLon]) -> List[LatLon]:
    """Compute a convex hull (Graham scan) for a set of lat/lon points.

    Returns the hull vertices in order, suitable for drawing a polygon.
    """
    if len(points) <= 2:
        return list(points)

    # Use lon as x, lat as y for the 2-D convex hull
    pts = sorted(set(points), key=lambda p: (p[1], p[0]))

    def cross(o: LatLon, a: LatLon, b: LatLon) -> float:
        return (a[1] - o[1]) * (b[0] - o[0]) - (a[0] - o[0]) * (b[1] - o[1])

    lower: List[LatLon] = []
    for p in pts:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)

    upper: List[LatLon] = []
    for p in reversed(pts):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)

    return lower[:-1] + upper[:-1]


def add_zone_overlays(
    fmap: folium.Map,
    zones: Dict[str, List[LatLon]],
) -> None:
    """Draw translucent convex-hull polygons for each probability zone.

    Colors: HIGH = red, MEDIUM = orange, LOW = green.
    """
    zone_styles = {
        "HIGH":   {"color": "#ff4444", "fill_color": "#ff4444", "fill_opacity": 0.15},
        "MEDIUM": {"color": "#ffaa00", "fill_color": "#ffaa00", "fill_opacity": 0.10},
        "LOW":    {"color": "#44cc44", "fill_color": "#44cc44", "fill_opacity": 0.05},
    }

    for zone_name, pts in zones.items():
        if len(pts) < 3:
            continue
        style = zone_styles.get(zone_name, zone_styles["LOW"])
        hull = _convex_hull(pts)
        if len(hull) < 3:
            continue
        folium.Polygon(
            locations=hull,
            color=style["color"],
            fill=True,
            fill_color=style["fill_color"],
            fill_opacity=style["fill_opacity"],
            weight=2,
            tooltip=f"{zone_name} Probability Zone",
            name=f"{zone_name} Zone",
        ).add_to(fmap)


# ---------------------------------------------------------------------------
# Search pattern overlay
# ---------------------------------------------------------------------------
def add_search_pattern(
    fmap: folium.Map,
    waypoints: List[LatLon],
    name: str = "Search Pattern",
) -> None:
    """Overlay a search-pattern track with numbered waypoint markers."""
    if not waypoints:
        return
    folium.PolyLine(
        locations=waypoints,
        color="orange",
        weight=4,
        tooltip=name,
    ).add_to(fmap)

    for idx, wp in enumerate(waypoints):
        folium.CircleMarker(
            location=wp,
            radius=3,
            fill=True,
            color="yellow",
            popup=f"WP{idx + 1}",
        ).add_to(fmap)


# ---------------------------------------------------------------------------
# Finalise
# ---------------------------------------------------------------------------
def finalize_map(fmap: folium.Map) -> folium.Map:
    """Add layer controls and return the completed map."""
    folium.LayerControl(collapsed=False).add_to(fmap)
    return fmap
