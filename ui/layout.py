# ui/layout.py
from __future__ import annotations
import os
import io
import csv
import streamlit as st
import pandas as pd

CSV_PATH_DEFAULT = "data/bctc_final.csv"
DEFAULT_YEARS = 10

# ===================== CSV reader (tự lực, không phụ thuộc core) =====================
@st.cache_data(show_spinner=False)
def _read_csv_robust(path: str) -> pd.DataFrame:
    if not os.path.exists(path):
        raise FileNotFoundError(f"CSV not found: {path}")

    # Thử các encoding phổ biến
    encodings = ("utf-8-sig", "utf-8", "latin1", "cp1258")
    seps = (",", ";", "\t", "|")

    # Nếu file “.csv” nhưng thực chất là Excel renaming → báo rõ
    with open(path, "rb") as f:
        head = f.read(4)
    # 0x50 0x4B “PK..” là zip/xlsx
    if head[:2] == b"PK":
        raise ValueError("This file looks like an Excel (.xlsx) renamed as .csv. Please export to real CSV.")

    last_err = None
    for enc in encodings:
        try:
            text = open(path, "r", encoding=enc, errors="ignore").read()
            # sniff delimiter
            try:
                dialect = csv.Sniffer().sniff(text[:4000], delimiters=";,|\t")
                sep = dialect.delimiter
            except Exception:
                # fallback
                sep = None

            if sep:
                df = pd.read_csv(io.StringIO(text), encoding=enc, sep=sep)
            else:
                # thử các sep phổ biến
                for s in seps:
                    try:
                        df = pd.read_csv(io.StringIO(text), encoding=enc, sep=s)
                        if df.shape[1] > 1:
                            break
                    except Exception:
                        continue
            if df is not None and df.shape[1] > 0:
                return df
        except Exception as e:
            last_err = e
            continue
    raise ValueError(f"Cannot parse CSV with common encodings/separators. Last error: {last_err}")

def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    # Chuẩn hoá tên cột để dễ dò
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]
    return df

def _col(df: pd.DataFrame, candidates: list[str]) -> str | None:
    low = {c.lower(): c for c in df.columns}
    for c in candidates:
        if c in df.columns:
            return c
        if c.lower() in low:
            return low[c.lower()]
    return None

# ===================== Public helpers (thay cho core.data_access) =====================
@st.cache_data(show_spinner=False)
def load_financial_csv(path: str = CSV_PATH_DEFAULT) -> pd.DataFrame:
    df = _read_csv_robust(path)
    df = _normalize_columns(df)
    # Map cột chuẩn cần dùng: Ticker / Year
    tick_col = _col(df, ["Ticker", "ticker", "MaCK", "Symbol"])
    year_col = _col(df, ["Year", "year", "Nam", "Năm"])
    if tick_col is None:
        raise ValueError("CSV is missing a 'Ticker' column.")
    if year_col is None:
        # cố gắng suy đoán từ kỳ (Period) nếu có
        per_col = _col(df, ["Period", "period"])
        if per_col is not None:
            df["Year"] = pd.to_numeric(df[per_col].astype(str).str[:4], errors="coerce")
            year_col = "Year"
        else:
            raise ValueError("CSV is missing a 'Year' column.")
    # Chuẩn tên 2 cột chính
    if tick_col != "Ticker":
        df.rename(columns={tick_col: "Ticker"}, inplace=True)
    if year_col != "Year":
        df.rename(columns={year_col: "Year"}, inplace=True)

    # ép kiểu
    df["Ticker"] = df["Ticker"].astype(str).str.upper().str.strip()
    df["Year"] = pd.to_numeric(df["Year"], errors="coerce")
    return df

@st.cache_data(show_spinner=False)
def list_tickers(path: str = CSV_PATH_DEFAULT) -> list[str]:
    df = load_financial_csv(path)
    ticks = sorted([t for t in df["Ticker"].dropna().astype(str).str.upper().unique().tolist() if t])
    return ticks

def filter_by_ticker_years(df: pd.DataFrame, ticker: str, years: int = DEFAULT_YEARS) -> pd.DataFrame:
    t = (ticker or "").upper().strip()
    sub = df[df["Ticker"] == t].copy()
    # Lọc N năm gần nhất (nếu có cột Year)
    if "Year" in sub.columns and sub["Year"].notna().any():
        sub = sub.sort_values("Year", ascending=False).head(years).sort_values("Year")
    return sub

def get_data(ticker: str, years: int = DEFAULT_YEARS) -> pd.DataFrame:
    df = load_financial_csv(CSV_PATH_DEFAULT)
    return filter_by_ticker_years(df, ticker, years)

# ===================== UI =====================
def inject_css_theme():
    st.markdown("""
    <style>
      :root{ --brand-blue:#0B74D0; --brand-red:#B11A21; }
      .stApp { background: #f6f7fb; }
      .sidebar-title{ font-weight:700; font-size:18px; margin-bottom:6px; color:#111; }
      .stButton button{
        width:100%; border-radius:10px; height:42px; font-weight:700;
        background:var(--brand-blue); color:white; border:0;
      }
      .stButton button:hover{ filter:brightness(0.95); }
      .pill{
        display:inline-flex; align-items:center; gap:8px;
        background:#fff; border:1px solid #e5e8f1; border-radius:999px;
        padding:6px 12px; margin:6px 0;
      }
      .pill .dot{width:8px;height:8px;border-radius:50%;background:var(--brand-red);}
      .section-h1{ font-size:24px; font-weight:800; margin:4px 0 10px 0; }
    </style>
    """, unsafe_allow_html=True)

@st.cache_data(show_spinner=False)
def _cached_list_tickers(csv_path: str) -> list[str]:
    return list_tickers(csv_path)

def sidebar_inputs() -> None:
    with st.sidebar:
        st.markdown('<div class="sidebar-title">Ticker</div>', unsafe_allow_html=True)
        try:
            tickers = _cached_list_tickers(CSV_PATH_DEFAULT)
        except Exception as e:
            st.error(f"Không thể đọc danh sách mã từ CSV.\nChi tiết: {e}")
            tickers = []

        with st.form(key="query_form", clear_on_submit=False):
            ticker = st.selectbox(
                " ",
                options=tickers,
                index=0 if tickers else None,
                placeholder="Gõ để tìm nhanh (VD: HPG)",
                help="Danh sách gợi ý lấy trực tiếp từ file data/bctc_final.csv",
                label_visibility="collapsed",
            )
            section = st.selectbox("Chọn nhóm", ["Financial", "Sentiment", "Summary"], index=0)
            submitted = st.form_submit_button("Xem báo cáo")

        if submitted:
            st.session_state["_sel_ticker"] = ticker
            st.session_state["_sel_section"] = section
            st.session_state["_submitted"] = True

        if st.session_state.get("_submitted"):
            t = st.session_state.get("_sel_ticker", "")
            s = st.session_state.get("_sel_section", "")
            st.markdown(
                f'<div class="pill"><span class="dot"></span>'
                f'<b>{t}</b>&nbsp;•&nbsp;{s}</div>', unsafe_allow_html=True
            )
        else:
            st.caption("Hãy chọn mã & nhóm báo cáo rồi nhấn **Xem báo cáo**.")

def get_active_selection() -> tuple[str, str]:
    if not st.session_state.get("_submitted"):
        st.stop()
    return st.session_state["_sel_ticker"], st.session_state["_sel_section"]
