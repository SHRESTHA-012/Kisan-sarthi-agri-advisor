import streamlit as st

st.title("🌾 AgriAdvisor Bihar")

user_input = st.text_input("प्रश्न पूछें")

if user_input:
    st.write("AI:", "यह एक परीक्षण उत्तर है")
