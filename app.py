# app.py (phần import ở đầu file)

import streamlit as st
import pandas as pd
import re

from utils.io import read_csv_smart

# Try import; if missing, define a robust fallback locally
try:
    from utils.transforms import build_display_year_column, sort_year_label
except ImportError:
    from utils.transforms import build_display_year_column

    def sort_year_label(label: str):
        """
        Sorting key for year labels:
        - Extracts 4-digit year (e.g., 2016 from '2016', '2016A', 'FY2016', '2016F')
        - Real years come before forecast years (suffix 'F' or 'f').
        - Stable fallback to string if no year found.
        """
        s = str(label).strip()
        is_forecast = s.endswith(("F", "f"))
        m = re.search(r"(19|20)\d{2}", s)
        year = int(m.group(0)) if m else 9999
        return (year, 1 if is_forecast else 0, s)

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

left, right = st.columns([1, 3], vertical_alignment="top")

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
