import streamlit as st
from backend.chatbot import generate_response

st.title("🌾 AgriAdvisor Bihar")

user_input = st.text_input("कृषि से जुड़ा प्रश्न पूछें")

if user_input:
    response = generate_response(user_input)
    st.write("AI:", response)


