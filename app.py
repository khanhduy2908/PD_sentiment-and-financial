
import streamlit as st
from utils.io import read_csv_smart
from utils.transforms import build_display_year_column, sort_year_labels
from tabs import financial, sentiment, summary

st.set_page_config(page_title="Corporate Default Risk Scoring", layout="wide")
st.title("Corporate Default Risk — Data Browser")

@st.cache_data(show_spinner=False)
def load_data():
    df = read_csv_smart()
    df = build_display_year_column(df)
    if "Ticker" not in df.columns:
        for c in ["ticker","Mã CP","MaCP","Symbol"]:
            if c in df.columns: df = df.rename(columns={c:"Ticker"}); break
    if "Ticker" not in df.columns:
        df["Ticker"] = "SAMPLE"
    return df

df = load_data()

left, right = st.columns([1,3])
with left:
    tickers = sorted(df["Ticker"].astype(str).unique().tolist())
    ticker = st.selectbox("Ticker", tickers, index=0 if tickers else None)
    ylabels = sort_year_labels(df.loc[df["Ticker"]==ticker, "display_year"].astype(str).unique().tolist())
    recent10 = ylabels[-10:] if len(ylabels) > 10 else ylabels
    st.caption(f"Years shown: {', '.join(recent10)}")

with right:
    tabs = st.tabs(["Financial","Sentiment","Summary"])
    scoped = df[df["Ticker"]==ticker].copy()
    scoped = scoped[scoped["display_year"].astype(str).isin(recent10)]
    with tabs[0]:
        financial.render(scoped)
    with tabs[1]:
        sentiment.render(scoped)
    with tabs[2]:
        summary.render(scoped)
