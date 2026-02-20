from __future__ import annotations
from typing import List, Tuple, Dict
import folium
from folium.plugins import HeatMap, MeasureControl
LatLon = Tuple[float, float]

def create_base_map(center: LatLon, zoom_start: int = 7) -> folium.Map:
    """Creating the base map with SAR Controls"""
    fmap = folium.Map(
        location = center,
        zoom_start = zoom_start,
        tiles = "CartoDB dark_matter",
        control_scale = True,
    )
    fmap.add_child(MeasureControl())
    return fmap

def add_last_known_position(fmap: folium.Map, position: LatLon) -> None:
    """Add the last known position marker"""
    folium.Marker(location = position, tooltip="Last Known Position", icon = folium.Icon(color="red", icon="plane", prefix="fa")).add_to(fmap)

def add_projected_path(fmap: folium.Map, path: List[LatLon]) -> None:
    """Adding the projected path as a dashed polyline"""
    folium.PolyLine(locations=path, color="cyan",weight=3,dash_array="5,5",tooltip="Projected Flight Path").add_to(fmap)

def add_range_circle(fmap:folium.Map, center:LatLon, radius_km:float, label:str, color:str) -> None:
    """Adding the circle range on the map"""
    folium.Circle(location=center, radius=radius_km*1000,color=color,fill=False,tooltip=label).add_to(fmap)

def add_probability_heatmap(fmap:folium.Map, points: List[LatLon]) -> None:
    """Adding the probability heatmap layer"""
    heat_layer = HeatMap(data=points, radius=15, blur=25, max_zoom=8, name="Probability Heatmap")
    heat_layer.add_to(fmap)

def add_search_pattern(fmap: folium.Map, waypoints: List[LatLon], name: str = "Search Pattern") -> None:
    """Overlay for the SAR search problem"""
    folium.PolyLine(locations = waypoints, color="orange",weight=4,tooltip=name).add_to(fmap)
    for idx, wp in enumerate(waypoints):
        folium.CircleMarker(location=wp,radius=3,fill=True,color="yellow",popup=f"WP{idx+1}").add_to(fmap)

def finalize_map(fmap:folium.Map) -> folium.Map:
    """Add layer controls and return map"""
    folium.LayerControl(collapsed=False).add_to(fmap)
    return fmap

