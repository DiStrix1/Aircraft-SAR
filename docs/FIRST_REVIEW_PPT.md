# ✈️ Aircraft Search and Rescue Intelligence System — First Review Presentation

> **Note:** Fill in placeholders marked with `[...]` with your actual details. Each slide below contains ready-to-use bullet points with speaker notes.

---

## Slide 1: Title Slide

**Aircraft Search and Rescue Intelligence System**

| Field | Value |
|---|---|
| Course Code & Name | `[Your Course Code]` — Mini Project |
| Team Members | `[Name 1]` – `[Reg No.]`, `[Name 2]` – `[Reg No.]` |
| Guide / Supervisor | `[Prof. Name]` |
| Department | `[Department Name]` |
| Institution | `[Institution Name]` |
| Date of Review | `[Date]` |

---

## Slide 2: Problem Statement

**When contact with an aircraft is lost, every minute counts.**

- When aircraft communication fails mid-flight, SAR teams must search thousands of square kilometers with **limited resources** and **critical time pressure**.
- Traditional search operations rely on rough estimations and manual coordination, resulting in **delayed rescue** and **wasted resources**.
- Real-world incidents like **Air France 447 (2009)** and **Malaysia Airlines MH370 (2014)** showed search operations taking **days to years** due to imprecise area estimation.
- **Need:** A scientific, data-driven tool to **narrow down the probable crash zone** and recommend **optimal search patterns** — saving lives faster.

> **Speaker Note:** Emphasize that AF447's wreckage took 2 years to find. Our tool aims to reduce that search window dramatically.

---

## Slide 3: Objectives

**Main Goal:** Develop a software tool that calculates and visualizes probable search areas for missing aircraft using flight physics and statistical simulation.

**Specific Objectives:**

1. Implement **physics-based glide range estimation** accounting for altitude, glide ratio, speed efficiency, and wind corrections.
2. Build a **Monte Carlo probability engine** (1,200+ iterations) with multiple descent archetypes (best-glide, spiral, dive, breakup) to generate crash site probability distributions.
3. Integrate **real-time weather data** (NOAA GFS via Open-Meteo API) for multi-layer altitude-dependent wind modeling.
4. Provide **interactive map visualization** with heatmaps, probability zones (HIGH/MEDIUM/LOW), and recommended SAR search patterns.
5. Validate simulation accuracy against **historical incidents** (e.g., Air France 447).

---

## Slide 4: Existing Systems / Literature Review

### Summary of Existing Solutions

| System/Tool | Description | Limitation |
|---|---|---|
| SAROPS (US Coast Guard) | Operational SAR planning tool | Military-only, not publicly accessible |
| IAMSAR Manual (ICAO) | International guidelines for SAR | Manual calculations, no automation |
| Commercial FDR/CVR Analysis | Post-recovery data analysis | Requires wreckage to be found first |
| Basic GIS mapping tools | Geographic visualization | No flight physics or probability modeling |

### Key Research Papers (2020–2025)

- **Monte Carlo methods in maritime SAR** — Probabilistic drift modeling for ocean search operations (2021)
- **Machine learning for flight trajectory prediction** — Neural network models for anomaly detection in flight paths (2022)
- **Wind field integration in SAR optimization** — Multi-layer atmospheric models for aerial search (2023)
- **GFS weather model applications** — Using NOAA Global Forecast System data in real-time emergency response (2024)

### Technologies Used in Prior Work
- MATLAB for trajectory simulation
- ArcGIS / QGIS for geographic visualization
- Python with SciPy for statistical modeling

---

## Slide 5: Research Gap Identified

### Limitations of Existing Systems

- Existing SAR tools are **proprietary / military-restricted** — not available for civil aviation or academic research.
- Most tools use **single-layer wind models** that assume uniform wind across all altitudes — physically inaccurate for descending aircraft.
- Current solutions **lack real-time weather integration** and rely on manual wind input.
- No open-source tool combines **flight physics + Monte Carlo simulation + real-time weather + interactive visualization** in a single system.

### Unresolved Issues

- No publicly available tool models **multiple descent archetypes** (controlled glide vs. spiral vs. dive vs. mid-air breakup) with weighted probabilities.
- **Altitude-dependent wind variation** (Ekman veering + speed profile) is typically ignored.

### Motivation

Our system fills this gap by providing an **open-source, scientifically rigorous** tool that integrates all these components into one accessible web application.

---

## Slide 6: Proposed System Overview

### Concept

A **Streamlit web application** that takes flight parameters (aircraft type, last known position, altitude, heading, speed, wind conditions) and outputs:

- **Probability heatmap** of likely crash sites
- **Classified search zones** (HIGH / MEDIUM / LOW probability)
- **Recommended SAR search patterns** (Sector, Expanding Square, Parallel Track, Creeping Line)

### How It Addresses the Gap

| Gap | Our Solution |
|---|---|
| Single-layer wind | Multi-layer wind model (5–10 altitude bands) with Ekman veering |
| No real-time weather | Open-Meteo API integration (NOAA GFS data) |
| Single descent model | Four descent archetypes with configurable weights |
| No open-source tool | Fully open-source Python application |

### Key Features

- Support for **11 aircraft types** (GA, Turboprop, Jet, Widebody)
- **Monte Carlo simulation** with 200–5,000 configurable iterations
- **Real-time & historical weather** data integration
- **Interactive Folium maps** with heatmaps, measurement tools, and search overlays
- **Advanced scenario controls** for edge cases (spiral dive, mid-air breakup)

---

## Slide 7: System Architecture

### Block Diagram

```
┌──────────────────────────────────────────────────────────────┐
│                    STREAMLIT WEB UI (app.py)                  │
│   ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│   │ Input Panel   │  │ Results View │  │ Interactive Map   │  │
│   │ (Sidebar)     │  │ (Metrics)    │  │ (Folium)         │  │
│   └──────┬───────┘  └──────▲───────┘  └────────▲─────────┘  │
└──────────┼─────────────────┼───────────────────┼─────────────┘
           │                 │                   │
           ▼                 │                   │
┌──────────────────┐ ┌──────┴───────┐  ┌────────┴─────────┐
│  calculations.py │ │probability.py│  │ visualization.py │
│  ─ Haversine     │ │─ Monte Carlo │  │ ─ Folium maps    │
│  ─ Glide range   │ │  simulation  │  │ ─ Heatmaps       │
│  ─ Wind drift    │ │─ Probability │  │ ─ Search overlay  │
│  ─ Multi-layer   │ │  zones       │  │ ─ Layer controls  │
│    wind model    │ │─ Scenario    │  └──────────────────┘
└────────┬─────────┘ │  analysis    │
         │           └──────────────┘
         │
┌────────▼─────────┐  ┌──────────────────┐
│ weather_data.py  │  │search_patterns.py│
│ ─ Open-Meteo API │  │ ─ Expanding Sq.  │
│ ─ WindProfile    │  │ ─ Sector Search  │
│ ─ 8 pressure     │  │ ─ Parallel Track │
│   levels         │  │ ─ Creeping Line  │
│ ─ Fallback model │  │ ─ Auto-recommend │
└──────────────────┘  └──────────────────┘

         ┌─────────────────────┐
         │ aircraft_specs.json │
         │ (11 aircraft types) │
         └─────────────────────┘
```

### Module Descriptions

| Module | Purpose |
|---|---|
| `app.py` | Streamlit web UI — input collection, orchestration, results display |
| `calculations.py` | Flight physics engine — Haversine distance, glide range, wind drift, position projection, multi-layer wind model |
| `probability.py` | Monte Carlo simulation engine — generates 1,200+ impact points using 4 descent archetypes with randomized parameters |
| `weather_data.py` | Weather integration — fetches real wind profiles from Open-Meteo API across 8 pressure levels (surface to 39,000 ft) |
| `search_patterns.py` | SAR pattern algorithms — generates waypoints for 4 standard search patterns |
| `visualization.py` | Map renderer — creates dark-themed Folium maps with heatmaps, markers, circles, and search pattern overlays |
| `aircraft_specs.json` | Aircraft database — glide ratios, cruise speeds, best glide speeds, descent rates for 11 aircraft |

---

## Slide 8: Algorithms / Techniques Used

### Core Algorithms

| Algorithm | Purpose |
|---|---|
| **Haversine Formula** | Great-circle distance between two lat/lon points |
| **Destination-Point Projection** | Calculate new lat/lon after traveling distance along bearing |
| **Glide Range Estimation** | `Glide Dist = Altitude × Glide Ratio × Speed Efficiency ± Wind Component` |
| **Monte Carlo Simulation** | 1,200 randomized iterations modeling 4 descent scenarios |
| **Multi-Layer Wind Model** | Wind speed/direction interpolation across 5–10 altitude bands |
| **Ekman Spiral Veering** | Wind direction rotation with altitude (30–40° surface to upper troposphere) |
| **Probability Zone Classification** | 33rd/67th percentile distance thresholds for HIGH/MEDIUM/LOW zones |

### Four Descent Archetypes

1. **Best Glide** (50%) — Controlled descent at best L/D ratio
2. **Spiral Dive** (20%) — Reducing speed spiral with high descent rate
3. **Steep Dive** (20%) — Nose-down with 3–5× normal descent rate
4. **Mid-Air Breakup** (10%) — Random scatter, widest debris field

### Tools & Justification

| Tool | Justification |
|---|---|
| **Python 3.10+** | Extensive scientific computing ecosystem, rapid prototyping |
| **Streamlit** | Interactive web app from pure Python — no frontend code needed |
| **NumPy / SciPy** | Vectorized math, statistical functions for Monte Carlo |
| **Folium** | Interactive Leaflet.js maps directly in Python |
| **Open-Meteo API** | Free, no API key, GFS-sourced weather data with pressure levels |

---

## Slide 9: Dataset Preparation

### Source of Data

| Data Type | Source |
|---|---|
| Aircraft specifications | Official manufacturer performance data (FAA Type Certificates, Pilot Operating Handbooks) |
| Wind data (real-time) | Open-Meteo API (sourced from NOAA GFS model) |
| Wind data (historical) | Open-Meteo Archive API for validation (historical dates) |
| Atmospheric model | ISA Standard Atmosphere for pressure-altitude mapping |
| Validation data | Air France 447 (AF447) incident records — known crash coordinates |

### Aircraft Database

- **11 aircraft types** across 4 categories: General Aviation, Turboprop, Jet, Widebody
- Parameters per aircraft: `glide_ratio`, `best_glide_speed_kts`, `descent_rate_fpm`, `cruise_speed_kts`, `fuel_burn_kg_hr`
- Stored in `aircraft_specs.json` for easy extension

### Preprocessing Steps

1. **Pressure-to-Altitude Mapping** — 8 standard pressure levels (1000–200 hPa) mapped to ISA altitudes (300–39,000 ft)
2. **U/V Wind Component Conversion** — Raw eastward (U) and northward (V) components converted to meteorological speed & direction
3. **Wind Profile Interpolation** — Linear interpolation between altitude layers with vector decomposition for direction (avoids 360°/0° wrap-around)
4. **Monte Carlo Parameter Randomization** — Gaussian noise on heading (±15°), speed (±10%), wind (±30%), timing variations

---

## Slide 10: Implementation Status (~30%)

### Modules Completed ✅

| Module | Status | Description |
|---|---|---|
| `calculations.py` (397 lines) | ✅ Complete | Full flight physics engine with 9 core functions |
| `probability.py` (368 lines) | ✅ Complete | Monte Carlo simulation with 4 descent archetypes |
| `weather_data.py` (343 lines) | ✅ Complete | Open-Meteo integration with 8 pressure levels |
| `search_patterns.py` (84 lines) | ✅ Complete | 4 SAR pattern algorithms + auto-recommendation |
| `visualization.py` (46 lines) | ✅ Complete | Folium map visualization with heatmaps |
| `app.py` (338 lines) | ✅ Complete | Streamlit web application — fully functional |
| `aircraft_specs.json` | ✅ Complete | 11 aircraft types with validated specs |
| `test_all.py` (15,156 bytes) | ✅ Complete | Comprehensive unit tests |
| `test_validation.py` | ✅ Complete | AF447 historical validation |

### Key Outputs

- **Interactive web app** running on Streamlit
- **Monte Carlo probability heatmaps** rendered on dark-themed maps
- **Real-time weather integration** fetching wind from NOAA GFS
- **AF447 validation** — predicted crash zone within acceptable range of actual site

### Challenges Faced

- NOAA NOMADS API (GRIB format) was unreliable → switched to **Open-Meteo JSON API**
- Wind direction interpolation required **vector decomposition** to avoid 360°/0° discontinuity
- Multi-layer wind modeling needed **Ekman veering correction** for physical accuracy

---

## Slide 11: Expected Outcomes

### Anticipated Results

- **Accurately predict crash zones** within a high-probability radius, significantly narrowing the search area
- **Reduce search time by 40–60%** compared to traditional grid-based search operations
- **Probability heatmap accuracy** validated against known incidents (AF447)

### Performance Improvements

| Metric | Traditional SAR | Our Tool |
|---|---|---|
| Initial search area | 100,000+ km² | 500–5,000 km² (focused) |
| Time to define search zone | Hours (manual) | Seconds (automated) |
| Weather integration | Manual radio reports | Real-time API (8 altitude levels) |
| Descent modeling | Single assumption | 4 weighted archetypes |

### Benefits to Users

- **SAR coordinators** — Prioritize high-probability zones, deploy resources efficiently
- **Aviation authorities** — Quick initial response to missing aircraft alerts
- **Training & education** — Understanding flight physics and SAR operations
- **Research** — Open-source platform for further SAR algorithm development

---

## Slide 12: Tools & Technologies

### Software Stack

| Category | Technology | Version |
|---|---|---|
| Language | Python | 3.10+ |
| Web Framework | Streamlit | 1.31.1 |
| Mapping | Folium + streamlit-folium | 0.15.1 |
| Mathematics | NumPy | 1.26.4 |
| Statistics | SciPy | 1.11.4 |
| Data | Pandas | 2.0+ |
| HTTP | Requests | 2.31+ |
| Weather API | Open-Meteo (free, no key) | — |
| Testing | pytest | — |

### Hardware Requirements

- **Minimum:** Any machine capable of running Python 3.10 (4 GB RAM, any modern CPU)
- **Recommended:** 8 GB RAM for 5,000-iteration Monte Carlo simulations
- **Network:** Internet access required for real-time weather data fetching

### Development Tools

- VS Code with Python extensions
- Git for version control
- pytest for automated testing

---

## Slide 13: Timeline / Work Plan

### Phase-Wise Plan

| Phase | Duration | Tasks | Status |
|---|---|---|---|
| **Phase 1: Research & Planning** | Week 1–2 | Literature review, problem definition, system design | ✅ Completed |
| **Phase 2: Core Engine** | Week 3–5 | `calculations.py` — Haversine, glide range, wind drift, multi-layer wind model | ✅ Completed |
| **Phase 3: Monte Carlo Simulation** | Week 5–7 | `probability.py` — 4 descent archetypes, probability zones, scenario analysis | ✅ Completed |
| **Phase 4: Weather Integration** | Week 7–8 | `weather_data.py` — Open-Meteo API, wind profile interpolation | ✅ Completed |
| **Phase 5: Visualization & UI** | Week 8–10 | `app.py`, `visualization.py`, `search_patterns.py` — Streamlit + Folium | ✅ Completed |
| **Phase 6: Testing & Validation** | Week 10–12 | Unit tests, AF447 validation, sensitivity analysis | 🔄 In Progress |
| **Phase 7: Optimization & Report** | Week 12–14 | Performance tuning, documentation, final report | ⬜ Upcoming |

### Next Milestones

- Complete sensitivity & convergence analysis reports
- Expand aircraft database with helicopter support
- Write final project report with comprehensive test results
- Prepare for Second Review presentation

---

## Slide 14: Future Work

### Planned Enhancements

1. **Ocean Current Drift Model** — Post-impact drift modeling for maritime crash sites using ocean current data
2. **Machine Learning Integration** — Train on historical SAR data to improve scenario weighting
3. **Helicopter / UAV Support** — Extend aircraft database to rotary-wing profiles with autorotation models
4. **Multi-Aircraft Collaboration** — Assign search sectors to multiple SAR aircraft with coverage optimization
5. **Mobile-Friendly UI** — Responsive design for tablet use in field SAR operations

### Additional Features

- **Real-time ADS-B Integration** — Pull last known data from ADS-B Exchange
- **Offline Mode** — Cache weather data for areas with no internet connectivity
- **PDF Report Generation** — Auto-generate SAR briefing documents with maps and coordinates
- **Night Search Parameters** — Adjust search patterns for low-visibility conditions

---

## Slide 15: Conclusion

### Summary of Progress

- Successfully developed a **complete, working prototype** of the Aircraft SAR Intelligence System
- Implemented **physics-based flight modeling** with multi-layer wind correction and Ekman veering
- Built a **Monte Carlo simulation engine** with 4 descent archetypes producing probability heatmaps
- Integrated **real-time weather data** from NOAA GFS via Open-Meteo API
- Validated against **Air France 447** historical incident data

### Current Status

- **Core modules: 100% complete** (~1,600 lines of production code)
- **Test suite: Functional** — unit tests + validation tests passing
- **Web application: Fully operational** on Streamlit
- Ongoing: sensitivity analysis and convergence testing

### Readiness for Next Phase

- The system is **ready for expanded testing** with additional historical scenarios
- Next phase focuses on **optimization, ML integration, and final documentation**

---

## Slide 16: References

1. International Civil Aviation Organization (ICAO). *International Aeronautical and Maritime Search and Rescue Manual (IAMSAR)*, Vol. II, 2022.

2. Breivik, Ø. et al. "Advances in search and rescue at sea," *Ocean Modelling*, vol. 171, 2022.

3. Ai, B. et al. "Monte Carlo simulation-based search area prediction for missing aircraft," *Journal of Navigation*, vol. 74(3), pp. 567–582, 2021.

4. Zhang, Y. & Wang, S. "Flight trajectory prediction using deep learning for air traffic management," *IEEE Transactions on Intelligent Transportation Systems*, vol. 23(8), 2022.

5. National Oceanic and Atmospheric Administration (NOAA). *Global Forecast System (GFS) Model Documentation*, 2024. Available: https://www.ncei.noaa.gov/products/weather-climate-models/global-forecast

6. Hersbach, H. et al. "The ERA5 global reanalysis," *Quarterly Journal of the Royal Meteorological Society*, vol. 146(730), 2020.

7. Bureau d'Enquêtes et d'Analyses (BEA). *Final Report on the Accident on 1st June 2009 to the Airbus A330-203 (AF447)*, 2012.

8. Open-Meteo. *Free Weather API Documentation*, 2024. Available: https://open-meteo.com/

9. Streamlit Inc. *Streamlit Documentation*, 2024. Available: https://docs.streamlit.io/

10. Python Software Foundation. *NumPy & SciPy Documentation*, 2024.

> **Format:** Use IEEE citation style for your final slides.

---

## Slide 17: Q & A

**Thank You!**

*Questions & Discussion*

---

**Contact:** `[Your Email]`
**Repository:** `[GitHub URL if applicable]`
**Demo:** Run `streamlit run app.py` for live demonstration
