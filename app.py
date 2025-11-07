# app.py — Premium shell
import streamlit as st
import pandas as pd
import re

from utils.io import read_csv_smart
from utils.transforms import build_display_year_column
from utils.ui import inject_global_css, header, kpi_row
from tabs import financial, sentiment, summary

st.set_page_config(page_title="Corporate Financial Dashboard", layout="wide")

def sort_year_label(s: str):
    s = str(s)
    is_f = s.endswith(("F","f"))
    m = re.search(r"(19|20)\d{2}", s)
    y = int(m.group(0)) if m else 9999
    return (y, 1 if is_f else 0, s)

@st.cache_data(show_spinner=False)
def load_data():
    df = read_csv_smart()
    df = build_display_year_column(df)
    if "Ticker" not in df.columns:
        for c in ["ticker","Mã CP","MaCP","Symbol"]:
            if c in df.columns:
                df["Ticker"] = df[c].astype(str)
                break
        else:
            df["Ticker"] = "SAMPLE"
    df["display_year"] = df["display_year"].astype(str)
    return df

df = load_data()
inject_global_css()
header("Financial Analytics", "Professional view")

# Sidebar
with st.sidebar:
    st.markdown("### Ticker")
    ticker = st.text_input("", value=df["Ticker"].iloc[0] if not df.empty else "")
    st.markdown("### Report")
    menu = st.radio("Select", ["Financial", "Sentiment", "Summary"], index=0, label_visibility="collapsed")

scoped = df[df["Ticker"] == ticker].copy()
unique_labels = list(pd.unique(scoped["display_year"]))
sorted_labels = sorted(unique_labels, key=sort_year_label)[-12:]
scoped = scoped[scoped["display_year"].isin(sorted_labels)]

# Optional KPI row at top (fake examples; wire with your real series)
kpi_row([
    {"title": "Net Revenue (last)", "value": f"{scoped.get('Net Revenue', pd.Series()).dropna().tail(1).astype(float).map('{:,.0f}'.format).iloc[0] if 'Net Revenue' in scoped.columns and not scoped['Net Revenue'].dropna().empty else '—'}"},
    {"title": "Gross Margin", "value": "—", "delta": "+0.4%"},
    {"title": "ROE", "value": "—", "delta": "-0.2%"},
])

# Main tabs delegating to your modules
if menu == "Financial":
    financial.render(scoped)
elif menu == "Sentiment":
    sentiment.render(scoped)
else:
    summary.render(scoped)
