import os
import streamlit as st
from core.data_access import load_financial_csv, list_tickers, filter_by_ticker_years, CSV_PATH_DEFAULT

PRIMARY_BLUE = "#1E3A8A"   # xanh dương đậm
PRIMARY_RED  = "#8B0000"   # đỏ đậm

def inject_css_theme():
    st.markdown(f"""
    <style>
      :root {{
        --primary-blue: {PRIMARY_BLUE};
        --primary-red:  {PRIMARY_RED};
      }}
      .stApp {{
        background-color: #ffffff;
      }}
      .stTabs [data-baseweb="tab-list"] button[role="tab"] {{
        font-weight: 600;
        border-bottom: 3px solid transparent;
        color: #1f2937;
      }}
      .stTabs [data-baseweb="tab-list"] button[aria-selected="true"] {{
        border-color: var(--primary-blue);
        color: var(--primary-blue);
      }}
      .css-1d391kg, .stMarkdown h1, .stMarkdown h2, .stMarkdown h3 {{
        color: var(--primary-blue);
      }}
      .downloadButton>button, .stButton>button {{
        border-radius: 6px;
        border: 1px solid var(--primary-blue);
      }}
    </style>
    """, unsafe_allow_html=True)

@st.cache_data(show_spinner=False)
def _cached_list_tickers(csv_path: str):
    return list_tickers(csv_path)

def sidebar_inputs():
    st.sidebar.header("Report")
    section = st.sidebar.radio("Section", ["Financial", "Sentiment", "Summary"], index=0)

    st.sidebar.markdown("---")
    st.sidebar.subheader("Ticker")

    # Gợi ý ticker từ CSV (typeahead)
    tickers = _cached_list_tickers(CSV_PATH_DEFAULT)
    placeholder = "Type to search ticker..." if tickers else "Enter ticker..."
    if tickers:
        ticker = st.sidebar.selectbox("Ticker", options=tickers, index=0, placeholder=placeholder)
    else:
        ticker = st.sidebar.text_input("Ticker", value="", placeholder=placeholder).upper().strip()

    st.sidebar.caption(f"Data source: {CSV_PATH_DEFAULT}")
    return ticker, section

@st.cache_data(show_spinner=False)
def _cached_df(csv_path: str):
    return load_financial_csv(csv_path)

def get_data(ticker: str, years: int = 10):
    """Load CSV và lọc theo ticker + 10 năm mặc định."""
    df = _cached_df(CSV_PATH_DEFAULT)
    if df.empty:
        raise ValueError("CSV is empty or cannot be parsed.")
    if "ticker" not in df.columns:
        raise ValueError("CSV must contain a 'ticker' column.")

    df2 = filter_by_ticker_years(df, ticker, years=years)
    if df2.empty:
        st.warning(f"No rows found for ticker '{ticker}'.")
    return df2
