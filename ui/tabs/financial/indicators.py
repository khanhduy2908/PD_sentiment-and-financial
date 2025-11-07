import streamlit as st
from ...core.features import build_indicators
from ...core.utils import load_yaml

def render(fin_filtered):
    st.subheader("Financial Indicator")
    kw = load_yaml("config/mappings.yaml")["keywords"]
    ratios = build_indicators(fin_filtered, kw)
    if ratios.empty:
        st.info("Indicators could not be computed for this ticker and period window.")
        return
    st.dataframe(ratios)
    st.download_button("Download CSV", ratios.to_csv().encode("utf-8"), file_name="financial_indicators.csv")
