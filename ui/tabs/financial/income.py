import streamlit as st
from ...core.transforms import pivot_statement, select_statement

def render(fin_filtered):
    st.subheader("Income Statement")
    df = select_statement(fin_filtered, "income")
    pv = pivot_statement(df)
    if pv.empty:
        st.info("No data for this ticker or period window.")
        return
    st.dataframe(pv)
    st.download_button("Download CSV", pv.to_csv().encode("utf-8"), file_name="income_statement.csv")
