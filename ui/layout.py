# ui/layout.py
from __future__ import annotations
import os, io
import streamlit as st
import pandas as pd

CSV_CANDIDATES = [
    "data/bctc_final.csv",
    "bctc_final.csv",
    "/mnt/data/bctc_final.csv",
]
DEFAULT_YEARS = 10

# ---------- Internal helpers ----------
def _looks_like_xlsx(path: str) -> bool:
    try:
        with open(path, "rb") as f:
            sig = f.read(4)
        return sig[:2] == b"PK"  # likely an .xlsx renamed to .csv
    except Exception:
        return False

def _best_candidate_path() -> str:
    for p in CSV_CANDIDATES:
        if os.path.exists(p):
            return p
    raise FileNotFoundError(
        "CSV not found. Put the file at one of: " + ", ".join(CSV_CANDIDATES)
    )

@st.cache_data(show_spinner=False)
def _read_csv_super_robust(path: str) -> pd.DataFrame:
    """Read CSV robustly; fail with clear messages if not a true CSV."""
    if not os.path.exists(path):
        raise FileNotFoundError(f"CSV does not exist: {path}")

    if _looks_like_xlsx(path):
        raise ValueError(
            "The file appears to be an Excel workbook (.xlsx) renamed to .csv. "
            "Please open it and Save As → CSV (Comma delimited)."
        )

    encodings = ("utf-8-sig", "utf-8", "cp1258", "latin1")

    # 1) Let pandas sniff the delimiter
    for enc in encodings:
        try:
            df = pd.read_csv(path, engine="python", sep=None, encoding=enc)
            if df.shape[1] > 0:
                return df
        except Exception:
            pass

    # 2) Manual delimiter detection
    text = None
    for enc in encodings:
        try:
            with open(path, "r", encoding=enc, errors="ignore") as f:
                text = f.read()
            break
        except Exception:
            continue

    if not text or not text.strip():
        raise ValueError("CSV is empty or whitespace only.")

    lines = [ln for ln in text.splitlines() if ln.strip()][:60]
    cands = [",", ";", "\t", "|"]
    counts = {d: 0 for d in cands}
    for ln in lines:
        for d in cands:
            counts[d] += ln.count(d)

    best_sep = max(counts, key=counts.get)
    if counts[best_sep] == 0:
        raise ValueError(
            "Could not detect a common delimiter (',', ';', TAB, '|'). "
            "Please export a proper CSV."
        )

    try:
        df = pd.read_csv(io.StringIO(text), sep=best_sep)
        if df.shape[1] == 0:
            raise ValueError("Parsed but no valid columns found.")
        return df
    except Exception as e:
        raise ValueError(f"Cannot parse CSV. Last error: {e}")

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

# ---------- Public data API (no core/* dependencies) ----------
@st.cache_data(show_spinner=False)
def load_financial_csv(path: str | None = None) -> pd.DataFrame:
    path = path or _best_candidate_path()
    df = _read_csv_super_robust(path)
    df = _normalize_cols(df)

    # Require Ticker & Year (infer Year from Period if needed)
    tick_col = _pick_col(df, ["Ticker", "ticker", "Symbol", "MaCK", "Code"])
    year_col = _pick_col(df, ["Year", "year", "Nam", "Năm"])
    if tick_col is None:
        raise ValueError("Column 'Ticker' is required in CSV.")
    if year_col is None:
        per_col = _pick_col(df, ["Period", "period", "Ky", "Kỳ"])
        if per_col is not None:
            df["Year"] = pd.to_numeric(df[per_col].astype(str).str[:4], errors="coerce")
            year_col = "Year"
        else:
            raise ValueError("Column 'Year' not found and cannot be inferred from 'Period'.")

    if tick_col != "Ticker":
        df.rename(columns={tick_col: "Ticker"}, inplace=True)
    if year_col != "Year":
        df.rename(columns={year_col: "Year"}, inplace=True)

    df["Ticker"] = df["Ticker"].astype(str).str.upper().str.strip()
    df["Year"] = pd.to_numeric(df["Year"], errors="coerce")
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

# ---------- Theme/CSS (no icons/emojis) ----------
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
        try:
            tickers = _cached_tickers()
        except Exception as e:
            st.error(f"Cannot read tickers from CSV. Details: {e}")
            tickers = []

        if "ticker" not in st.session_state and tickers:
            st.session_state["ticker"] = tickers[0]

        ticker = st.selectbox(
            "Type to search…",
            options=tickers,
            index=(tickers.index(st.session_state.get("ticker")) if (tickers and st.session_state.get("ticker") in tickers) else 0),
            key="ticker",
            help="The list comes directly from CSV; free typing is disabled to prevent invalid codes."
        )

        st.caption("Select a ticker; the dashboard updates automatically.")
        return ticker
