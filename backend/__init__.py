"""
Aircraft SAR Intelligence System
==================================
A search-area prediction tool for missing aircraft, powered by flight
physics and Monte Carlo simulation.

This package exposes the core backend modules:
  • calculations    — flight-physics engine (haversine, glide, wind drift)
  • probability     — Monte Carlo simulation and zone classification
  • weather_data    — real-time weather integration (Open-Meteo)
  • search_patterns — IAMSAR standard search patterns
  • visualization   — Folium map builder
"""

__version__ = "2.0.0"
