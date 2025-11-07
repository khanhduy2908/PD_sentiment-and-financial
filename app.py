# app.py
import streamlit as st
import pandas as pd

from utils.io import read_csv_smart
from utils.transforms import build_display_year_column, sort_year_label
from tabs import financial, sentiment, summary
from utils.ui import inject_global_css

st.set_page_config(page_title="Corporate Financial Dashboard", layout="wide")

@st.cache_data(show_spinner=False)
def load_data() -> pd.DataFrame:
    df = read_csv_smart()
    df = build_display_year_column(df)

    # Standardize ticker column if missing
    if "Ticker" not in df.columns:
        for c in ["ticker", "Mã CP", "MaCP", "Symbol"]:
            if c in df.columns:
                df["Ticker"] = df[c].astype(str)
                break
        else:
            df["Ticker"] = "SAMPLE"

    # Ensure year-like display column exists and string-typed
    if "display_year" not in df.columns:
        # Fallback: try typical year fields
        for c in ["Year", "year", "Năm"]:
            if c in df.columns:
                df["display_year"] = df[c].astype(str)
                break
        else:
            df["display_year"] = ""

    df["display_year"] = df["display_year"].astype(str)
    return df

df = load_data()
inject_global_css()

left, right = st.columns([1, 3], vertical_alignment="start")

with left:
    # All English labels, no icons added anywhere
    st.text_input("Ticker", value=str(df["Ticker"].iloc[0] if not df.empty else ""))

    st.header("Report")
    page = st.radio(
        label="",
        options=["Financial", "Sentiment", "Summary"],
        index=0,
        label_visibility="collapsed"
    )

with right:
    # Keep only the most recent ~12 labels (sorted)
    all_labels = list(pd.unique(df["display_year"].astype(str)))
    try:
        recent_labels = sorted(all_labels, key=sort_year_label)[-12:]
    except Exception:
        # Fallback simple sort if helper differs
        recent_labels = sorted(all_labels)[-12:]

    scoped = df[df["display_year"].astype(str).isin(recent_labels)].copy()

    if page == "Financial":
        financial.render(scoped)
    elif page == "Sentiment":
        sentiment.render(scoped)
    else:
        summary.render(scoped)
