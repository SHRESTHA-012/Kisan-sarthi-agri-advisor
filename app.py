import streamlit as st
from backend.crop_engine import get_crops
from backend.weather_service import get_weather
from backend.chatbot import generate_response

st.title("🌾 AgriAdvisor Bihar")

user_input = st.text_input("कृषि से जुड़ा प्रश्न पूछें")

if user_input:
    st.write("AI:", "यह एक परीक्षण उत्तर है")

district = "Patna"
season = "Kharif"

crops = get_crops(district, season)

if user_input:
    st.write("Crops:", crops)

weather = get_weather(district)
st.write("Weather:", weather)
