# app.py — professional layout
import streamlit as st
import pandas as pd
import re

from utils.io import read_csv_smart
from utils.transforms import build_display_year_column
from tabs import financial, sentiment, summary
from utils.ui import inject_global_css

st.set_page_config(page_title="Corporate Financial Dashboard", layout="wide")

# ----------------------------
# Fallback sorter
# ----------------------------
def sort_year_label(label: str):
    s = str(label).strip()
    is_forecast = s.endswith(("F", "f"))
    m = re.search(r"(19|20)\d{2}", s)
    year = int(m.group(0)) if m else 9999
    return (year, 1 if is_forecast else 0, s)


# ----------------------------
# LOAD DATA
# ----------------------------
@st.cache_data(show_spinner=False)
def load_data() -> pd.DataFrame:
    df = read_csv_smart()
    df = build_display_year_column(df)

    if "Ticker" not in df.columns:
        for c in ["ticker", "Mã CP", "MaCP", "Symbol"]:
            if c in df.columns:
                df["Ticker"] = df[c].astype(str)
                break
        else:
            df["Ticker"] = "SAMPLE"

    df["display_year"] = df["display_year"].astype(str)
    return df


df = load_data()
inject_global_css()

# ----------------------------
# LAYOUT: SIDEBAR + MAIN
# ----------------------------
with st.sidebar:
    st.markdown("### Ticker")
    ticker = st.text_input("", value=df["Ticker"].iloc[0] if not df.empty else "")

    st.markdown("### Report")
    menu = st.radio(
        "Select View",
        ["Financial", "Sentiment", "Summary"],
        index=0,
        label_visibility="collapsed"
    )

# Filter data by ticker
scoped = df[df["Ticker"] == ticker].copy()

# Keep only last 10–12 periods
unique_labels = list(pd.unique(scoped["display_year"].astype(str)))
sorted_labels = sorted(unique_labels, key=sort_year_label)[-12:]
scoped = scoped[scoped["display_year"].astype(str).isin(sorted_labels)]

# ----------------------------
# MAIN CONTENT
# ----------------------------
if menu == "Financial":
    financial.render(scoped)
elif menu == "Sentiment":
    sentiment.render(scoped)
elif menu == "Summary":
    summary.render(scoped)
