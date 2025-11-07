# ui/layout.py
from __future__ import annotations
import os, io
import streamlit as st
import pandas as pd

# Where we look for your file (put it in one of these)
CSV_CANDIDATES = [
    "data/bctc_final.csv",
    "bctc_final.csv",
    "/mnt/data/bctc_final.csv",
]

DEFAULT_YEARS = 10

# ---------- Smart CSV loader (mirrors your working pattern) ----------
def read_csv_smart(path: str) -> pd.DataFrame:
    """
    Try common encodings first (like your working app). If columns=0,
    retry with common delimiters. Never treats .xlsx as CSV.
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"CSV not found at: {path}")

    # Guard: don't accept Excel accidentally renamed as .csv
    with open(path, "rb") as f:
        sig = f.read(4)
    if sig[:2] == b"PK":
        raise ValueError(
            "This file looks like an Excel workbook (.xlsx) renamed to .csv. "
            "Please save as real CSV (Comma delimited)."
        )

    # 1) Your working approach: try encodings
    for enc in ("utf-8-sig", "utf-8", "latin1", "cp1258"):
        try:
            df = pd.read_csv(path, encoding=enc)
            if df.shape[1] > 0:
                return df
        except Exception:
            pass

    # 2) If still no columns, sniff delimiter from text and re-read
    text = None
    for enc in ("utf-8-sig", "utf-8", "latin1", "cp1258"):
        try:
            with open(path, "r", encoding=enc, errors="ignore") as f:
                text = f.read()
            break
        except Exception:
            continue

    if not text or not text.strip():
        raise ValueError("CSV file is empty or whitespace only.")

    sample = "\n".join([ln for ln in text.splitlines() if ln.strip()][:100])
    delim_scores = {d: sample.count(d) for d in [",", ";", "\t", "|"]}
    best = max(delim_scores, key=delim_scores.get)
    if delim_scores[best] == 0:
        raise ValueError(
            "Cannot detect a CSV delimiter (tried ',', ';', TAB, '|'). "
            "Please export a proper CSV."
        )

    df = pd.read_csv(io.StringIO(text), sep=best)
    if df.shape[1] == 0:
        raise ValueError("Parsed text but found no columns in CSV.")
    return df

def _best_candidate_path() -> str:
    for p in CSV_CANDIDATES:
        if os.path.exists(p):
            return p
    raise FileNotFoundError(
        "CSV not found. Put bctc_final.csv at one of: " + ", ".join(CSV_CANDIDATES)
    )

def _normalize_cols(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out.columns = [str(c).strip() for c in out.columns]
    return out

def _pick_col(df: pd.DataFrame, candidates: list[str]) -> str | None:
    lower = {c.lower(): c for c in df.columns}
    for c in candidates:
        if c in df.columns:
            return c
        if c.lower() in lower:
            return lower[c.lower()]
    return None

@st.cache_data(show_spinner=False)
def load_financial_csv(path: str | None = None) -> pd.DataFrame:
    path = path or _best_candidate_path()
    df = read_csv_smart(path)
    df = _normalize_cols(df)

    # Map Ticker & Year (fall back to Period→Year)
    tick_col = _pick_col(df, ["Ticker", "ticker", "Symbol", "Code", "MaCK"])
    year_col = _pick_col(df, ["Year", "year", "Nam", "Năm"])
    per_col  = _pick_col(df, ["Period", "period", "Ky", "Kỳ"])

    if tick_col is None:
        raise ValueError("Column 'Ticker' (or Symbol/Code) is required in CSV.")

    if year_col is None:
        if per_col is not None:
            # Use first 4 chars as year (e.g., '2023Q4' → 2023)
            df["Year"] = pd.to_numeric(df[per_col].astype(str).str[:4], errors="coerce")
            year_col = "Year"
        else:
            raise ValueError("Column 'Year' not found and cannot be inferred from 'Period'.")

    if tick_col != "Ticker":
        df.rename(columns={tick_col: "Ticker"}, inplace=True)
    if year_col != "Year":
        df.rename(columns={year_col: "Year"}, inplace=True)

    df["Ticker"] = df["Ticker"].astype(str).str.upper().str.strip()
    df["Year"]   = pd.to_numeric(df["Year"], errors="coerce")

    df = df[df["Ticker"].astype(bool)]
    df = df[df["Year"].notna()]

    if df.empty:
        raise ValueError("No valid rows after normalizing Ticker/Year.")
    return df

@st.cache_data(show_spinner=False)
def list_tickers(path: str | None = None) -> list[str]:
    df = load_financial_csv(path)
    return sorted(df["Ticker"].dropna().astype(str).str.upper().unique().tolist())

def filter_by_ticker_years(df: pd.DataFrame, ticker: str, years: int = DEFAULT_YEARS) -> pd.DataFrame:
    t = (ticker or "").upper().strip()
    sub = df[df["Ticker"] == t].copy()
    if "Year" in sub.columns and sub["Year"].notna().any():
        sub = sub.sort_values("Year", ascending=False).head(years).sort_values("Year")
    return sub

def get_data(ticker: str, years: int = DEFAULT_YEARS) -> pd.DataFrame:
    df = load_financial_csv()
    return filter_by_ticker_years(df, ticker, years)

# ---------- Theme (English only, no emojis/icons) ----------
def inject_css_theme():
    st.markdown("""
    <style>
      .stApp { background:#f7f8fb; }
      .sidebar-title{ font-weight:700; font-size:18px; margin-bottom:6px; color:#111827; }
      .note { color:#6b7280; font-size:12px; }
      h1,h2,h3 { font-weight:700; }
    </style>
    """, unsafe_allow_html=True)

@st.cache_data(show_spinner=False)
def _cached_tickers() -> list[str]:
    return list_tickers()

def sidebar_inputs() -> str:
    with st.sidebar:
        st.markdown('<div class="sidebar-title">Ticker</div>', unsafe_allow_html=True)
        tickers = []
        try:
            tickers = _cached_tickers()
        except Exception as e:
            st.error(f"Cannot read tickers from CSV. Details: {e}")

        # Keep last choice, default to first if available
        if "ticker" not in st.session_state and tickers:
            st.session_state["ticker"] = tickers[0]

        ticker = st.selectbox(
            "Type to search…",
            options=tickers,
            index=(tickers.index(st.session_state.get("ticker")) if (tickers and st.session_state.get("ticker") in tickers) else 0),
            key="ticker",
            help="List is loaded from CSV; invalid codes are not allowed."
        )

        st.caption("Choose a ticker; tabs update automatically.")
        return ticker
