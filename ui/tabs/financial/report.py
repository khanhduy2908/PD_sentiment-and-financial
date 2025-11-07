import streamlit as st
import pandas as pd
from ...core.transforms import select_statement, pivot_statement

def render(fin_filtered):
    st.subheader("Financial Report – Charts")
    inc = select_statement(fin_filtered, "income")
    if inc.empty:
        st.info("No income data to chart.")
        return
    pv = pivot_statement(inc)
    # simple chart for revenue & gross profit if they exist
    rev = pv.loc[pv.index.str.contains("net revenue", case=False, na=False)] if not pv.empty else pd.DataFrame()
    gp = pv.loc[pv.index.str.contains("gross profit", case=False, na=False)] if not pv.empty else pd.DataFrame()
    if not rev.empty:
        st.line_chart(rev.T)
    if not gp.empty:
        st.line_chart(gp.T)
