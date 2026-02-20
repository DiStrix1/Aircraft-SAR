"""
Aircraft Search and Rescue Intelligence System
================================================
Streamlit web application — interactive SAR search-area predictor.
"""

import streamlit as st
import numpy as np
import json
import os
from datetime import datetime, timezone
from streamlit_folium import st_folium  # type: ignore

from calculations import (
    AIRCRAFT_DATA,
    haversine_distance,
    destination_point,
    calculate_glide_distance,
    project_position,
)
from probability import monte_carlo_simulation, generate_probability_zones, scenario_analysis
from weather_data import get_wind_profile, build_manual_profile, WindProfile
from search_patterns import (
    expanding_square,
    sector_search,
    parallel_track_search,
    recommend_search_pattern,
)
from visualization import (
    create_base_map,
    add_last_known_position,
    add_projected_path,
    add_range_circle,
    add_probability_heatmap,
    add_search_pattern,
    finalize_map,
)

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Aircraft SAR Intelligence",
    page_icon="✈️",
    layout="wide",
)

# ---------------------------------------------------------------------------
# Custom styling
# ---------------------------------------------------------------------------
st.markdown("""
<style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        color: #E8E8E8;
        text-align: center;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 1rem;
        color: #A0A0A0;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background: linear-gradient(135deg, #1e3a5f 0%, #0d1b2a 100%);
        border-radius: 12px;
        padding: 1.2rem;
        margin-bottom: 1rem;
        border: 1px solid #2a4a7f;
    }
    .metric-label {
        color: #7eb8da;
        font-size: 0.85rem;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    .metric-value {
        color: #ffffff;
        font-size: 1.6rem;
        font-weight: 600;
    }
    .zone-high   { color: #ff4444; font-weight: bold; }
    .zone-medium { color: #ffaa00; font-weight: bold; }
    .zone-low    { color: #44ff44; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
st.markdown('<div class="main-header">✈️ Aircraft SAR Intelligence System</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Search-area prediction powered by flight physics & Monte Carlo simulation</div>', unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Sidebar — input parameters
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header("🛩️ Flight Parameters")
    aircraft_type = st.selectbox("Aircraft Type", list(AIRCRAFT_DATA.keys()))

    st.subheader("📍 Last Known Position")
    col_lat, col_lon = st.columns(2)
    with col_lat:
        last_lat = st.number_input("Latitude (°)", value=12.0, min_value=-90.0, max_value=90.0, step=0.01, format="%.4f")
    with col_lon:
        last_lon = st.number_input("Longitude (°)", value=77.0, min_value=-180.0, max_value=180.0, step=0.01, format="%.4f")

    st.subheader("🧭 Flight Details")
    heading_deg = st.slider("Heading (°)", 0, 360, 90)
    airspeed_kts = st.number_input("Airspeed (kts)", value=int(AIRCRAFT_DATA[aircraft_type]["cruise_speed"]), min_value=50, max_value=600)
    altitude_ft = st.number_input("Altitude (ft)", value=35000, min_value=0, max_value=45000, step=500)
    time_since_contact = st.number_input("Time Since Contact (min)", value=30, min_value=1, max_value=600)

    st.subheader("🌬️ Wind Conditions")
    wind_speed_kts = st.slider("Wind Speed (kts)", 0, 100, 20)
    wind_direction_deg = st.slider("Wind From (°)", 0, 360, 270)

    # ── Weather Data Integration ─────────────────────────────────
    st.subheader("🌤️ Real Weather Data")
    st.caption(
        "Fetch actual wind data from NOAA GFS for the incident time. "
        "If unavailable, the manual wind inputs above are used."
    )
    incident_date = st.date_input(
        "Incident Date (UTC)",
        value=datetime.now().date(),
        help="Date of the incident (UTC).",
    )
    col_hr, col_mn = st.columns(2)
    with col_hr:
        incident_hour = st.number_input(
            "Hour (UTC)", min_value=0, max_value=23, value=12, step=1,
        )
    with col_mn:
        incident_minute = st.number_input(
            "Minute", min_value=0, max_value=59, value=0, step=15,
        )
    from datetime import time as _time
    incident_time = _time(incident_hour, incident_minute)
    fetch_weather = st.button("🌐  Fetch Weather Data", use_container_width=True)

    # Handle weather fetch
    if "wind_profile" not in st.session_state:
        st.session_state.wind_profile = None
    if "weather_status" not in st.session_state:
        st.session_state.weather_status = ""

    if fetch_weather:
        incident_dt = datetime.combine(incident_date, incident_time).replace(tzinfo=timezone.utc)
        with st.spinner("Fetching wind data from NOAA GFS…"):
            profile = get_wind_profile(last_lat, last_lon, incident_dt)
        if profile is not None:
            st.session_state.wind_profile = profile
            st.session_state.weather_status = f"✅ Weather data loaded ({profile.source})"
        else:
            # Build fallback from manual input
            st.session_state.wind_profile = build_manual_profile(wind_speed_kts, wind_direction_deg)
            st.session_state.weather_status = (
                "⚠️ GFS data unavailable — using atmospheric model from manual input"
            )

    if st.session_state.weather_status:
        st.info(st.session_state.weather_status)

    # Show wind profile table if available
    if st.session_state.wind_profile is not None:
        wp = st.session_state.wind_profile
        with st.expander(f"📊 Wind Profile ({wp.source})", expanded=False):
            import pandas as pd
            df = pd.DataFrame([
                {
                    "Altitude (ft)": int(l.altitude_ft),
                    "Speed (kts)": round(l.wind_speed_kts, 1),
                    "Direction (°)": round(l.wind_direction_deg, 1),
                }
                for l in wp.layers
            ])
            st.dataframe(df, use_container_width=True, hide_index=True)

    st.subheader("⚙️ Simulation")
    iterations = st.slider("Monte Carlo Iterations", 200, 5000, 1200, step=100)

    # ── Advanced scenario overrides ──────────────────────────────
    with st.expander("🔬 Advanced Scenario Controls"):
        st.caption(
            "Adjust these for special scenarios (e.g. uncontrolled stall, "
            "mid-air breakup). Defaults work well for typical engine-out glides."
        )
        controlled_ratio = st.slider(
            "Controlled Glide Ratio",
            min_value=0.0, max_value=1.0, value=0.7, step=0.05,
            help="Fraction of iterations that assume a controlled glide. "
                 "Set to 0.0 for full uncontrolled descent (e.g. stall).",
        )
        ac_default_dr = AIRCRAFT_DATA[aircraft_type].get("descent_rate_fpm", 2800)
        use_custom_descent = st.checkbox("Override Descent Rate", value=False)
        if use_custom_descent:
            descent_rate_override = st.number_input(
                "Descent Rate (fpm)",
                min_value=500, max_value=30000, value=ac_default_dr, step=500,
                help="For aerodynamic stalls use ~10,000–11,000 fpm. "
                     "For controlled descent the aircraft default is used.",
            )
        else:
            descent_rate_override = None

        heading_spread_deg = st.slider(
            "Heading Spread (±°)",
            min_value=0, max_value=180, value=15, step=5,
            help="Random heading variation per iteration. "
                 "Use ±180° when heading was completely unknown.",
        )
        col_smin, col_smax = st.columns(2)
        with col_smin:
            scatter_min = st.number_input(
                "Scatter Min (km)", min_value=0.0, max_value=50.0, value=0.0, step=0.5,
                help="Minimum random scatter added to each impact point.",
            )
        with col_smax:
            scatter_max = st.number_input(
                "Scatter Max (km)", min_value=0.0, max_value=50.0, value=0.0, step=0.5,
                help="Maximum random scatter added to each impact point.",
            )

    calculate = st.button("🔎  Calculate Search Area", type="primary", use_container_width=True)

# ---------------------------------------------------------------------------
# Main area
# ---------------------------------------------------------------------------
if calculate:
    ac = AIRCRAFT_DATA[aircraft_type]

    with st.spinner("Running Monte Carlo simulation…"):
        # ── Monte Carlo ──────────────────────────────────────────────
        points = monte_carlo_simulation(
            iterations=iterations,
            last_lat=last_lat,
            last_lon=last_lon,
            heading_deg=heading_deg,
            airspeed_kts=airspeed_kts,
            altitude_ft=altitude_ft,
            aircraft_type=aircraft_type,
            time_since_contact_min=time_since_contact,
            wind_speed_kts=wind_speed_kts,
            wind_direction_deg=wind_direction_deg,
            controlled_ratio=controlled_ratio,
            descent_rate_override=descent_rate_override,
            heading_spread_deg=float(heading_spread_deg),
            scatter_min_km=scatter_min,
            scatter_max_km=scatter_max,
            wind_profile=st.session_state.get("wind_profile"),
        )

        lats = np.array([p[0] for p in points])
        lons = np.array([p[1] for p in points])
        centroid = (float(lats.mean()), float(lons.mean()))

        zones = generate_probability_zones(points, centroid)
        scenario = scenario_analysis(altitude_ft, airspeed_kts, time_since_contact, wind_speed_kts)

        # ── Glide range ──────────────────────────────────────────────
        glide_km = calculate_glide_distance(
            altitude_ft, ac["glide_ratio"], airspeed_kts,
            ac["best_glide_speed"], wind_speed_kts, wind_direction_deg, heading_deg,
        )

        # ── Projected position ───────────────────────────────────────
        proj_lat, proj_lon = project_position(
            last_lat, last_lon, heading_deg, airspeed_kts,
            wind_speed_kts, wind_direction_deg, time_since_contact,
        )

    # ── Metrics row ──────────────────────────────────────────────────
    st.markdown("---")
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.metric("Glide Range", f"{glide_km:.1f} km")
    with m2:
        st.metric("Scenario", scenario["scenario"])
    with m3:
        st.metric("Severity", scenario["severity"])
    with m4:
        search_area_km2 = np.pi * (np.std(lats) * 111) * (np.std(lons) * 111 * np.cos(np.radians(centroid[0])))
        st.metric("Est. Search Area", f"{search_area_km2:,.0f} km²")

    # ── Map ──────────────────────────────────────────────────────────
    st.markdown("### 🗺️ Search Area Map")
    fmap = create_base_map(centroid, zoom_start=7)
    add_last_known_position(fmap, (last_lat, last_lon))
    add_projected_path(fmap, [(last_lat, last_lon), (proj_lat, proj_lon)])
    add_range_circle(fmap, (last_lat, last_lon), glide_km, "Glide Range", "cyan")
    add_probability_heatmap(fmap, points)

    # Search-pattern overlay
    pattern_name = recommend_search_pattern(search_area_km2, "HIGH", 1)
    if pattern_name == "Sector Search":
        wp = sector_search(centroid, glide_km * 0.3)
    elif pattern_name == "Expanding Square":
        wp = expanding_square(centroid, 5.0)
    else:
        wp = parallel_track_search(centroid, 20, 30, 5, heading_deg)
    add_search_pattern(fmap, wp, pattern_name)

    fmap = finalize_map(fmap)

    st_folium(fmap, width=None, height=550, returned_objects=[])

    # ── Zone breakdown ───────────────────────────────────────────────
    st.markdown("### 📊 Probability Zone Breakdown")
    z1, z2, z3 = st.columns(3)
    with z1:
        st.markdown(f'<div class="metric-card"><span class="metric-label">🔴 High Probability</span><br/>'
                     f'<span class="metric-value">{len(zones["HIGH"])} pts</span></div>', unsafe_allow_html=True)
    with z2:
        st.markdown(f'<div class="metric-card"><span class="metric-label">🟠 Medium Probability</span><br/>'
                     f'<span class="metric-value">{len(zones["MEDIUM"])} pts</span></div>', unsafe_allow_html=True)
    with z3:
        st.markdown(f'<div class="metric-card"><span class="metric-label">🟢 Low Probability</span><br/>'
                     f'<span class="metric-value">{len(zones["LOW"])} pts</span></div>', unsafe_allow_html=True)

    # ── Statistics ───────────────────────────────────────────────────
    st.markdown("### 📈 Simulation Statistics")
    s1, s2 = st.columns(2)
    with s1:
        st.write(f"**Centroid:** ({centroid[0]:.4f}°, {centroid[1]:.4f}°)")
        st.write(f"**Iterations:** {iterations}")
        st.write(f"**Recommended Pattern:** {pattern_name}")
    with s2:
        st.write(f"**Wind Factor:** {scenario['wind_factor']}")
        st.write(f"**Altitude Category:** {scenario['altitude_category']}")
        centroid_dist = haversine_distance(last_lat, last_lon, centroid[0], centroid[1])
        st.write(f"**Centroid Offset:** {centroid_dist:.1f} km from last known")

else:
    st.info("👈 Enter flight parameters in the sidebar and click **Calculate Search Area** to begin.")
