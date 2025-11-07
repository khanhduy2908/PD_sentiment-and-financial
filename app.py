# app.py
import os, sys
import streamlit as st

# đảm bảo chạy từ project root
ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from ui.layout import inject_css_theme, sidebar_inputs, get_active_selection, get_data

# các tab con (đã có sẵn)
from ui.tabs.financial import income as tab_income
from ui.tabs.financial import balance as tab_balance
from ui.tabs.financial import cashflow as tab_cashflow
from ui.tabs.financial import indicators as tab_indicators
from ui.tabs.financial import note as tab_note
from ui.tabs.financial import report as tab_report

# ====== PAGE CONFIG ======
st.set_page_config(
    page_title="AI-Driven Default Risk – Financial & Sentiment",
    page_icon="📊",
    layout="wide",
)

inject_css_theme()
sidebar_inputs()                          # form bên trái
ticker, section = get_active_selection()  # chỉ có khi user bấm "Xem báo cáo"
data = get_data(ticker, years=10)

# ====== HEADER ======
st.markdown(f'<div class="section-h1">Báo cáo cho <span style="color:#0B74D0">{ticker}</span></div>', unsafe_allow_html=True)

# ====== ROUTER ======
if section == "Financial":
    tabs = st.tabs(["Income statement","Balance Sheet","Cashflow Statement","Financial Indicator","Note","Report"])
    with tabs[0]: tab_income.render(data)
    with tabs[1]: tab_balance.render(data)
    with tabs[2]: tab_cashflow.render(data)
    with tabs[3]: tab_indicators.render(data)
    with tabs[4]: tab_note.render(data)
    with tabs[5]: tab_report.render(data)

elif section == "Sentiment":
    st.info("Tab Sentiment sẽ tích hợp sau (news, aggregates, …).")

else:  # Summary
    st.info("Tab Summary sẽ tích hợp sau (modeling, explainability, …).")
