import streamlit as st
from layout import sidebar_inputs, get_data, inject_css_theme
from ui.tabs.financial import income as tab_income
from ui.tabs.financial import balance as tab_balance
from ui.tabs.financial import cashflow as tab_cash
from ui.tabs.financial import indicators as tab_indicators
from ui.tabs.financial import note as tab_note
from ui.tabs.financial import report as tab_report

st.set_page_config(page_title="AI Default Risk", layout="wide")
inject_css_theme()

ticker, section = sidebar_inputs()
data = get_data(ticker, years=10)

if section == "Financial":
    tabs = st.tabs([
        "Income statement","Balance Sheet","Cashflow Statement",
        "Financial Indicator","Note","Report"
    ])
    with tabs[0]: tab_income.render(data)
    with tabs[1]: tab_balance.render(data)
    with tabs[2]: tab_cash.render(data)
    with tabs[3]: tab_indicators.render(data)
    with tabs[4]: tab_note.render(data)
    with tabs[5]: tab_report.render(data)
elif section == "Sentiment":
    st.info("Sentiment module coming next.")
else:
    st.info("Summary / Default risk module coming next.")
