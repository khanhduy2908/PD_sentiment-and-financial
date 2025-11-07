import streamlit as st
from ...core.transforms import select_statement, pivot_statement

def render(fin_filtered):
    st.subheader("Financial Indicators")
    df = select_statement(fin_filtered, "indicator")
    if df.empty:
        st.info("No financial indicators found.")
        return
    pv = pivot_statement(df)
    st.dataframe(pv, use_container_width=True)
    st.download_button("Download CSV", pv.to_csv().encode("utf-8"), file_name="financial_indicators.csv")
