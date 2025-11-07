import streamlit as st
from core.data_access import load_configs, load_financial_long, filter_by_ticker_years

def sidebar_inputs():
    st.sidebar.header("Ticker")
    ticker = st.sidebar.text_input("Enter ticker", value="ABC")
    st.sidebar.header("Report")
    section = st.sidebar.radio("Choose", ["Financial","Sentiment","Summary"])
    return ticker, section

def get_data(ticker: str):
    app_cfg, path_cfg, map_cfg = load_configs()
    df = load_financial_long(path_cfg, map_cfg)
    df2 = filter_by_ticker_years(df, ticker, app_cfg.get("default_years", 10))
    return df2
