
import streamlit as st
import pandas as pd
from financial_subtabs import income_statement, balance_sheet, cashflow_statement, notes, financial_indicators

def render(fin_df: pd.DataFrame):
    st.header("Financial")
    sub = st.tabs(["Income Statement","Balance Sheet","Cashflow Statement","Note","Financial Indicators"])
    with sub[0]:
        income_statement.render(fin_df)
    with sub[1]:
        balance_sheet.render(fin_df)
    with sub[2]:
        cashflow_statement.render(fin_df)
    with sub[3]:
        notes.render(fin_df)
    with sub[4]:
        financial_indicators.render(fin_df)
