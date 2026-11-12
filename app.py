"""
FINITE AUTOMATA VALIDATOR - Streamlit entry point.
Run with:   streamlit run app.py
"""
import streamlit as st

st.set_page_config(page_title="Finite Automata Validator", page_icon="🔷", layout="wide")

from ui import common, page_email, page_home, page_password, page_pin, page_testing, page_visualizer  # noqa: E402

PAGES = {
    "🏠 Home Dashboard": page_home,
    "💳 ATM PIN Validator": page_pin,
    "🔑 Password Validator": page_password,
    "✉️ E-mail Validator": page_email,
    "🔷 Automata Visualizer": page_visualizer,
    "🧪 Testing and Results": page_testing,
}

common.inject_css()
st.sidebar.markdown("## 🔷 Finite Automata Validator")
st.sidebar.caption("FLA · CLA-2 Task 2")
choice = st.sidebar.radio("Navigate", list(PAGES), label_visibility="collapsed")
st.sidebar.divider()
st.sidebar.caption("Syntax checks by DFA / NFA. Passwords are never stored or logged.")
PAGES[choice].render()
