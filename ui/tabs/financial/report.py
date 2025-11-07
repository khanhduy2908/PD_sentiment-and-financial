import streamlit as st
import matplotlib.pyplot as plt
from ...core.features import build_indicators
from ...core.utils import load_yaml

def render(fin_filtered):
    st.subheader("Report")
    kw = load_yaml("config/mappings.yaml")["keywords"]
    ratios = build_indicators(fin_filtered, kw)
    if ratios.empty:
        st.info("Not enough data to draw charts.")
        return

    st.markdown("**Overview tables**")
    st.dataframe(ratios)

    if "Revenue" in ratios.columns:
        fig = plt.figure()
        s = ratios["Revenue"].dropna()
        plt.plot(s.index, s.values)
        plt.title("Revenue Trend")
        plt.xlabel("Year")
        plt.ylabel("VND")
        st.pyplot(fig)

    for metric in ["GrossMargin","EBITMargin","NetMargin"]:
        if metric in ratios.columns and ratios[metric].notna().any():
            fig = plt.figure()
            s = ratios[metric].dropna()
            plt.plot(s.index, s.values)
            plt.title(f"{metric} Trend")
            plt.xlabel("Year")
            plt.ylabel(metric)
            st.pyplot(fig)
