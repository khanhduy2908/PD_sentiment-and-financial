# ui/layout.py
from __future__ import annotations
import os
import streamlit as st

# dùng các hàm đọc/lọc dữ liệu đã có
from core.data_access import (
    list_tickers,           # trả về list mã từ CSV
    load_financial_long,    # đọc CSV robust
    filter_by_ticker_years  # lọc theo ticker + số năm
)

CSV_PATH_DEFAULT = "data/bctc_final.csv"
DEFAULT_YEARS = 10

# ====== THEME / CSS ======
def inject_css_theme():
    st.markdown("""
    <style>
      :root{
        --brand-blue:#0B74D0;  /* xanh dương */
        --brand-red:#B11A21;   /* đỏ đậm */
      }
      .stApp { background: #f6f7fb; }
      .sidebar-title{
        font-weight:700; font-size:18px; margin-bottom:6px; color:#111;
      }
      .sb-help { color:#65708a; font-size:12px; margin-top:-8px; }
      div[data-baseweb="select"] > div { border-radius:10px; border:1px solid #d7dbe6; }
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
      .section-h1{
        font-size:24px; font-weight:800; margin:4px 0 10px 0;
      }
    </style>
    """, unsafe_allow_html=True)


# ====== SIDEBAR FORM (không auto-run khi đổi lựa chọn) ======
@st.cache_data(show_spinner=False)
def _cached_list_tickers(csv_path: str) -> list[str]:
    # đọc cột ticker từ CSV -> list unique
    return list_tickers(csv_path)

def sidebar_inputs() -> None:
    """Render form trong sidebar; lưu kết quả vào session_state.
       Không return trực tiếp để tránh rerun sai thời điểm."""
    with st.sidebar:
        st.markdown('<div class="sidebar-title">Ticker</div>', unsafe_allow_html=True)
        # lấy danh sách mã từ CSV (autocomplete)
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
            st.markdown('<div class="sidebar-title" style="margin-top:14px;">Nhóm báo cáo</div>', unsafe_allow_html=True)
            section = st.selectbox(
                "Chọn nhóm",
                options=["Financial", "Sentiment", "Summary"],
                index=0,
            )
            submitted = st.form_submit_button("Xem báo cáo")

        # ghi session state khi submit
        if submitted:
            st.session_state["_sel_ticker"] = ticker
            st.session_state["_sel_section"] = section
            st.session_state["_submitted"] = True

        # hiển thị trạng thái hiện tại (nếu đã chọn)
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
    """Lấy ticker & section đã được submit. Nếu chưa có thì dừng app."""
    if not st.session_state.get("_submitted"):
        st.stop()
    return st.session_state["_sel_ticker"], st.session_state["_sel_section"]


# ====== DATA ACCESS tiện dùng ở app ======
def get_data(ticker: str, years: int = DEFAULT_YEARS):
    df = load_financial_long(CSV_PATH_DEFAULT)  # robust csv
    return filter_by_ticker_years(df, ticker, years)
