import json
import os
from backend.chatbot import generate_response
from backend.crop_engine import get_crop_advice, get_crops_by_season
from backend.weather_service import get_weather

# ── Load JSON data files once at startup ──────────────────────────────────────
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def _load(filename):
    path = os.path.join(BASE, "data", filename)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

CROPS_DATA     = _load("bihar_crops.json")
PEST_DATA      = _load("pest_data.json")
DISEASE_DATA   = _load("diseases_data.json")
SCHEMES_DATA   = _load("govt_schemes.json")
MSP_DATA       = _load("msp_prices.json")
WEATHER_THR    = _load("weather_thresholds.json")

# ── Intent keywords ────────────────────────────────────────────────────────────
INTENT_MAP = {
    "weather":  ["मौसम", "बारिश", "तापमान", "weather", "mausam", "barish", "garmi", "sardi"],
    "pest":     ["कीड़ा", "कीट", "keeda", "pest", "माहू", "mahu", "तना", "borer", "लपेटक"],
    "disease":  ["रोग", "बीमारी", "rog", "bimari", "झुलसा", "blast", "rust", "blight"],
    "scheme":   ["योजना", "yojana", "सरकार", "sarkar", "scheme", "subsidy", "किसान सम्मान", "pm kisan", "बीमा"],
    "msp":      ["msp", "भाव", "bhav", "price", "कीमत", "keemat", "समर्थन मूल्य", "mandi"],
    "crop":     ["फसल", "fasal", "crop", "खेती", "kheti", "बोना", "bona", "उगाना", "variety", "किस्म"],
    "fertilizer":["खाद", "khad", "urea", "dap", "fertilizer", "उर्वरक", "zinc", "पोषण"],
}

def detect_intent(text: str) -> str:
    text_lower = text.lower()
    for intent, keywords in INTENT_MAP.items():
        for kw in keywords:
            if kw in text_lower:
                return intent
    return "general"


def detect_crop(text: str):
    """Return crop_id if a crop name is mentioned in query."""
    crop_name_map = {
        "धान": "C001", "paddy": "C001", "rice": "C001", "chawal": "C001", "dhan": "C001",
        "गेहूं": "C002", "gehun": "C002", "wheat": "C002",
        "मक्का": "C003", "maize": "C003", "makka": "C003", "corn": "C003",
        "मसूर": "C004", "masur": "C004", "lentil": "C004",
        "सरसों": "C005", "sarson": "C005", "mustard": "C005",
        "गन्ना": "C006", "ganna": "C006", "sugarcane": "C006",
        "आलू": "C007", "aalu": "C007", "potato": "C007",
        "लीची": "C008", "litchi": "C008",
    }
    text_lower = text.lower()
    for name, crop_id in crop_name_map.items():
        if name in text_lower:
            return crop_id
    return None


# ── Intent handlers ────────────────────────────────────────────────────────────

def handle_weather(district: str, user_input: str) -> str:
    weather = get_weather(district)
    return (
        f"किसान भाई, {district} का आज का मौसम:\n"
        f"🌡️ तापमान: {weather.get('temp', 'N/A')}°C\n"
        f"💧 नमी: {weather.get('humidity', 'N/A')}%\n"
        f"🌤️ स्थिति: {weather.get('description', 'N/A')}\n\n"
        f"{weather.get('advisory', '')}"
    )


def handle_msp(user_input: str) -> str:
    crop_id = detect_crop(user_input)
    results = []

    # Search in both kharif and rabi
    for season_key in ["kharif", "rabi"]:
        for crop in MSP_DATA["msp_history"][season_key]["crops"]:
            if crop_id and crop.get("crop_id") != crop_id:
                continue
            name = crop["crop_name_hi"]
            msp = crop["msp"].get("2025_26") or crop["msp"].get("2024_25")
            results.append(f"• {name}: ₹{msp} प्रति क्विंटल")

    if results:
        return "किसान भाई, MSP (न्यूनतम समर्थन मूल्य) 2025-26:\n" + "\n".join(results[:6])
    return "किसान भाई, MSP जानकारी के लिए dbtagriculture.bihar.gov.in देखें।"


def handle_scheme(user_input: str) -> str:
    schemes = SCHEMES_DATA["schemes"]
    # Pick top 2 most relevant schemes based on keyword match
    relevant = []
    for s in schemes:
        if any(kw in user_input.lower() for kw in [
            s["name_en"].lower(), s.get("name_hi", "").lower(),
            s["id"].lower()
        ]):
            relevant.append(s)

    if not relevant:
        # Return top 3 most important schemes by default
        relevant = schemes[:3]

    out = ["किसान भाई, इन सरकारी योजनाओं का लाभ उठाएं:\n"]
    for s in relevant[:2]:
        out.append(f"📌 {s['name_hi']}")
        out.append(f"   {s['description'][:120]}...")
        benefit = s.get("benefit", {})
        if "amount_per_year_inr" in benefit:
            out.append(f"   💰 लाभ: ₹{benefit['amount_per_year_inr']} प्रति वर्ष")
        apply_info = s.get("how_to_apply", {})
        if "online" in apply_info:
            out.append(f"   🌐 {apply_info['online']}")
        helpline = s.get("helpline") or SCHEMES_DATA.get("quick_helplines", {}).get("bihar_agriculture_helpline")
        if helpline:
            out.append(f"   📞 {helpline}")
        out.append("")

    return "\n".join(out)


def handle_pest(user_input: str, crop_id: str = None) -> str:
    pests = PEST_DATA["pests"]
    matched = []

    for pest in pests:
        name_match = (
            pest["name_hi"].lower() in user_input.lower() or
            pest["name_en"].lower() in user_input.lower()
        )
        crop_match = crop_id and crop_id in pest.get("affects_crops", [])
        if name_match or crop_match:
            matched.append(pest)

    if not matched:
        # Fall through to RAG
        return None

    pest = matched[0]
    chemicals = pest["management"].get("chemical", [])
    cultural = pest["management"].get("cultural", [])[:2]

    out = [
        f"किसान भाई, यह {pest['name_hi']} ({pest['name_en']}) है।\n",
        f"🔍 पहचान: {pest['identification']['symptoms'][:120]}",
        f"\n🌿 घरेलू उपाय:",
    ]
    for c in cultural:
        out.append(f"  • {c}")

    if chemicals:
        chem = chemicals[0]
        out.append(f"\n💊 दवाई: {chem['pesticide']}")
        out.append(f"   मात्रा: {chem['dose']}")
        out.append(f"   तरीका: {chem['method']}")

    return "\n".join(out)


def handle_disease(user_input: str, crop_id: str = None) -> str:
    diseases = DISEASE_DATA["diseases"]
    matched = []

    for d in diseases:
        name_match = (
            d["name_hi"].lower() in user_input.lower() or
            d["name_en"].lower() in user_input.lower()
        )
        crop_match = crop_id and crop_id in d.get("affects_crops", [])
        if name_match or crop_match:
            matched.append(d)

    if not matched:
        return None

    disease = matched[0]
    chemicals = disease["management"].get("chemical", [])
    cultural = disease["management"].get("cultural", [])[:2]

    out = [
        f"किसान भाई, यह {disease['name_hi']} है।\n",
        f"🔍 लक्षण: {disease['identification']['symptoms'][:150]}",
        f"\n🌿 सांस्कृतिक उपाय:",
    ]
    for c in cultural:
        out.append(f"  • {c}")

    if chemicals:
        chem = chemicals[0]
        out.append(f"\n💊 फफूंदनाशक: {chem['fungicide']}")
        out.append(f"   मात्रा: {chem['dose']}")
        out.append(f"   तरीका: {chem['method']}")

    return "\n".join(out)


def handle_crop(user_input: str, district: str, crop_id: str = None) -> str:
    if crop_id:
        return get_crop_advice(crop_id)
    # No specific crop → suggest by season
    season = _detect_season()
    crops = get_crops_by_season(season)
    return (
        f"किसान भाई, {district} में अभी {season} मौसम के लिए ये फसलें उगाई जा सकती हैं:\n"
        + "\n".join([f"  • {c}" for c in crops])
    )


def _detect_season() -> str:
    from datetime import datetime
    month = datetime.now().month
    if 6 <= month <= 10:
        return "Kharif"
    elif 11 <= month or month <= 3:
        return "Rabi"
    else:
        return "Zaid"


# ── Main entry point ───────────────────────────────────────────────────────────

def process_query(user_input: str, session: dict) -> str:
    user_input = user_input.strip()

    # ── STEP 1: Onboarding — ask district first ──
    if not session.get("district"):
        session["district"] = user_input
        return (
            f"धन्यवाद किसान भाई! {user_input} जिले के लिए आपका स्वागत है। 🌾\n"
            "अब आप कोई भी सवाल पूछ सकते हैं:\n"
            "• फसल की जानकारी\n"
            "• मौसम\n"
            "• कीड़े / बीमारी\n"
            "• MSP भाव\n"
            "• सरकारी योजनाएं"
        )

    district = session["district"]

    # ── STEP 2: Detect intent & crop ──
    intent   = detect_intent(user_input)
    crop_id  = detect_crop(user_input)

    # ── STEP 3: Route to handler ──
    if intent == "weather":
        return handle_weather(district, user_input)

    if intent == "msp":
        return handle_msp(user_input)

    if intent == "scheme":
        return handle_scheme(user_input)

    if intent == "pest":
        result = handle_pest(user_input, crop_id)
        if result:
            return result
        # Fall through to RAG if no direct match

    if intent == "disease":
        result = handle_disease(user_input, crop_id)
        if result:
            return result

    if intent == "crop":
        return handle_crop(user_input, district, crop_id)

    # ── STEP 4: Default → RAG + LLM ──
    return generate_response(user_input, session)
