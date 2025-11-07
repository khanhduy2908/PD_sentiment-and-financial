# app.py
# Corporate Financial Dashboard — premium layout, English-only, no icons

import os
import pandas as pd
import streamlit as st

# ---- Local modules from your repo ----
# Keep only functions we are sure you have; avoid importing missing ones
from utils.io import read_csv_smart
from utils.transforms import build_display_year_column
from tabs import financial, sentiment, summary


# =============================
# Page config + global styling
# =============================
st.set_page_config(
    page_title="Corporate Financial Dashboard",
    layout="wide"
)

def inject_global_css():
    st.markdown("""
    <style>
      .block-container {padding-top: 0.8rem; padding-bottom: 1.0rem;}
      .app-header{
        font-family: Inter, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, "Apple Color Emoji","Segoe UI Emoji";
        font-size: 28px; font-weight: 700; color: #1B1F24; letter-spacing: .2px;
        margin: 6px 0 2px 0;
      }
      .app-subtitle{ font-size: 14px; color:#475569; margin:0 0 16px 0;}
      .stTabs [data-baseweb="tab"] { padding: 6px 14px; font-weight: 600; }
      .stSelectbox > label, .stRadio > label, .stTextInput > label { font-weight: 600; color:#1f2937; }
      .stRadio [data-baseweb="radio"] { gap: 6px; }
    </style>
    """, unsafe_allow_html=True)

inject_global_css()
st.markdown('<div class="app-header">Corporate Financial Dashboard</div>', unsafe_allow_html=True)
st.markdown('<div class="app-subtitle">Financial statements • Indicators • Notes</div>', unsafe_allow_html=True)


# =============================
# Data loading
# =============================
@st.cache_data(show_spinner=False)
def load_data() -> pd.DataFrame:
    """
    Load CSV from ./data/bctc_final.csv or repository root fallback.
    Also builds a 'display_year' helper column for consistent year labels.
    """
    df = read_csv_smart()  # your util handles search paths
    df = build_display_year_column(df)

    # Normalize Ticker column if absent
    if "Ticker" not in df.columns:
        for c in ["ticker", "Mã CP", "MaCP", "Symbol"]:
            if c in df.columns:
                df["Ticker"] = df[c]
                break
    if "Ticker" not in df.columns:
        df["Ticker"] = "SAMPLE"

    # Standardize types
    df["Ticker"] = df["Ticker"].astype(str).str.strip().str.upper()
    df["display_year"] = df["display_year"].astype(str)

    return df


def build_ticker_list(df: pd.DataFrame):
    """Unique sorted ticker list."""
    if "Ticker" not in df.columns:
        return []
    tickers = (
        df["Ticker"].fillna("").astype(str).str.strip().str.upper()
        .replace({"": pd.NA}).dropna().unique().tolist()
    )
    return sorted(set(tickers))


# =============================
# App body
# =============================
df = load_data()

# --- Sidebar controls (premium, English-only) ---
with st.sidebar:
    st.caption("Ticker")
    all_tickers = build_ticker_list(df)

    # Load from URL ?ticker=...
    qs = st.experimental_get_query_params()
    tic_from_url = None
    if "ticker" in qs and qs["ticker"]:
        tic_from_url = str(qs["ticker"][0]).upper()

    if not all_tickers:
        st.info("No tickers found in data. Please check your CSV.")
        selected_ticker = None
    else:
        default_idx = 0
        if tic_from_url and tic_from_url in all_tickers:
            default_idx = all_tickers.index(tic_from_url)
        elif "HPG" in all_tickers:
            default_idx = all_tickers.index("HPG")

        selected_ticker = st.selectbox(
            "Select a ticker",
            options=all_tickers,
            index=default_idx,
            help="Start typing to filter the list (e.g., HPG, VNM, FPT).",
            label_visibility="collapsed"
        )

    st.markdown("---")
    st.caption("Report")
    report_tab = st.radio(
        "Report",
        options=["Financial", "Sentiment", "Summary"],
        index=0,
        label_visibility="collapsed"
    )

# Sync ticker back to URL
if selected_ticker:
    st.experimental_set_query_params(ticker=selected_ticker)

# Scope data by ticker
if selected_ticker:
    scoped = df[df["Ticker"] == selected_ticker].copy()
else:
    scoped = df.head(0).copy()  # empty frame to avoid errors

# Pick recent 10 years if possible
if not scoped.empty and "display_year" in scoped.columns:
    # keep ordering by year-like string
    years = (
        scoped["display_year"].dropna().astype(str).unique().tolist()
    )
    # sort numeric where possible
    def _year_key(y):
        try:
            return (0, int("".join(ch for ch in y if ch.isdigit())[:4]))
        except Exception:
            return (1, y)
    years_sorted = sorted(years, key=_year_key)
    recent10 = [y for y in years_sorted if y][-10:]
    scoped = scoped[scoped["display_year"].astype(str).isin(recent10)].copy()


# =============================
# Main tabs
# =============================
tabs = st.tabs([
    "Income statement",
    "Balance Sheet",
    "Cashflow Statement",
    "Financial Indicator",
    "Report"
])

with tabs[0]:
    financial.render(scoped, default_subtab="income")  # your financial tab

with tabs[1]:
    financial.render(scoped, default_subtab="balance")

with tabs[2]:
    financial.render(scoped, default_subtab="cashflow")

with tabs[3]:
    st.subheader("FINANCIAL INDICATORS")
    # financial_subtabs.financial_indicators.render is called
    # inside financial.render when default_subtab="indicator".
    # If you want to render directly, uncomment next line and remove the line after:
    # financial_indicators.render(scoped)
    financial.render(scoped, default_subtab="indicator")

with tabs[4]:
    # Notes/Report area
    financial.render(scoped, default_subtab="notes")
    # Or if you keep separate modules:
    # summary.render(scoped)
