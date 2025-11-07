# ui/layout.py
import streamlit as st
from core.data_access import load_financial_long, filter_by_ticker_years

def sidebar_inputs():
    st.sidebar.header("Ticker")
    ticker = st.sidebar.text_input("Enter ticker", value="ABC").upper().strip()
    st.sidebar.header("Report")
    section = st.sidebar.radio("Choose", ["Financial", "Sentiment", "Summary"])
    return ticker, section

def get_data(ticker: str, years: int = 10):
    # Đọc trực tiếp file CSV bạn đã up
    df = load_financial_long("data/bctc_final.csv")
    return filter_by_ticker_years(df, ticker, years)

def inject_css_theme():
    st.markdown("""
    <style>
      :root { --blue:#1E3A8A; --red:#8B0000; }
      h1,h2,h3 { color: var(--blue); }
      .red-accent { color: var(--red); font-weight:700; }
    </style>
    """, unsafe_allow_html=True)

# Alias để tương thích với app.py cũ
def sidebar_controls():
    return sidebar_inputs()
