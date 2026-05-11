import requests
import json
import os


OWM_API_KEY = os.getenv("OPENWEATHER_API_KEY", "YOUR_API_KEY_HERE")
OWM_URL     = "https://api.openweathermap.org/data/2.5/weather"

# Load weather thresholds for advisory generation
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
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


def _get_coords(district: str):
    """Return (lat, lon) for a district."""
    if district in _DISTRICT_COORDS:
        v = _DISTRICT_COORDS[district]
        return v["lat"], v["lon"]
    if district in _FALLBACK_COORDS:
        return _FALLBACK_COORDS[district]
    # Default to Patna
    return 25.5941, 85.1376


def _generate_advisory(temp: float, humidity: int, description: str) -> str:
    """Generate a simple advisory based on weather conditions."""
    advisories = []

    for alert in _THRESHOLDS.get("general_weather_alerts", []):
        atype = alert["alert_type"]

        if atype == "heatwave" and temp >= alert["threshold_temp_c"]:
            advisories.append("🔥 " + alert["advisory"])

        elif atype == "cold_wave" and temp <= alert["threshold_temp_c"]:
            advisories.append("🥶 " + alert["advisory"])

        elif atype == "fog" and "fog" in description.lower() and humidity >= 90:
            advisories.append("🌫️ " + alert["advisory"])

    if not advisories:
        if temp > 35:
            advisories.append("☀️ गर्मी ज़्यादा है — सुबह या शाम सिंचाई करें।")
        elif temp < 10:
            advisories.append("❄️ ठंड है — गेहूं और आलू के खेत में सिंचाई करें।")
        elif humidity > 80:
            advisories.append("💧 नमी अधिक है — फफूंद रोग का खतरा। फसल की निगरानी करें।")
        else:
            advisories.append("✅ मौसम खेती के लिए अनुकूल है।")

    return " ".join(advisories)


def get_weather(district: str) -> dict:
    """
    Fetch real weather from OpenWeatherMap.
    Returns dict with temp, humidity, description, advisory.
    Falls back to mock data if API key not set or call fails.
    """
    if OWM_API_KEY == "YOUR_API_KEY_HERE":
        return _mock_weather(district)

    lat, lon = _get_coords(district)

    try:
        resp = requests.get(OWM_URL, params={
            "lat": lat,
            "lon": lon,
            "appid": OWM_API_KEY,
            "units": "metric",
            "lang": "hi"
        }, timeout=5)

        data = resp.json()

        if resp.status_code != 200:
            print(f" OWM API error: {data.get('message')}")
            return _mock_weather(district)

        temp        = round(data["main"]["temp"], 1)
        humidity    = data["main"]["humidity"]
        description = data["weather"][0]["description"]
        wind_speed  = data["wind"]["speed"]

        advisory = _generate_advisory(temp, humidity, description)

        return {
            "temp":        temp,
            "humidity":    humidity,
            "description": description,
            "wind_kmh":    round(wind_speed * 3.6, 1),
            "advisory":    advisory,
            "district":    district,
        }

    except requests.exceptions.Timeout:
        print(" Weather API timeout")
        return _mock_weather(district)
    except Exception as e:
        print(f" Weather error: {e}")
        return _mock_weather(district)


def _mock_weather(district: str) -> dict:
    """Fallback mock — used when API key is not set."""
    from datetime import datetime
    month = datetime.now().month

    if 3 <= month <= 6:
        temp, humidity, desc = 38, 45, "साफ आसमान, गर्म"
    elif 7 <= month <= 9:
        temp, humidity, desc = 30, 85, "बादल, बारिश की संभावना"
    elif 10 <= month <= 11:
        temp, humidity, desc = 28, 60, "साफ, सुहाना मौसम"
    else:
        temp, humidity, desc = 14, 70, "ठंडा, कोहरे की संभावना"

    advisory = _generate_advisory(temp, humidity, desc)

    return {
        "temp":        temp,
        "humidity":    humidity,
        "description": desc,
        "wind_kmh":    10,
        "advisory":    advisory,
        "district":    district,
        "note":        "⚠️ Demo data — OPENWEATHER_API_KEY set karein real data ke liye"
    }
