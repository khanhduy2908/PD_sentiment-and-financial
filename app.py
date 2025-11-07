
import streamlit as st
from src.ui.layout import render_shell
from src.core.state import AppState

st.set_page_config(page_title="AI-Driven Default Risk", layout="wide", initial_sidebar_state="expanded")

def main():
    if "state" not in st.session_state:
        st.session_state["state"] = AppState()
    render_shell(st.session_state["state"])

if __name__ == "__main__":
    main()
