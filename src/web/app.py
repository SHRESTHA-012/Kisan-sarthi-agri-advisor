import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import streamlit as st
from src.core.chatbot import generate_response
from src.core.weather_service import get_weather
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(
    page_title="AgriAdvisor Bihar",
    page_icon="🌾",
    layout="centered",
)

st.title("🌾 AgriAdvisor Bihar")
st.caption("बिहार के किसानों के लिए AI कृषि सलाहकार")

if "messages" not in st.session_state:
    st.session_state.messages = []

if "district" not in st.session_state:
    st.session_state.district = None

BIHAR_DISTRICTS = [
    "Patna", "Gaya", "Muzaffarpur", "Bhagalpur", "Darbhanga",
    "Purnia", "Nalanda", "Rohtas", "Vaishali", "Champaran",
    "Sitamarhi", "Samastipur", "Begusarai", "Saran", "Siwan",
    "Araria", "Arwal", "Aurangabad", "Banka", "Buxar",
    "Gopalganj", "Jamui", "Jehanabad", "Kaimur", "Katihar",
    "Khagaria", "Kishanganj", "Lakhisarai", "Madhepura", "Madhubani",
    "Munger", "Nawada", "Sheikhpura", "Sheohar", "Supaul", "West Champaran",
]

if st.session_state.district is None:
    st.info("👋 शुरू करने के लिए अपना जिला चुनें")
    selected = st.selectbox("अपना जिला चुनें", ["-- जिला चुनें --"] + BIHAR_DISTRICTS)
    if selected != "-- जिला चुनें --":
        st.session_state.district = selected
        st.rerun()
    st.stop()

with st.sidebar:
    st.markdown(f"### 📍 {st.session_state.district}")
    weather = get_weather(st.session_state.district)
    st.metric("🌡️ तापमान", f"{weather['temp']}°C")
    st.metric("💧 नमी", f"{weather['humidity']}%")
    st.markdown(f"**{weather['description']}**")
    st.info(weather["advisory"])

    if st.button("जिला बदलें"):
        st.session_state.district  = None
        st.session_state.messages  = []
        st.rerun()

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

user_input = st.chat_input("कृषि से जुड़ा प्रश्न पूछें...")

if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.write(user_input)

    with st.chat_message("assistant"):
        with st.spinner("सोच रहे हैं..."):
            response = generate_response(
                user_input,
                district=st.session_state.district,
                chat_history=st.session_state.messages,
            )
        st.write(response)

    st.session_state.messages.append({"role": "assistant", "content": response})
