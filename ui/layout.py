import streamlit as st
from core.data_access import (
    load_financial_csv,
    list_tickers,
    filter_by_ticker_years,
    resolve_csv_path,
    preview_parse_info,
)

PRIMARY_BLUE = "#1E3A8A"  # xanh dương đậm
PRIMARY_RED  = "#8B0000"  # đỏ đậm

def inject_css_theme():
    st.markdown(f"""
    <style>
      :root {{
        --primary-blue: {PRIMARY_BLUE};
        --primary-red:  {PRIMARY_RED};
      }}
      .stApp {{ background-color: #ffffff; }}
      .stTabs [data-baseweb="tab-list"] button[role="tab"] {{
        font-weight: 600;
        border-bottom: 3px solid transparent;
        color: #1f2937;
      }}
      .stTabs [data-baseweb="tab-list"] button[aria-selected="true"] {{
        border-color: var(--primary-blue);
        color: var(--primary-blue);
      }}
      .stMarkdown h1, .stMarkdown h2, .stMarkdown h3 {{ color: var(--primary-blue); }}
      .css-1dp5vir, .stButton>button {{ border-radius: 6px; }}
    </style>
    """, unsafe_allow_html=True)

@st.cache_data(show_spinner=False)
def _cached_tickers(path: str):
    return list_tickers(path)

def sidebar_inputs():
    st.sidebar.header("Report")
    section = st.sidebar.radio("Section", ["Financial", "Sentiment", "Summary"], index=0)
    st.sidebar.markdown("---")

    # Hiển thị parse info ngắn gọn để bạn biết app đang đọc thế nào
    info = preview_parse_info()
    if "error" in info:
        st.sidebar.error(f"CSV parse error: {info['error']}")
        path, _ = resolve_csv_path()
        st.sidebar.caption(f"Data source: {path}")
        tickers = []
    else:
        st.sidebar.caption(
            f"Data source: {info.get('path')} | sep='{info.get('sep')}' | "
            f"encoding='{info.get('encoding')}' | skiprows={info.get('skiprows')}"
        )
        tickers = _cached_tickers(info["path"])

    st.sidebar.subheader("Ticker")
    if tickers:
        ticker = st.sidebar.selectbox(
            "Ticker",
            options=tickers,
            index=0,
            placeholder="Type to search…",
        )
    else:
        ticker = st.sidebar.text_input("Ticker", value="", placeholder="E.g. HPG").upper().strip()

    return ticker, section

@st.cache_data(show_spinner=False)
def _cached_df(path: str):
    return load_financial_csv(path)

def get_data(ticker: str, years: int = 10):
    path, _ = resolve_csv_path()
    df = _cached_df(path)
    if df.empty:
        st.warning("CSV parsed but empty.")
        return df
    if "ticker" not in df.columns:
        st.error("CSV must contain a 'ticker' column.")
        return df
    return filter_by_ticker_years(df, ticker, years=years)
