# app.py
import sys, os
import streamlit as st

ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from ui.layout import inject_css_theme, sidebar_inputs, get_data

def _safe_import(path):
    try:
        return __import__(path, fromlist=["_"])
    except Exception:
        return None

# Your existing tab modules (each must have render(fin_filtered))
tab_income     = _safe_import("ui.tabs.financial.income")
tab_balance    = _safe_import("ui.tabs.financial.balance")
tab_cashflow   = _safe_import("ui.tabs.financial.cashflow")
tab_indicators = _safe_import("ui.tabs.financial.indicators")
tab_note       = _safe_import("ui.tabs.financial.note")
tab_report     = _safe_import("ui.tabs.financial.report")
tab_news       = _safe_import("ui.tabs.sentiment.news")
tab_sagg       = _safe_import("ui.tabs.sentiment.aggregates")
tab_model      = _safe_import("ui.tabs.summary.modeling")

st.set_page_config(page_title="Financial & Sentiment Dashboard", layout="wide")
inject_css_theme()
st.title("Financial & Sentiment Dashboard")

ticker = sidebar_inputs()

data = None
data_error = None
if ticker:
    try:
        data = get_data(ticker, years=10)
    except Exception as e:
        data_error = str(e)

tab_titles, tab_renderers = [], []
def _add(title, module):
    if module is not None and hasattr(module, "render"):
        tab_titles.append(title)
        tab_renderers.append(module.render)

# Show all aspects as tabs (no “group” selector)
_add("Income Statement", tab_income)
_add("Balance Sheet", tab_balance)
_add("Cash Flow Statement", tab_cashflow)
_add("Indicators", tab_indicators)
_add("Notes", tab_note)
_add("Report", tab_report)
_add("Sentiment — News", tab_news)
_add("Sentiment — Aggregates", tab_sagg)
_add("Summary — Modeling", tab_model)

if not tab_titles:
    st.warning("No child tabs with a function `render(fin_filtered)` were found.")
else:
    tabs = st.tabs(tab_titles)
    if data_error:
        for t in tabs:
            with t:
                st.error(f"Cannot load data for {ticker}. Details: {data_error}")
    else:
        for (t, render_fn) in zip(tabs, tab_renderers):
            with t:
                try:
                    render_fn(data)
                except Exception as e:
                    st.error(f"Tab error: {e}")
