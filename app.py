import sys, os
import streamlit as st

# ==== Path setup để import được ui/* ====
ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
UI_DIR = os.path.join(ROOT, "ui")
if UI_DIR not in sys.path:
    sys.path.insert(0, UI_DIR)

# ==== Import layout + tabs ====
try:
    from layout import sidebar_inputs, get_data, inject_css_theme
except ModuleNotFoundError:
    from ui.layout import sidebar_inputs, get_data, inject_css_theme

from ui.tabs.financial import income as tab_income
from ui.tabs.financial import balance as tab_balance
from ui.tabs.financial import cashflow as tab_cashflow
from ui.tabs.financial import indicators as tab_indicators
from ui.tabs.financial import note as tab_note
from ui.tabs.financial import report as tab_report

st.set_page_config(page_title="AI-Driven Default Risk", layout="wide", initial_sidebar_state="expanded")
inject_css_theme()

# === Sidebar inputs (ticker có gợi ý) ===
ticker, section = sidebar_inputs()

# === Load data theo ticker (mặc định 10 năm) ===
try:
    fin_df = get_data(ticker, years=10)
except Exception as e:
    st.error(f"❌ Cannot load data from CSV. {e}")
    st.stop()

# === Điều hướng các tab ===
if section == "Financial":
    tabs = st.tabs([
        "Income Statement",
        "Balance Sheet",
        "Cashflow Statement",
        "Financial Indicators",
        "Notes",
        "Report"
    ])
    with tabs[0]: tab_income.render(fin_df)
    with tabs[1]: tab_balance.render(fin_df)
    with tabs[2]: tab_cashflow.render(fin_df)
    with tabs[3]: tab_indicators.render(fin_df)
    with tabs[4]: tab_note.render(fin_df)
    with tabs[5]: tab_report.render(fin_df)

elif section == "Sentiment":
    st.info("Sentiment module – coming next.")
elif section == "Summary":
    st.info("Summary / Modeling – coming next.")
else:
    st.warning("Please select a section from the sidebar.")
