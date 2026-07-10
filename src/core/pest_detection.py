import json
import os
import base64
from pathlib import Path

from src.services.llm_service import vision_chat

# ── Load pest data ─────────────────────────────────────────────────────────────
BASE       = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_PEST_PATH = os.path.join(BASE, "data", "pest_data.json")

with open(_PEST_PATH, "r", encoding="utf-8") as f:
    _PEST_DATA = json.load(f)

_PESTS = _PEST_DATA["pests"]

# ── Keyword maps ───────────────────────────────────────────────────────────────
_PEST_KEYWORDS = {
    "P001": ["भूरा माहू", "brown plant hopper", "bph", "hopperburn", "पत्ती पीली", "गोलाकार सूखना", "honeydew", "चिपचिपा"],
    "P002": ["पत्ती लपेटक", "leaf folder", "पत्ती मुड़ना", "पत्ती लिपटना", "सफेद धारी", "white streak", "पत्ती ट्यूब"],
    "P003": ["तना छेदक", "stem borer", "dead heart", "डेड हार्ट", "सफेद बाली", "white ear", "तना सड़न", "तने में छेद"],
    "P004": ["माहू", "aphid", "चेपा", "पत्ती मुड़ना", "पीलापन", "काली फफूंद", "sooty mold", "हरा कीड़ा"],
    "P005": ["दीमक", "termite", "जड़ सड़न", "पौधा मरना", "मिट्टी सुरंग", "खोखला तना", "wilting"],
    "P006": ["फॉल आर्मीवर्म", "fall armyworm", "faw", "सैनिक कीट", "पत्ती में छेद", "मक्का कीड़ा", "frass", "y निशान"],
    "P007": ["मक्का तना छेदक", "maize borer", "मक्का में छेद", "गुलाबी कीड़ा", "bore hole", "dead heart maize"],
    "P008": ["फली छेदक", "pod borer", "फली में छेद", "दाना खाना", "pod damage", "फली कीड़ा"],
    "P009": ["सरसों माहू", "mustard aphid", "सरसों कीड़ा", "पीला कीड़ा", "सरसों पीली", "फूल कीड़ा"],
    "P010": ["शीर्ष प्ररोह छेदक", "top shoot borer", "अगरी छेदक", "ऊपरी तना", "गन्ना कीड़ा", "dead heart sugarcane"],
    "P011": ["आलू कंद शलभ", "potato tuber moth", "आलू में सुरंग", "कंद सड़न", "आलू कीड़ा", "tuber damage"],
}

_CROP_KEYWORDS = {
    "C001": ["धान", "rice", "paddy", "dhaan"],
    "C002": ["गेहूं", "wheat", "gehu", "गेहुँ"],
    "C003": ["मक्का", "maize", "makka", "corn"],
    "C004": ["चना", "gram", "chana", "chickpea"],
    "C005": ["सरसों", "mustard", "sarso", "rapeseed"],
    "C006": ["गन्ना", "sugarcane", "ganna"],
    "C007": ["आलू", "potato", "aalu", "aloo"],
}


# ── Formatter ──────────────────────────────────────────────────────────────────

def _format_pest_advisory(pest: dict, score: int = 0) -> str:
    mgmt       = pest.get("management", {})
    ident      = pest.get("identification", {})
    chemical   = mgmt.get("chemical", [])
    cultural   = mgmt.get("cultural", [])
    biological = mgmt.get("biological", [])

    lines = [
        f"🐛 *{pest['name_hi']}* ({pest['name_en']})",
        f"📋 लक्षण: {ident.get('symptoms', 'जानकारी उपलब्ध नहीं')}",
        f"🌿 प्रभावित भाग: {ident.get('affected_part', '-')}",
        f"📅 मौसम: {ident.get('season', '-')}",
    ]
    if pest.get("economic_threshold"):
        lines.append(f"⚠️ आर्थिक सीमा: {pest['economic_threshold']}")
    if cultural:
        lines.append("\n🌾 सांस्कृतिक प्रबंधन:")
        for c in cultural[:2]:
            lines.append(f"  • {c}")
    if biological:
        lines.append("\n🦋 जैविक नियंत्रण:")
        for b in biological[:2]:
            lines.append(f"  • {b}")
    if chemical:
        lines.append("\n🧪 रासायनिक उपचार:")
        for chem in chemical[:2]:
            lines.append(f"  • {chem['pesticide']} — {chem['dose']} ({chem['method']})")
            if chem.get("waiting_period_days"):
                lines.append(f"    ⏳ प्रतीक्षा अवधि: {chem['waiting_period_days']} दिन")
    alert = pest.get("alert_conditions", {})
    if alert.get("weather_trigger"):
        lines.append(f"\n🌦️ सतर्कता: {alert['weather_trigger']}")

    return "\n".join(lines)


# ── Text-based detection ───────────────────────────────────────────────────────

def detect_pest_from_text(query: str) -> str | None:
    query_lower = query.lower()

    detected_crops = [
        crop_id for crop_id, keywords in _CROP_KEYWORDS.items()
        if any(kw in query_lower for kw in keywords)
    ]

    scores = {}
    for pest_id, keywords in _PEST_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw.lower() in query_lower)
        if score > 0:
            pest = next((p for p in _PESTS if p["id"] == pest_id), None)
            if pest and detected_crops:
                if any(c in pest.get("affects_crops", []) for c in detected_crops):
                    score += 2
            scores[pest_id] = score

    if not scores:
        return None

    best_id    = max(scores, key=scores.get)
    best_score = scores[best_id]
    if best_score == 0:
        return None

    pest = next((p for p in _PESTS if p["id"] == best_id), None)
    return _format_pest_advisory(pest, best_score) if pest else None


def get_all_pests_for_crop(crop_query: str) -> str:
    crop_query_lower = crop_query.lower()
    matched_crop_ids = [
        crop_id for crop_id, keywords in _CROP_KEYWORDS.items()
        if any(kw in crop_query_lower for kw in keywords)
    ]
    if not matched_crop_ids:
        return "किसान भाई, कृपया फसल का नाम स्पष्ट बताएं (धान, गेहूं, मक्का आदि)।"

    matching_pests = [
        p for p in _PESTS
        if any(c in p.get("affects_crops", []) for c in matched_crop_ids)
    ]
    if not matching_pests:
        return "इस फसल के लिए कोई कीट जानकारी उपलब्ध नहीं है।"

    lines = ["🌾 इस फसल के प्रमुख कीट:\n"]
    for p in matching_pests:
        lines.append(f"• {p['name_hi']} ({p['name_en']}) — {p['identification'].get('symptoms','')[:60]}...")
    lines.append("\nकिसी एक कीट की विस्तृत जानकारी के लिए उसका नाम बताएं।")
    return "\n".join(lines)


# ── Image-based detection ──────────────────────────────────────────────────────

def _encode_image(image_path: str) -> str:
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def _build_pest_list_for_prompt() -> str:
    return "\n".join(
        f"- {p['name_en']} ({p['name_hi']}): {p['identification'].get('symptoms', '')[:80]}"
        for p in _PESTS
    )


def detect_pest_from_image(image_path: str) -> str:
    if not os.path.exists(image_path):
        return "❌ छवि फ़ाइल नहीं मिली। कृपया दोबारा अपलोड करें।"

    ext = Path(image_path).suffix.lower()
    if ext not in [".jpg", ".jpeg", ".png", ".webp"]:
        return "❌ असमर्थित फ़ाइल प्रारूप। कृपया JPG, PNG, या WEBP फ़ाइल भेजें।"

    try:
        image_b64 = _encode_image(image_path)
        pest_list = _build_pest_list_for_prompt()

        prompt = f"""You are an expert agricultural pest and disease identifier for Bihar, India.
Analyze this image and identify:
1. The pest or disease visible
2. Which crop is affected
3. Severity (mild/moderate/severe)

Known Bihar pests:
{pest_list}

Respond ONLY in this exact format:
PEST: [pest name in Hindi and English]
CROP: [crop name]
SEVERITY: [mild/moderate/severe]
SYMPTOMS: [what you see in 1-2 sentences]
CONFIDENCE: [high/medium/low]"""

        raw_result = vision_chat(prompt, image_b64)
        return _parse_vision_response(raw_result)

    except Exception as e:
        error_str = str(e).lower()
        if "llava" in error_str or "model" in error_str or "not found" in error_str:
            return _image_fallback_response()
        return "❌ छवि विश्लेषण में समस्या हुई। कृपया लक्षण टेक्स्ट में बताएं।"


def _parse_vision_response(raw: str) -> str:
    parsed = {}
    for line in raw.strip().split("\n"):
        if ":" in line:
            key, _, val = line.partition(":")
            parsed[key.strip().upper()] = val.strip()

    pest_name  = parsed.get("PEST", "").lower()
    severity   = parsed.get("SEVERITY", "moderate")
    symptoms   = parsed.get("SYMPTOMS", "")
    crop       = parsed.get("CROP", "")
    confidence = parsed.get("CONFIDENCE", "medium")

    matched_pest = next((
        p for p in _PESTS
        if p["name_en"].lower() in pest_name or p["name_hi"] in pest_name
        or any(kw in pest_name for kw in _PEST_KEYWORDS.get(p["id"], []))
    ), None)

    severity_hi   = {"mild": "🟡 हल्का", "moderate": "🟠 मध्यम", "severe": "🔴 गंभीर"}.get(severity.lower(), "🟠 मध्यम")
    confidence_hi = {"high": "✅ उच्च", "medium": "⚠️ मध्यम", "low": "❓ कम"}.get(confidence.lower(), "⚠️ मध्यम")

    lines_out = [
        "📸 *छवि विश्लेषण परिणाम*",
        f"🎯 विश्वास स्तर: {confidence_hi}",
        f"🌿 फसल: {crop}",
        f"⚡ गंभीरता: {severity_hi}",
        f"👁️ दिखे लक्षण: {symptoms}",
        "",
    ]

    if matched_pest:
        lines_out.append(_format_pest_advisory(matched_pest))
    else:
        lines_out.append(
            f"🐛 पहचाना गया: {parsed.get('PEST', 'अज्ञात कीट')}\n"
            "किसान भाई, कृपया नजदीकी KVK केंद्र से संपर्क करें।"
        )

    return "\n".join(lines_out)


def _image_fallback_response() -> str:
    return """📸 छवि विश्लेषण के लिए LLaVA मॉडल आवश्यक है।

इंस्टॉल करने के लिए: `ollama pull llava`

अभी के लिए लक्षण टेक्स्ट में बताएं:
• "धान की पत्ती पीली हो रही है"
• "तने में छेद दिख रहा है" 🌾"""


# ── Unified entry point ────────────────────────────────────────────────────────

def analyze_pest(query: str = None, image_path: str = None) -> str | None:
    if image_path:
        image_result = detect_pest_from_image(image_path)
        if query:
            text_result = detect_pest_from_text(query)
            if text_result:
                return image_result + "\n\n---\n💬 *टेक्स्ट विश्लेषण:*\n" + text_result
        return image_result

    if query:
        result = detect_pest_from_text(query)
        if result:
            return result
        pest_query_keywords = ["कीट", "रोग", "बीमारी", "pest", "disease", "insect", "problem"]
        if any(kw in query.lower() for kw in pest_query_keywords):
            return get_all_pests_for_crop(query)

    return None
