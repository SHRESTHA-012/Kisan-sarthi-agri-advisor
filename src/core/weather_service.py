"""
Weather service — business logic for weather advisories.
Uses src.services.weather_client for all actual HTTP calls.
"""
from src.services.weather_client import fetch_weather_api, get_thresholds


def _generate_advisory(temp: float, humidity: int, description: str) -> str:
    """Generate a farming advisory based on weather conditions."""
    _THRESHOLDS = get_thresholds()
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
    Fetch weather for a district.
    Returns dict with temp, humidity, description, advisory.
    Falls back to seasonal mock data if API is unavailable.
    """
    data = fetch_weather_api(district)

    if data:
        advisory = _generate_advisory(data["temp"], data["humidity"], data["description"])
        return {**data, "advisory": advisory, "district": district}

    return _mock_weather(district)


def _mock_weather(district: str) -> dict:
    """Fallback seasonal mock — used when API key is not set."""
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
        "note":        "⚠️ Demo data — OPENWEATHER_API_KEY set karein real data ke liye",
    }
