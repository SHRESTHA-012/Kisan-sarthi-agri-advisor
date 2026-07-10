"""
OpenWeatherMap API client.
All HTTP calls to OWM are isolated here — swap the provider without
touching any core business logic.
"""
import requests
import json
import os

OWM_API_KEY = os.getenv("OPENWEATHER_API_KEY", "YOUR_API_KEY_HERE")
OWM_URL     = "https://api.openweathermap.org/data/2.5/weather"

# Load weather thresholds for advisory generation
BASE      = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_THR_PATH = os.path.join(BASE, "data", "weather_thresholds.json")

with open(_THR_PATH, "r", encoding="utf-8") as f:
    _THRESHOLDS = json.load(f)

# District → coordinates map (from weather_thresholds.json)
_DISTRICT_COORDS = {
    d: v for d, v in _THRESHOLDS.get("imd_district_stations", {}).items()
}

# Fallback coordinates for common Bihar districts not in IMD list
_FALLBACK_COORDS = {
    "Patna":       (25.5941, 85.1376),
    "Gaya":        (24.7914, 85.0002),
    "Muzaffarpur": (26.1209, 85.3647),
    "Bhagalpur":   (25.2425, 87.0169),
    "Darbhanga":   (26.1542, 85.9000),
    "Purnia":      (25.7771, 87.4753),
    "Nalanda":     (25.1369, 85.4420),
    "Rohtas":      (24.9937, 83.8375),
    "Vaishali":    (25.6930, 85.2011),
    "Champaran":   (26.6526, 84.9298),
    "Sitamarhi":   (26.5912, 85.4896),
    "Samastipur":  (25.8693, 85.7791),
    "Begusarai":   (25.4182, 86.1272),
    "Saran":       (25.9230, 84.7478),
    "Siwan":       (26.2203, 84.3556),
}


def get_coords(district: str):
    """Return (lat, lon) for a district."""
    if district in _DISTRICT_COORDS:
        v = _DISTRICT_COORDS[district]
        return v["lat"], v["lon"]
    if district in _FALLBACK_COORDS:
        return _FALLBACK_COORDS[district]
    return 25.5941, 85.1376  # Default to Patna


def fetch_weather_api(district: str) -> dict | None:
    """
    Call OpenWeatherMap API. Returns raw data dict or None on failure.
    """
    if OWM_API_KEY == "YOUR_API_KEY_HERE":
        return None

    lat, lon = get_coords(district)
    try:
        resp = requests.get(OWM_URL, params={
            "lat": lat, "lon": lon,
            "appid": OWM_API_KEY,
            "units": "metric",
            "lang": "hi"
        }, timeout=5)

        if resp.status_code != 200:
            return None

        data = resp.json()
        return {
            "temp":        round(data["main"]["temp"], 1),
            "humidity":    data["main"]["humidity"],
            "description": data["weather"][0]["description"],
            "wind_kmh":    round(data["wind"]["speed"] * 3.6, 1),
        }
    except Exception:
        return None


def get_thresholds() -> dict:
    """Expose loaded thresholds for advisory logic."""
    return _THRESHOLDS
