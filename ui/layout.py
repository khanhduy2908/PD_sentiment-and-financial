import streamlit as st
from core.data_access import (
    load_financial_csv,
    list_tickers,
    filter_by_ticker_years,
    resolve_csv_path,
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
      .stButton>button, .downloadButton>button {{
        border-radius: 6px; border: 1px solid var(--primary-blue);
      }}
    </style>
    """, unsafe_allow_html=True)

@st.cache_data(show_spinner=False)
def _cached_tickers_and_path():
    """
    Trả về (tickers, path, error_str).
    Nếu có lỗi parse, trả tickers=[], error_str để sidebar hiển thị, app vẫn không crash.
    """
    try:
        path, tried = resolve_csv_path()
    except Exception as e:
        return [], None, f"File not found. {e}"

    try:
        tks = list_tickers(path)
        return tks, path, None
    except Exception as e:
        # Không crash — để người dùng vẫn có field nhập ticker
        return [], path, f"CSV parse error: {e}"

def sidebar_inputs():
    st.sidebar.header("Report")
    section = st.sidebar.radio("Section", ["Financial", "Sentiment", "Summary"], index=0)
    st.sidebar.markdown("---")

    st.sidebar.subheader("Ticker")
    tickers, resolved_path, err = _cached_tickers_and_path()

    if resolved_path:
        st.sidebar.caption(f"Data source: {resolved_path}")
    if err:
        st.sidebar.error(err)

    if tickers:
        ticker = st.sidebar.selectbox(
            "Search & select ticker",
            options=tickers,
            index=0,
            placeholder="Type to search...",
        )
    else:
        ticker = st.sidebar.text_input("Enter ticker", value="", placeholder="E.g. HPG, VNM, ...").upper().strip()

    return ticker, section

@st.cache_data(show_spinner=False)
def _cached_df(path: str):
    return load_financial_csv(path)

def get_data(ticker: str, years: int = 10):
    # Dò path thực tế
    path, _ = resolve_csv_path()
    df = _cached_df(path)
    if df.empty:
        raise ValueError("CSV is empty after parsing.")
    if "ticker" not in df.columns:
        raise ValueError("CSV must contain a 'ticker' column.")

    df2 = filter_by_ticker_years(df, ticker, years=years)
    if df2.empty:
        st.warning(f"No rows found for ticker '{ticker}'.")
    return df2
