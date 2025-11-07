# ui/layout.py
from __future__ import annotations
import os, io, csv
import streamlit as st
import pandas as pd

# Thứ tự dò file CSV (đặt file vào 1 trong 3 nơi này là được)
CSV_CANDIDATES = [
    "data/bctc_final.csv",
    "bctc_final.csv",
    "/mnt/data/bctc_final.csv",
]
DEFAULT_YEARS = 10

# =============== CSV READER (không phụ thuộc core) ===============
def _looks_like_xlsx(path: str) -> bool:
    try:
        with open(path, "rb") as f:
            sig = f.read(4)
        # ZIP signature → .xlsx hoặc file Excel bị rename .csv
        return sig[:2] == b"PK"
    except Exception:
        return False

def _best_candidate_path() -> str:
    for p in CSV_CANDIDATES:
        if os.path.exists(p):
            return p
    # Nếu không thấy file nào:
    raise FileNotFoundError(
        "Không tìm thấy CSV. Hãy đặt file tại một trong các đường dẫn: "
        + ", ".join(CSV_CANDIDATES)
    )

@st.cache_data(show_spinner=False)
def _read_csv_robust_any(path: str) -> pd.DataFrame:
    if not os.path.exists(path):
        raise FileNotFoundError(f"CSV not found: {path}")
    if _looks_like_xlsx(path):
        raise ValueError(
            "File có vẻ là Excel (.xlsx) nhưng đặt đuôi .csv. "
            "Vui lòng xuất lại **CSV thật** từ Excel."
        )

    # 1) Thử đọc trực tiếp bằng pandas với engine='python' + auto-sniff sep
    encodings = ("utf-8-sig", "utf-8", "latin1", "cp1258")
    for enc in encodings:
        try:
            df = pd.read_csv(path, engine="python", sep=None, encoding=enc)
            if df.shape[1] > 0:
                return df
        except Exception:
            pass

    # 2) Đọc thô text và tự đếm delimiter
    text = None
    last_err = None
    for enc in encodings:
        try:
            with open(path, "r", encoding=enc, errors="ignore") as f:
                text = f.read()
            if text:
                break
        except Exception as e:
            last_err = e
            continue
    if not text:
        raise ValueError(f"Không đọc được nội dung CSV. Lỗi cuối: {last_err}")

    # Lấy vài dòng đầu để đếm dấu phân tách
    lines = [ln for ln in text.splitlines() if ln.strip()][:50]
    if not lines:
        raise ValueError("File CSV trống hoặc chỉ có khoảng trắng.")

    candidates = [",", ";", "\t", "|"]
    counts = {d: 0 for d in candidates}
    for ln in lines:
        for d in candidates:
            counts[d] += ln.count(d)
    # Chọn delimiter có số đếm lớn nhất
    best_sep = max(counts, key=counts.get)
    # Nếu không có dấu nào, thử coi như 1 cột (không phù hợp data bảng) → báo lỗi rõ
    if counts[best_sep] == 0:
        raise ValueError(
            "Không nhận thấy dấu phân tách phổ biến trong file. "
            "Hãy đảm bảo file là CSV thực (có dấu ',' ';' TAB hoặc '|')."
        )

    # 3) Thử parse lại với sep tốt nhất
    df = None
    for enc in encodings:
        try:
            df = pd.read_csv(io.StringIO(text), sep=best_sep, encoding=enc)
            if df.shape[1] > 0:
                return df
        except Exception as e:
            last_err = e
            continue

    raise ValueError(
        "Cannot parse CSV with common encodings/separators. "
        f"Last error: {last_err}"
    )

def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]
    return df

def _find_col(df: pd.DataFrame, candidates: list[str]) -> str | None:
    low = {c.lower(): c for c in df.columns}
    for c in candidates:
        if c in df.columns:
            return c
        if c.lower() in low:
            return low[c.lower()]
    return None

# =============== API thay thế core.data_access ===============
@st.cache_data(show_spinner=False)
def load_financial_csv(path: str | None = None) -> pd.DataFrame:
    path = path or _best_candidate_path()
    df = _read_csv_robust_any(path)
    df = _normalize_columns(df)

    # Bắt buộc có Ticker / Year (tự dò một số tên khác)
    tick_col = _find_col(df, ["Ticker", "ticker", "MaCK", "Symbol", "Code"])
    year_col = _find_col(df, ["Year", "year", "Nam", "Năm"])

    if tick_col is None:
        raise ValueError("CSV thiếu cột 'Ticker'.")
    if year_col is None:
        # Thử suy từ 'Period' → cắt 4 ký tự đầu
        per_col = _find_col(df, ["Period", "period", "Kỳ", "Ky"])
        if per_col is not None:
            df["Year"] = pd.to_numeric(df[per_col].astype(str).str[:4], errors="coerce")
            year_col = "Year"
        else:
            raise ValueError("CSV thiếu cột 'Year' và không suy được từ 'Period'.")

    if tick_col != "Ticker":
        df.rename(columns={tick_col: "Ticker"}, inplace=True)
    if year_col != "Year":
        df.rename(columns={year_col: "Year"}, inplace=True)

    df["Ticker"] = df["Ticker"].astype(str).str.upper().str.strip()
    df["Year"] = pd.to_numeric(df["Year"], errors="coerce")

    # Loại dòng không có ticker/year hợp lệ
    df = df[df["Ticker"].astype(bool)]
    df = df[df["Year"].notna()]
    if df.empty:
        raise ValueError("CSV không có bản ghi hợp lệ sau khi chuẩn hoá Ticker/Year.")

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
    df = load_financial_csv()  # tự dò file
    return filter_by_ticker_years(df, ticker, years)

# =============== Sidebar & selection flow ===============
def inject_css_theme():
    st.markdown("""
    <style>
      :root{ --brand:#0B74D0; }
      .stApp { background: #f7f8fb; }
      .sidebar-title{ font-weight:700; font-size:18px; margin-bottom:6px; color:#0f172a; }
      .pill{
        display:inline-flex; align-items:center; gap:8px;
        background:#fff; border:1px solid #e5e7eb; border-radius:999px;
        padding:6px 12px; margin:6px 0;
      }
      .pill .dot{width:8px;height:8px;border-radius:50%;background:#ef4444;}
      .stButton button{
        width:100%; height:42px; border-radius:10px; font-weight:700;
        background:var(--brand); color:#fff; border:0;
      }
      .stButton button:hover{ filter:brightness(0.95); }
      .section-h1{ font-size:24px; font-weight:800; margin:4px 0 10px 0; }
    </style>
    """, unsafe_allow_html=True)

@st.cache_data(show_spinner=False)
def _cached_list_tickers() -> list[str]:
    return list_tickers()

def sidebar_inputs() -> None:
    with st.sidebar:
        st.markdown('<div class="sidebar-title">Ticker</div>', unsafe_allow_html=True)

        # Nạp danh sách mã từ CSV
        try:
            tickers = _cached_list_tickers()
        except Exception as e:
            st.error(f"Không thể đọc danh sách mã từ CSV.\nChi tiết: {e}")
            tickers = []

        with st.form(key="query_form", clear_on_submit=False):
            ticker = st.selectbox(
                " ",
                options=tickers,
                index=0 if tickers else None,
                placeholder="Gõ để tìm nhanh (VD: HPG)",
                help="Danh sách gợi ý lấy trực tiếp từ file CSV",
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
            st.caption("Chọn mã & nhóm rồi nhấn **Xem báo cáo** để hiển thị nội dung.")

def get_active_selection() -> tuple[str, str]:
    if not st.session_state.get("_submitted"):
        st.stop()
    return st.session_state["_sel_ticker"], st.session_state["_sel_section"]
