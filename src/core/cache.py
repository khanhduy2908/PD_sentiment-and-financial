
import streamlit as st

def cache_data(func=None, **kwargs):
    if func is None:
        return st.cache_data(show_spinner=False, **kwargs)
    return st.cache_data(show_spinner=False, **kwargs)(func)
