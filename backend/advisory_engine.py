# from backend.chatbot import generate_response
# from backend.crop_engine import get_crops
# from backend.weather_service import get_weather


# def process_query(user_input, session):
    
#     user_input = user_input.strip()

#     # ✅ STEP 1: Onboarding (ask district first)
#     if session.get("district") is None:
#         session["district"] = user_input
#         return "धन्यवाद किसान भाई। अब आप अपना सवाल पूछ सकते हैं।"

#     district = session["district"]

#     # ✅ STEP 2: Weather query
#     if "मौसम" in user_input:
#         weather = get_weather(district)
#         return f"किसान भाई, आज {district} का मौसम: {weather}"

#     # ✅ STEP 3: Crop suggestion
#     if "फसल" in user_input:
#         crops = get_crops(district, "kharif")
#         return f"किसान भाई, आप इन फसलों पर विचार कर सकते हैं: {crops}"

#     # ✅ STEP 4: Default → LLM + RAG
#     response = generate_response(user_input, session)

#     return response
