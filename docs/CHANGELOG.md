# Aircraft SAR Intelligence System — Development Changelog

**Project:** Aircraft Search and Rescue Intelligence System  
**Author:** Dishu Mahajan  
**Institution:** SRMIST, Trichy  

---

## 📅 February 5, 2026 — Project Inception & Core Development

### Phase 1: Project Setup & Foundation

- **Initialized project** at `d:\Projects\Aircraft-SAR`
- Created Python virtual environment (`venv`) with Python 3.10+
- Installed core dependencies: `streamlit`, `folium`, `numpy`, `scipy`, `branca`
- Created `requirements.txt` with pinned versions

### Phase 2: Core Physics Engine (`calculations.py`)

- Implemented **Haversine distance** formula for great-circle distance on Earth's surface
- Implemented **destination point** calculation using spherical Earth great-circle navigation
- Created **glide distance calculator** accounting for:
  - Aircraft glide ratio
  - Wind component (headwind/tailwind)
  - Speed efficiency penalty (deviation from best glide speed)
- Created **fuel range calculator** based on fuel remaining, burn rate, and groundspeed
- Implemented **wind drift calculator** using vector crosswind decomposition
- Built **position projection** function combining aircraft velocity + wind vectors to compute ground track
- Defined `AIRCRAFT_DATA` dictionary with specs for 5 aircraft:
  - Cessna 172, Boeing 737, Boeing 777, Airbus A320, Piper Cherokee

### Phase 3: Monte Carlo Probability Engine (`probability.py`)

- Implemented **Monte Carlo simulation** (1200 iterations) with stochastic variation:
  - Heading: ±15° | Airspeed: ±10% | Wind speed: ±30% | Wind direction: ±20°
  - Random engine failure timing within contact window
  - 75% controlled glide / 25% uncontrolled descent assumption
- Created **probability zone classifier** (HIGH / MEDIUM / LOW) based on radial distance ratios
- Added **scenario analysis** function for engine failure at early / mid / late stages

### Phase 4: Search Pattern Algorithms (`search_patterns.py`)

- Implemented 4 search pattern generators:
  - **Expanding Square** — spiral outward from datum point
  - **Sector Search** — pie-slice sweeps from datum
  - **Parallel Track** — grid coverage for large areas
  - **Creeping Line Ahead** — systematic sweep from high-probability end
- Built **search pattern recommender** based on area size and probability concentration

### Phase 5: Visualization Module (`visualization.py`)

- Created **interactive Folium map** with CartoDB dark_matter tiles
- Added map layers: last known position marker, projected flight path polyline, glide/fuel range circles, probability heatmap, search pattern overlay with waypoints
- Integrated MeasureControl for distance measurement
- Added LayerControl for toggling map layers

### Phase 6: Streamlit Application (`app.py`)

- Built **sidebar input panel** with all flight parameters
- Integrated all modules: calculations → probability → visualization
- Rendered interactive map via `streamlit.components.v1.html()`
- Displayed search statistics: glide range, fuel range, Monte Carlo point count, recommended pattern, wind speed

### Phase 7: Testing (`test_all.py`)

- Created **comprehensive test suite** with unittest (46 tests):
  - Constants verification
  - Haversine distance (same point, known distance, antipodal points)
  - Destination point (zero distance, cardinal movements)
  - Glide distance (basic, zero altitude, tailwind/headwind effects)
  - Fuel range (basic, zero fuel, zero burn rate, negative values)
  - Wind drift (no wind, crosswind, headwind)
  - Position projection (with/without wind)
  - Monte Carlo (iteration count, tuple format, invalid aircraft)
  - Probability zones (classification, all points classified)
  - Search patterns (all 4 patterns, pattern recommendation)
  - Visualization (map creation, all layer functions)
  - Edge cases (extreme latitude, negative coordinates, zero time)

### Phase 8: Documentation

- Created `README.md` with installation guide, usage instructions, and project overview
- Created `docs/PROJECT_REPORT.md` — comprehensive academic report (400+ lines)
- Created `docs/PRESENTATION_GUIDE.md` — slide-by-slide presentation guide

---

## 📅 February 8, 2026 — Code Review & Testing

- Full code review of all modules
- Ran all 46 unit tests — **all passing**
- Validated core calculation accuracy against published aviation data

---

## 📅 February 12, 2026 — Accuracy Enhancement Phase

### Phase 1: Multi-Layer Atmospheric Wind Model

Added 3 new functions to `calculations.py`:

- **`wind_speed_at_altitude()`** — Power-law wind profile (FAA atmospheric model)
  - Formula: `V(z) = V_ref × (z / z_ref)^α` where α = 0.14
- **`multi_layer_wind_drift()`** — Computes cumulative wind drift through 4 altitude layers:
  - Layer 1: 35,000 → 25,000 ft
  - Layer 2: 25,000 → 15,000 ft
  - Layer 3: 15,000 → 5,000 ft
  - Layer 4: 5,000 → 0 ft
  - Uses midpoint altitude for wind speed at each layer
- **`project_glide_position_multilayer()`** — Projects glide endpoint by combining:
  - Forward glide distance (still-air)
  - Cumulative multi-layer wind drift vector

### Phase 2: Aircraft Database Expansion (`aircraft_specs.json`)

Migrated aircraft data from hardcoded dictionary to **external JSON database** with 11 aircraft:

| Aircraft | Category | Glide Ratio | Best Glide (kts) | Descent Rate (fpm) |
|----------|----------|-------------|-------------------|---------------------|
| Cessna 172S | GA | 9.0 | 68 | 700 |
| Cessna 182 | GA | 10.5 | 75 | 750 |
| Piper PA-28-181 | GA | 10.0 | 76 | 800 |
| Diamond DA40 | GA | 11.0 | 73 | 700 |
| ATR 72-600 | Turboprop | 12.0 | 130 | 1,500 |
| Dash 8 Q400 | Turboprop | 12.5 | 150 | 1,600 |
| Airbus A320-200 | Jet | 16.0 | 230 | 2,500 |
| Boeing 737-800 | Jet | 15.0 | 230 | 2,600 |
| Boeing 777-200ER | Widebody | 17.0 | 260 | 3,000 |
| Airbus A350-900 | Widebody | 18.0 | 255 | 2,800 |
| Airbus A330-300 | Widebody | 16.5 | 240 | 2,800 |

### Phase 3: Integration & Bug Fixes

- **`calculations.py`**: Added `load_aircraft_database()` to load from JSON at module level with hardcoded fallback. Restored missing `project_position()` function.
- **`probability.py`**: 
  - Fixed accuracy bug: was using `cruise_speed` instead of `best_glide_speed` for glide calculations
  - Integrated `project_glide_position_multilayer` into Monte Carlo simulation
  - Made simulation configurable with keyword-only parameters:
    - `controlled_ratio` (default: 0.75) — probability of controlled glide
    - `scatter_min_km` / `scatter_max_km` (default: 0.2–2.0 km)
    - `descent_rate_override` — override for stall/unusual scenarios
    - `heading_spread_deg` (default: 15°) — heading uncertainty per iteration
- **`app.py`**: Wired up `project_glide_position_multilayer`, added descent rate from aircraft data
- **`test_all.py`**: Updated aircraft names to match JSON database, added imports for new functions

### Phase 4: AF447 Historical Validation (`test_validation.py`)

Created validation test against **Air France Flight 447** (June 2009):

**Scenario Configuration:**
- Aircraft: Airbus A330-300 at FL350
- Last known: 2.98°N, 30.59°W
- Actual crash: 3.04°N, 30.83°W
- Scenario overrides: `controlled_ratio=0.0`, `descent_rate=11000 fpm`, `heading_spread=180°`

**Validation Results:**
```
Predicted centroid:  (2.98, -30.61)
Actual crash site:   (3.04, -30.83)
Centroid error:      25.62 km

Coverage:
  Within  5 km:     33 / 5000  (0.7%)
  Within 10 km:    141 / 5000  (2.8%)
  Within 25 km:   1225 / 5000  (24.5%)
  Within 50 km:   3670 / 5000  (73.4%)

In HIGH zone:    True
In MEDIUM zone:  True

VERDICT: EXCELLENT — centroid within 50 km
```

### Summary of Test Results (Feb 12, 2026)

| Test Suite | Tests | Status |
|------------|-------|--------|
| `test_all.py` | 46 | ✅ All Passing |
| `test_validation.py` (AF447) | 1 | ✅ EXCELLENT (25.62 km error) |

---

## 📊 Cumulative Project Metrics

| Metric | Value |
|--------|-------|
| Total Python files | 6 |
| Total test cases | 47 |
| Aircraft in database | 11 |
| Lines of code (approx.) | ~900 |
| AF447 validation error | 25.62 km |
| Dependencies | 5 (streamlit, folium, numpy, scipy, branca) |

---

## 🗂️ Current Project Structure

```
Aircraft-SAR/
├── app.py                  # Streamlit web application
├── calculations.py         # Physics engine + multi-layer wind model
├── probability.py          # Monte Carlo simulation engine
├── search_patterns.py      # SAR pattern generators
├── visualization.py        # Folium map rendering
├── aircraft_specs.json     # Aircraft performance database (11 aircraft)
├── test_all.py             # Unit test suite (46 tests)
├── test_validation.py      # AF447 historical validation
├── requirements.txt        # Python dependencies
├── README.md               # Project overview & usage guide
└── docs/
    ├── PROJECT_REPORT.md   # Academic project report
    ├── PRESENTATION_GUIDE.md  # Presentation slide guide
    └── CHANGELOG.md        # This file
```

---

*Last updated: February 12, 2026*
