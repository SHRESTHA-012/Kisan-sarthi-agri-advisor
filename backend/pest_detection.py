import json
import os
import re
import base64
from pathlib import Path

# ── Load pest data ─────────────────────────────────────────────────────────────
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_PEST_PATH = os.path.join(BASE, "data", "pest_data.json")

with open(_PEST_PATH, "r", encoding="utf-8") as f:
    _PEST_DATA = json.load(f)

_PESTS = _PEST_DATA["pests"]

# ── Keyword map for text-based detection ──────────────────────────────────────
_PEST_KEYWORDS = {
    "P001": [
        "भूरा माहू", "brown plant hopper", "bph", "hopperburn",
        "पत्ती पीली", "गोलाकार सूखना", "honeydew", "चिपचिपा"
    ],
    "P002": [
        "पत्ती लपेटक", "leaf folder", "पत्ती मुड़ना", "पत्ती लिपटना",
        "सफेद धारी", "white streak", "पत्ती ट्यूब"
    ],
    "P003": [
        "तना छेदक", "stem borer", "dead heart", "डेड हार्ट",
        "सफेद बाली", "white ear", "तना सड़न", "तने में छेद"
    ],
    "P004": [
        "माहू", "aphid", "चेपा", "पत्ती मुड़ना", "पीलापन",
        "काली फफूंद", "sooty mold", "हरा कीड़ा"
    ],
    "P005": [
        "दीमक", "termite", "जड़ सड़न", "पौधा मरना",
        "मिट्टी सुरंग", "खोखला तना", "wilting"
    ],
    "P006": [
        "फॉल आर्मीवर्म", "fall armyworm", "faw", "सैनिक कीट",
        "पत्ती में छेद", "मक्का कीड़ा", "frass", "y निशान"
    ],
    "P007": [
        "मक्का तना छेदक", "maize borer", "मक्का में छेद",
        "गुलाबी कीड़ा", "bore hole", "dead heart maize"
    ],
    "P008": [
        "फली छेदक", "pod borer", "फली में छेद",
        "दाना खाना", "pod damage", "फली कीड़ा"
    ],
    "P009": [
        "सरसों माहू", "mustard aphid", "सरसों कीड़ा",
        "पीला कीड़ा", "सरसों पीली", "फूल कीड़ा"
    ],
    "P010": [
        "शीर्ष प्ररोह छेदक", "top shoot borer", "अगरी छेदक",
        "ऊपरी तना", "गन्ना कीड़ा", "dead heart sugarcane"
    ],
    "P011": [
        "आलू कंद शलभ", "potato tuber moth", "आलू में सुरंग",
        "कंद सड़न", "आलू कीड़ा", "tuber damage"
    ],
}

# Crop keyword map to filter by crop
_CROP_KEYWORDS = {
    "C001": ["धान", "rice", "paddy", "dhaan"],
    "C002": ["गेहूं", "wheat", "gehu", "गेहुँ"],
    "C003": ["मक्का", "maize", "makka", "corn"],
    "C004": ["चना", "gram", "chana", "chickpea"],
    "C005": ["सरसों", "mustard", "sarso", "rapeseed"],
    "C006": ["गन्ना", "sugarcane", "ganna"],
    "C007": ["आलू", "potato", "aalu", "aloo"],
}


# ── Format pest advisory in Hindi ─────────────────────────────────────────────
def _format_pest_advisory(pest: dict, score: int = 0) -> str:
    mgmt = pest.get("management", {})
    ident = pest.get("identification", {})
    chemical = mgmt.get("chemical", [])
    cultural = mgmt.get("cultural", [])
    biological = mgmt.get("biological", [])

    lines = [
        f"🐛 *{pest['name_hi']}* ({pest['name_en']})",
        f"📋 लक्षण: {ident.get('symptoms', 'जानकारी उपलब्ध नहीं')}",
        f"🌿 प्रभावित भाग: {ident.get('affected_part', '-')}",
        f"📅 मौसम: {ident.get('season', '-')}",
    ]

    # Economic threshold
    threshold = pest.get("economic_threshold")
    if threshold:
        lines.append(f"⚠️ आर्थिक सीमा: {threshold}")

    # Cultural management
    if cultural:
        lines.append(f"\n🌾 सांस्कृतिक प्रबंधन:")
        for c in cultural[:2]:
            lines.append(f"  • {c}")

    # Biological management
    if biological:
        lines.append(f"\n🦋 जैविक नियंत्रण:")
        for b in biological[:2]:
            lines.append(f"  • {b}")

    # Chemical management
    if chemical:
        lines.append(f"\n🧪 रासायनिक उपचार:")
        for chem in chemical[:2]:
            lines.append(
                f"  • {chem['pesticide']} — {chem['dose']} ({chem['method']})"
            )
            if chem.get("waiting_period_days"):
                lines.append(f"    ⏳ प्रतीक्षा अवधि: {chem['waiting_period_days']} दिन")

    # Weather alert
    alert = pest.get("alert_conditions", {})
    if alert.get("weather_trigger"):
        lines.append(f"\n🌦️ सतर्कता: {alert['weather_trigger']}")

    return "\n".join(lines)


# ══════════════════════════════════════════════════════════════════════════════
# TEXT-BASED DETECTION
# ══════════════════════════════════════════════════════════════════════════════

def detect_pest_from_text(query: str) -> str:
    """
    Detect pest from farmer's text description.
    Returns formatted Hindi advisory or None if no pest detected.
    """
    query_lower = query.lower()

    # Detect crop context
    detected_crops = []
    for crop_id, keywords in _CROP_KEYWORDS.items():
        if any(kw in query_lower for kw in keywords):
            detected_crops.append(crop_id)

    # Score each pest
    scores = {}
    for pest_id, keywords in _PEST_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw.lower() in query_lower)
        if score > 0:
            # Boost score if crop matches
            pest = next((p for p in _PESTS if p["id"] == pest_id), None)
            if pest and detected_crops:
                if any(c in pest.get("affects_crops", []) for c in detected_crops):
                    score += 2
            scores[pest_id] = score

    if not scores:
        return None

    # Get best match
    best_id = max(scores, key=scores.get)
    best_score = scores[best_id]

    if best_score == 0:
        return None

    pest = next((p for p in _PESTS if p["id"] == best_id), None)
    if not pest:
        return None

    return _format_pest_advisory(pest, best_score)


def get_all_pests_for_crop(crop_query: str) -> str:
    """Return all known pests for a given crop."""
    crop_query_lower = crop_query.lower()

    matched_crop_ids = []
    for crop_id, keywords in _CROP_KEYWORDS.items():
        if any(kw in crop_query_lower for kw in keywords):
            matched_crop_ids.append(crop_id)

    if not matched_crop_ids:
        return "किसान भाई, कृपया फसल का नाम स्पष्ट बताएं (धान, गेहूं, मक्का आदि)।"

    matching_pests = [
        p for p in _PESTS
        if any(c in p.get("affects_crops", []) for c in matched_crop_ids)
    ]

    if not matching_pests:
        return "इस फसल के लिए कोई कीट जानकारी उपलब्ध नहीं है।"

    lines = [f"🌾 इस फसल के प्रमुख कीट:\n"]
    for p in matching_pests:
        lines.append(f"• {p['name_hi']} ({p['name_en']}) — {p['identification'].get('symptoms','')[:60]}...")

    lines.append("\nकिसी एक कीट की विस्तृत जानकारी के लिए उसका नाम बताएं।")
    return "\n".join(lines)


# ══════════════════════════════════════════════════════════════════════════════
# IMAGE-BASED DETECTION (via Ollama Vision)
# ══════════════════════════════════════════════════════════════════════════════

def _encode_image(image_path: str) -> str:
    """Encode image to base64 string."""
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def _build_pest_list_for_prompt() -> str:
    """Build a compact pest reference list for the vision prompt."""
    lines = []
    for p in _PESTS:
        symptoms = p["identification"].get("symptoms", "")[:80]
        lines.append(f"- {p['name_en']} ({p['name_hi']}): {symptoms}")
    return "\n".join(lines)


def detect_pest_from_image(image_path: str) -> str:
    """
    Detect pest/disease from an uploaded image using Ollama vision model.
    Falls back to llava if available, else returns guidance message.

    Args:
        image_path: Path to the uploaded image file

    Returns:
        Hindi advisory string
    """
    if not os.path.exists(image_path):
        return "❌ छवि फ़ाइल नहीं मिली। कृपया दोबारा अपलोड करें।"

    # Check file format
    ext = Path(image_path).suffix.lower()
    supported = [".jpg", ".jpeg", ".png", ".webp"]
    if ext not in supported:
        return f"❌ असमर्थित फ़ाइल प्रारूप। कृपया JPG, PNG, या WEBP फ़ाइल भेजें।"

    try:
        import ollama

        # Encode image
        image_b64 = _encode_image(image_path)
        pest_list = _build_pest_list_for_prompt()

        prompt = f"""You are an expert agricultural pest and disease identifier for Bihar, India.

Analyze this image of a crop plant and identify:
1. The pest or disease visible
2. Which crop is affected
3. Severity (mild/moderate/severe)

Known Bihar pests for reference:
{pest_list}

Respond ONLY in this exact format:
PEST: [pest name in Hindi and English]
CROP: [crop name]
SEVERITY: [mild/moderate/severe]
SYMPTOMS: [what you see in 1-2 sentences]
CONFIDENCE: [high/medium/low]"""

        response = ollama.chat(
            model="llava",  # Vision model
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                    "images": [image_b64]
                }
            ],
            options={"temperature": 0.2}
        )

        raw_result = response["message"]["content"]
        return _parse_vision_response(raw_result, image_path)

    except Exception as e:
        error_str = str(e).lower()

        if "llava" in error_str or "model" in error_str or "not found" in error_str:
            return _image_fallback_response()
        else:
            print(f"Vision error: {e}")
            return "❌ छवि विश्लेषण में समस्या हुई। कृपया लक्षण टेक्स्ट में बताएं।"


def _parse_vision_response(raw: str, image_path: str) -> str:
    """Parse vision model output and match to known pests."""
    lines = raw.strip().split("\n")
    parsed = {}

    for line in lines:
        if ":" in line:
            key, _, val = line.partition(":")
            parsed[key.strip().upper()] = val.strip()

    pest_name = parsed.get("PEST", "").lower()
    severity  = parsed.get("SEVERITY", "moderate")
    symptoms  = parsed.get("SYMPTOMS", "")
    crop      = parsed.get("CROP", "")
    confidence = parsed.get("CONFIDENCE", "medium")

    # Try to match detected pest to our database
    matched_pest = None
    for pest in _PESTS:
        if (pest["name_en"].lower() in pest_name or
            pest["name_hi"] in pest_name or
            any(kw in pest_name for kw in _PEST_KEYWORDS.get(pest["id"], []))):
            matched_pest = pest
            break

    # Severity emoji
    severity_map = {
        "mild": "🟡 हल्का",
        "moderate": "🟠 मध्यम",
        "severe": "🔴 गंभीर"
    }
    severity_hi = severity_map.get(severity.lower(), "🟠 मध्यम")

    confidence_map = {
        "high": "✅ उच्च",
        "medium": "⚠️ मध्यम",
        "low": "❓ कम"
    }
    confidence_hi = confidence_map.get(confidence.lower(), "⚠️ मध्यम")

    lines_out = [
        f"📸 *छवि विश्लेषण परिणाम*",
        f"🎯 विश्वास स्तर: {confidence_hi}",
        f"🌿 फसल: {crop}",
        f"⚡ गंभीरता: {severity_hi}",
        f"👁️ दिखे लक्षण: {symptoms}",
        ""
    ]

    if matched_pest:
        lines_out.append(_format_pest_advisory(matched_pest))
    else:
        lines_out.append(
            f"🐛 पहचाना गया: {parsed.get('PEST', 'अज्ञात कीट')}\n"
            f"किसान भाई, कृपया नजदीकी KVK केंद्र से संपर्क करें या "
            f"लक्षण विस्तार से बताएं।"
        )

    return "\n".join(lines_out)


def _image_fallback_response() -> str:
    """Response when llava vision model is not installed."""
    return """📸 छवि विश्लेषण के लिए LLaVA मॉडल आवश्यक है।

इंस्टॉल करने के लिए टर्मिनल में चलाएं:
`ollama pull llava`

अभी के लिए, कृपया लक्षण टेक्स्ट में बताएं, जैसे:
• "धान की पत्ती पीली हो रही है"
• "तने में छेद दिख रहा है"
• "पत्ती मुड़ गई है"

मैं टेक्स्ट से भी सही पहचान कर सकता हूं! 🌾"""


# ══════════════════════════════════════════════════════════════════════════════
# UNIFIED ENTRY POINT (called from chatbot.py)
# ══════════════════════════════════════════════════════════════════════════════

def analyze_pest(query: str = None, image_path: str = None) -> str:
    """
    Main entry point for pest detection.

    Args:
        query: Farmer's text description of symptoms
        image_path: Path to uploaded pest image (optional)

    Returns:
        Hindi advisory string
    """
    # Image takes priority if provided
    if image_path:
        image_result = detect_pest_from_image(image_path)

        # Also run text detection if query provided alongside image
        if query:
            text_result = detect_pest_from_text(query)
            if text_result:
                return image_result + "\n\n---\n💬 *टेक्स्ट विश्लेषण:*\n" + text_result

        return image_result

    # Text-only detection
    if query:
        result = detect_pest_from_text(query)
        if result:
            return result

        # Check if asking about all pests for a crop
        pest_query_keywords = ["कीट", "रोग", "बीमारी", "pest", "disease", "insect", "problem"]
        if any(kw in query.lower() for kw in pest_query_keywords):
            return get_all_pests_for_crop(query)

        return None  # Let chatbot.py handle via RAG if no pest detected

    return None


# ── Quick test ─────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    # Test text detection
    test_queries = [
        "धान में भूरा माहू का क्या इलाज है?",
        "मेरे गेहूं की पत्ती मुड़ रही है और पीली हो रही है",
        "मक्का में कौन कौन से कीट लगते हैं?",
        "तना छेदक से कैसे बचाएं",
    ]

    print("=" * 60)
    print("TEXT-BASED PEST DETECTION TEST")
    print("=" * 60)

    for q in test_queries:
        print(f"\n📝 Query: {q}")
        result = analyze_pest(query=q)
        if result:
            print(result[:300] + "..." if len(result) > 300 else result)
        else:
            print("❌ No pest detected")
        print("-" * 40)
