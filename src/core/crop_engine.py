import json
import os

BASE       = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_DATA_PATH = os.path.join(BASE, "data", "bihar_crops.json")

with open(_DATA_PATH, "r", encoding="utf-8") as f:
    _CROPS = json.load(f)["crops"]

_CROP_BY_ID = {c["id"]: c for c in _CROPS}


def get_crops_by_season(season: str) -> list[str]:
    """Return list of crop names for a given season (Kharif/Rabi/Zaid)."""
    season_lower = season.lower()
    return [
        c["name_hi"] + f" ({c['name_en']})"
        for c in _CROPS
        if c["season"].lower() == season_lower
    ]


def get_crops_by_district(district: str, season: str = None) -> list[str]:
    """Return crops suitable for a given district, optionally filtered by season."""
    results = []
    for c in _CROPS:
        if district in c.get("districts_suitable", []):
            if season is None or c["season"].lower() == season.lower():
                results.append(c["name_hi"] + f" ({c['name_en']})")
    return results if results else get_crops_by_season(season or "kharif")


def get_crop_advice(crop_id: str) -> str:
    """Return a formatted advisory string for a specific crop."""
    crop = _CROP_BY_ID.get(crop_id)
    if not crop:
        return "किसान भाई, इस फसल की जानकारी उपलब्ध नहीं है।"

    sowing = crop.get("sowing", {})
    soil   = crop.get("soil", {})
    fert   = crop.get("fertilizer", {})
    basal  = fert.get("basal", {})

    lines = [f"🌾 {crop['name_hi']} ({crop['name_en']}) — {crop['season'].upper()} फसल\n"]

    varieties = crop.get("popular_varieties", [])[:2]
    if varieties:
        lines.append("📌 अच्छी किस्में:")
        for v in varieties:
            lines.append(f"  • {v['variety']} — {v.get('features','')}, {v.get('duration_days', v.get('duration_months',''))} दिन")

    period = sowing.get("optimal_period") or f"महीना: {sowing.get('nursery_month', '')}"
    lines.append(f"\n🗓️ बुवाई का समय: {period}")

    seed_rate = sowing.get("seed_rate_kg_per_acre") or sowing.get("seed_rate_tons_per_acre")
    if seed_rate:
        unit = "kg" if "kg" in str(sowing) else "ton"
        lines.append(f"🌱 बीज दर: {seed_rate} {unit} प्रति एकड़")

    lines.append(f"🪴 मिट्टी: {', '.join(soil.get('type', []))}, pH {soil.get('ph_range', [])}")

    fert_parts = []
    if basal.get("DAP_kg_per_acre"):
        fert_parts.append(f"DAP {basal['DAP_kg_per_acre']} kg")
    if basal.get("MOP_kg_per_acre"):
        fert_parts.append(f"MOP {basal['MOP_kg_per_acre']} kg")
    if fert_parts:
        lines.append(f"🧪 बेसल खाद: {', '.join(fert_parts)} प्रति एकड़")

    top = fert.get("top_dressing", [])
    if top:
        lines.append(f"   टॉप ड्रेसिंग: यूरिया {top[0].get('urea_kg_per_acre', '')} kg — {top[0].get('stage', '')}")

    msp = crop.get("msp_2024_25_per_qtl")
    if msp:
        lines.append(f"\n💰 MSP 2024-25: ₹{msp} प्रति क्विंटल")

    return "\n".join(lines)


# Legacy alias — keeps advisory_engine.py and chatbot.py working
def get_crops(district: str, season: str) -> list[str]:
    return get_crops_by_district(district, season)
