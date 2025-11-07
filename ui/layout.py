import streamlit as st
from core.data_access import (
    load_financial_csv,
    list_tickers,
    filter_by_ticker_years,
    resolve_csv_path,
    preview_parse_info,
)

PRIMARY_BLUE = "#1E3A8A"   # xanh dương đậm
PRIMARY_RED  = "#8B0000"   # đỏ đậm

def inject_css_theme():
    st.markdown(f"""
    <style>
      :root {{ --primary-blue:{PRIMARY_BLUE}; --primary-red:{PRIMARY_RED}; }}
      .stApp {{ background:#fff; }}
      .stTabs [data-baseweb="tab-list"] button[role="tab"] {{
        font-weight:600; border-bottom:3px solid transparent; color:#1f2937;
      }}
      .stTabs [data-baseweb="tab-list"] button[aria-selected="true"] {{
        border-color:var(--primary-blue); color:var(--primary-blue);
      }}
    </style>
    """, unsafe_allow_html=True)

@st.cache_data(show_spinner=False)
def _cached_tickers(path: str):
    return list_tickers(path)

@st.cache_data(show_spinner=False)
def _cached_df(path: str):
    return load_financial_csv(path)

def sidebar_inputs():
    st.sidebar.header("Report")
    section = st.sidebar.radio("Section", ["Financial", "Sentiment", "Summary"], index=0)
    st.sidebar.markdown("---")

    info = preview_parse_info()
    if "error" in info:
        st.sidebar.error(f"❌ Cannot load data from CSV. {info['error']}")
        ticker = st.sidebar.text_input("Ticker", value="").upper().strip()
        return ticker, section

    st.sidebar.caption(
        f"Data: {info.get('path')} | sep='{info.get('sep')}' | enc='{info.get('encoding')}' "
        f"| skiprows={info.get('skiprows')} | size={info.get('size_bytes')} bytes"
    )
    path, _ = resolve_csv_path()
    tickers = _cached_tickers(path)

    ticker = st.sidebar.selectbox(
        "Ticker", options=tickers or ["HPG"], index=0, placeholder="Type to search…"
    )
    return ticker, section

def get_data(ticker: str, years: int = 10):
    path, _ = resolve_csv_path()
    df = _cached_df(path)
    return filter_by_ticker_years(df, ticker, years=years)
