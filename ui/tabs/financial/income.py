import streamlit as st
from core.transforms import build_income_table, style_table

def render(fin_filtered):
    st.subheader("Income Statement")
    table, meta = build_income_table(fin_filtered)
    if table.empty:
        st.info("No income statement data for this ticker or period window.")
        return
    st.dataframe(style_table(table, meta), use_container_width=True)
    st.download_button("Download CSV", table.to_csv().encode("utf-8"), file_name="income_statement.csv")
