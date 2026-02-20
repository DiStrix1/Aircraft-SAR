# ✈️ Aircraft Search and Rescue Intelligence System

A Python-based software tool that calculates and visualizes probable search areas for missing aircraft, reducing search time through scientific analysis of flight physics and Monte Carlo probability simulation.

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![Streamlit](https://img.shields.io/badge/Streamlit-1.28+-red.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)

## 🎯 Problem Statement

When contact with an aircraft is lost, every minute counts. Traditional search operations cover vast areas blindly, wasting critical time and resources. This software uses aviation physics and statistical simulation to predict the most probable crash locations, enabling focused and efficient search operations.

## ✨ Features

- **Glide Range Calculation** - Physics-based estimation of how far an aircraft can glide after engine failure
- **Wind Drift Correction** - Vector mathematics to account for wind effects on flight path
- **Monte Carlo Simulation** - 1200+ iterations to generate probability distribution
- **Interactive Map Visualization** - Folium-based maps with heatmaps and search zones
- **Search Pattern Recommendations** - Optimal SAR patterns based on scenario analysis
- **Multiple Aircraft Support** - Preset data for Cessna 172, Boeing 737/777, Airbus A320, Piper Cherokee

## 🛠️ Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/Aircraft-SAR.git
cd Aircraft-SAR

# Create virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1  # Windows
# source venv/bin/activate   # Linux/Mac

# Install dependencies
pip install -r requirements.txt

# Run the application
streamlit run app.py
```

## 📋 Requirements

```
streamlit>=1.28.0
folium>=0.14.0
numpy>=1.24.0
scipy>=1.10.0
```

## 🚀 Usage

1. **Launch the application**: `streamlit run app.py`
2. **Enter flight parameters** in the sidebar:
   - Aircraft type
   - Last known coordinates (latitude, longitude)
   - Heading and airspeed
   - Altitude at last contact
   - Time since contact lost
   - Wind speed and direction
3. **Click "Calculate"** to generate the search area
4. **View results**: Interactive map with probability zones and statistics

## 📊 Input Parameters

| Parameter | Description | Range |
|-----------|-------------|-------|
| Aircraft Type | Preset aircraft with glide ratios | Dropdown |
| Latitude | Last known latitude | -90° to +90° |
| Longitude | Last known longitude | -180° to +180° |
| Heading | Flight direction | 0° to 360° |
| Airspeed | Speed in knots | 50-600 kts |
| Altitude | Height in feet | 0-45,000 ft |
| Time Since Contact | Minutes since last contact | 1-600 min |
| Wind Speed | Wind speed in knots | 0-100 kts |
| Wind Direction | Wind coming from | 0° to 360° |

## 🔬 Core Algorithms

### Haversine Formula (Great-Circle Distance)
Calculates accurate distance between two points on Earth's curved surface.

### Glide Range Calculation
```
Glide Distance = Altitude × Glide Ratio × Speed Efficiency + Wind Adjustment
```

### Monte Carlo Simulation
Runs 1200 iterations with random variations in heading (±15°), speed (±10%), wind (±30%), and engine failure timing to generate probability distribution.

## 📁 Project Structure

```
Aircraft-SAR/
├── app.py                 # Streamlit web application
├── calculations.py        # Flight physics engine
├── probability.py         # Monte Carlo simulation
├── search_patterns.py     # SAR pattern algorithms
├── visualization.py       # Map generation
├── test_all.py           # Unit tests
├── requirements.txt      # Dependencies
└── README.md            # This file
```

## 📄 License

This project is licensed under the MIT License.

## 👥 Authors

- Your Name - College Project 2026
