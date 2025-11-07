import streamlit as st
from core.data_access import load_configs, load_financial_long, filter_by_ticker_years
from ui.layout import sidebar_controls, inject_css_theme
from ui.tabs.financial import income as tab_income
from ui.tabs.financial import balance as tab_balance
from ui.tabs.financial import cashflow as tab_cashflow
from ui.tabs.financial import indicators as tab_indicators
from ui.tabs.financial import report as tab_report
from ui.tabs.sentiment import news as tab_news
from ui.tabs.sentiment import aggregates as tab_aggr
from ui.tabs.summary import modeling as tab_modeling

st.set_page_config(page_title="AI Default Risk", layout="wide", initial_sidebar_state="expanded")
inject_css_theme()

app_cfg, path_cfg, map_cfg = load_configs()
fin_long = load_financial_long(path_cfg, map_cfg)

ticker, section, apply_clicked = sidebar_controls()
if "ticker" not in st.session_state:
    st.session_state["ticker"] = ""
if apply_clicked:
    st.session_state["ticker"] = ticker.strip()

chosen = st.session_state["ticker"]
if not chosen:
    st.markdown("### Please enter a ticker on the left and press Apply.")
    st.stop()

years = int(app_cfg["app"]["default_year_window"])
fin_filtered = filter_by_ticker_years(fin_long, chosen, years)

st.title("AI-Driven Corporate Default Risk Prediction")
st.caption("Financial • Sentiment • Summary")

if section == "Financial":
    tabs = st.tabs(["Income statement","Balance Sheet","Cashflow Statement","Financial Indicator","Report"])
    with tabs[0]:
        tab_income.render(fin_filtered)
    with tabs[1]:
        tab_balance.render(fin_filtered)
    with tabs[2]:
        tab_cashflow.render(fin_filtered)
    with tabs[3]:
        tab_indicators.render(fin_filtered)
    with tabs[4]:
        tab_report.render(fin_filtered)
elif section == "Sentiment":
    tabs = st.tabs(["News","Aggregates"])
    with tabs[0]:
        tab_news.render(None)  # add real sentiment later
    with tabs[1]:
        tab_aggr.render(None)
else:
    tabs = st.tabs(["Modeling"])
    with tabs[0]:
        tab_modeling.render(fin_filtered)
