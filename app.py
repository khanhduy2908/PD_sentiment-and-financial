# app.py
# Corporate Financial Dashboard — Premium UI (EN only, no icons)

import os
import pandas as pd
import streamlit as st

# =============================
# Safe imports from your utils/
# =============================
def _try_imports():
    read_csv_smart = None
    build_display_year_column = None
    sort_year_label = None
    try:
        from utils.io import read_csv_smart  # type: ignore
    except Exception:
        pass
    try:
        from utils.transforms import (  # type: ignore
            build_display_year_column,
            sort_year_label,
        )
    except Exception:
        pass
    return read_csv_smart, build_display_year_column, sort_year_label


READ_CSV_SMART, BUILD_YEAR_COL, SORT_YEAR_LABEL = _try_imports()

# Fallbacks if utils/ is missing or incomplete
def _fallback_build_display_year_column(df: pd.DataFrame) -> pd.DataFrame:
    """Create a stable 'display_year' column from the first valid of common year-like columns."""
    year_cols = ["Year", "year", "Năm", "nam", "display_year", "year_label"]
    for c in year_cols:
        if c in df.columns:
            out = df.copy()
            out["display_year"] = out[c].astype(str).str.extract(r"(\d{4})")[0]
            return out
    out = df.copy()
    out["display_year"] = ""
    return out


def _fallback_sort_year_label(y: str) -> tuple:
    """Sort key: numbers (YYYY) first by value asc, then anything else."""
    try:
        return (0, int(y), y)
    except Exception:
        return (1, 0, y)


def build_display_year_column(df: pd.DataFrame) -> pd.DataFrame:
    if BUILD_YEAR_COL is not None:
        try:
            return BUILD_YEAR_COL(df)
        except Exception:
            pass
    return _fallback_build_display_year_column(df)


def sort_year_label(y: str):
    if SORT_YEAR_LABEL is not None:
        try:
            return SORT_YEAR_LABEL(y)
        except Exception:
            pass
    return _fallback_sort_year_label(y)


# =============================
# Page config & global CSS
# =============================
st.set_page_config(
    page_title="Corporate Financial Dashboard",
    layout="wide",
    initial_sidebar_state="expanded",
)

def inject_global_css():
    st.markdown(
        """
        <style>
        /* Base */
        .block-container {padding-top: 1.0rem; padding-bottom: 1.0rem; max-width: 1400px;}
        html, body, [class*="css"] {font-family: Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;}

        /* Headings */
        h1, h2, h3 {font-weight: 700; letter-spacing: -0.02em;}
        .main-title {font-size: 28px; margin: 0 0 1rem 0;}
        .kpi-label {font-size: 13px; color: #6B7280; margin-bottom: .4rem;}
        .kpi-value {font-size: 18px; font-weight: 700; color: #111827;}

        /* Cards */
        .kpi-card {
            border: 1px solid #EEF2F7;
            border-radius: 16px;
            background: #FFFFFF;
            padding: 14px 16px;
        }

        /* Tabs-like nav (we render by sidebar report selector, so this styles general buttons if used) */
        .pill-btn > div > button {
            border-radius: 9999px !important;
            border: 1px solid #E5E7EB !important;
            background: #F9FAFB !important;
            color: #111827 !important;
            font-weight: 600 !important;
            padding: 8px 14px !important;
        }
        .pill-btn.active > div > button {
            background: #111827 !important;
            color: #FFFFFF !important;
            border-color: #111827 !important;
        }

        /* Sidebar header spacing */
        section[data-testid="stSidebar"] h2 {margin-top: .5rem;}
        </style>
        """,
        unsafe_allow_html=True,
    )


# =============================
# Data loading
# =============================
@st.cache_data(show_spinner=False)
def load_data() -> pd.DataFrame:
    """
    Load CSV from ./data/bctc_final.csv (preferred) or repository root fallback.
    Add 'display_year' and normalize Ticker if necessary.
    """
    df = None
    # First, try your helper if available
    if READ_CSV_SMART is not None:
        try:
            df = READ_CSV_SMART()
        except Exception:
            df = None

    # Fallback manual search
    if df is None:
        candidates = [
            "bctc_final.csv",
            os.path.join("data", "bctc_final.csv"),
        ]
        for p in candidates:
            if os.path.exists(p):
                try:
                    df = pd.read_csv(p)
                    break
                except Exception:
                    pass

    # If still not found, create an empty shell so app still runs
    if df is None:
        df = pd.DataFrame(
            columns=[
                "Ticker",
                "display_year",
                "Net Revenue",
                "Gross Profit",
                "COGS",
                "ROE",
            ]
        )

    # Normalize year column
    df = build_display_year_column(df)

    # Ensure Ticker column exists
    if "Ticker" not in df.columns:
        for c in ["ticker", "Mã CP", "MaCP", "Symbol"]:
            if c in df.columns:
                df = df.rename(columns={c: "Ticker"})
                break
        else:
            df["Ticker"] = "SAMPLE"

    # Force types
    df["Ticker"] = df["Ticker"].astype(str).str.upper().str.strip()
    df["display_year"] = df["display_year"].astype(str).str.extract(r"(\d{4})")[0]

    return df


# =============================
# Helpers
# =============================
def build_ticker_list(df: pd.DataFrame) -> list[str]:
    if "Ticker" not in df.columns:
        return []
    vals = (
        df["Ticker"]
        .astype(str)
        .str.upper()
        .str.strip()
        .replace({"": pd.NA})
        .dropna()
        .unique()
        .tolist()
    )
    vals.sort()
    return vals

def kpi_series(df: pd.DataFrame, alias_list: list[str]) -> pd.Series:
    """Return the first matching numeric series based on a list of aliases."""
    if df.empty:
        return pd.Series(dtype=float)
    hits = []
    lower = {c.lower(): c for c in df.columns}
    for a in alias_list:
        c = lower.get(a.lower())
        if c:
            hits.append(c)
    if not hits:
        return pd.Series(dtype=float)
    ser = pd.to_numeric(df[hits[0]], errors="coerce")
    return ser

def get_latest_value(df: pd.DataFrame, value_aliases: list[str]) -> str:
    if df.empty:
        return "—"
    # Pick latest year row
    if "display_year" not in df.columns:
        return "—"
    local = df.copy()
    local = local[local["display_year"].str.len() > 0]
    if local.empty:
        return "—"
    local["__sort__"] = local["display_year"].map(sort_year_label)
    local = local.sort_values("__sort__", ascending=False)
    ser = kpi_series(local, value_aliases)
    if ser.empty:
        return "—"
    val = ser.iloc[0]
    try:
        if pd.isna(val):
            return "—"
        # nice number format
        if abs(val) >= 1e3:
            return f"{val:,.0f}"
        return f"{val:,.2f}"
    except Exception:
        return "—"

def get_latest_pct(df: pd.DataFrame, num_aliases: list[str], den_aliases: list[str]) -> str:
    if df.empty:
        return "—"
    if "display_year" not in df.columns:
        return "—"
    local = df.copy()
    local = local[local["display_year"].str.len() > 0]
    if local.empty:
        return "—"
    local["__sort__"] = local["display_year"].map(sort_year_label)
    local = local.sort_values("__sort__", ascending=False)

    num = kpi_series(local, num_aliases)
    den = kpi_series(local, den_aliases)
    if num.empty or den.empty:
        return "—"
    val = None
    try:
        if den.iloc[0] and pd.notna(den.iloc[0]) and float(den.iloc[0]) != 0:
            val = float(num.iloc[0]) / float(den.iloc[0])
    except Exception:
        val = None
    if val is None or pd.isna(val):
        return "—"
    return f"{val*100:.1f}%"

# =============================
# Import section renderers
# =============================
try:
    from tabs import financial, sentiment, summary  # type: ignore
except Exception:
    financial = sentiment = summary = None


# =============================
# Sidebar controls
# =============================
def report_selector() -> str:
    if "report_mode" not in st.session_state:
        st.session_state["report_mode"] = "Financial"

    # Prefer segmented control if available
    try:
        selected = st.segmented_control(
            "Report",
            options=["Financial", "Sentiment", "Summary"],
            default=st.session_state["report_mode"],
            key="seg_report",
        )
        st.session_state["report_mode"] = selected
        return selected
    except Exception:
        # Fallback to 3 pill buttons
        st.markdown(
            """
            <style>
            .pill-btn > div > button {
                border-radius: 9999px;
                border: 1px solid #E5E7EB;
                background: #F9FAFB;
                color: #111827;
                font-weight: 600;
                padding: 0.5rem 0.75rem;
            }
            .pill-btn.active > div > button {
                background: #111827;
                color: #FFFFFF;
                border-color: #111827;
            }
            </style>
            """,
            unsafe_allow_html=True,
        )
        cols = st.columns(3)
        labels = ["Financial", "Sentiment", "Summary"]
        for i, label in enumerate(labels):
            active = st.session_state["report_mode"] == label
            with cols[i]:
                box = st.container()
                box.markdown(
                    f'<div class="pill-btn {"active" if active else ""}">',
                    unsafe_allow_html=True,
                )
                if st.button(label, use_container_width=True, key=f"report_{label}"):
                    st.session_state["report_mode"] = label
                box.markdown("</div>", unsafe_allow_html=True)
        return st.session_state["report_mode"]


# =============================
# App body
# =============================
inject_global_css()
df = load_data()

with st.sidebar:
    st.header("Ticker")

    tickers = build_ticker_list(df)
    # If you want default, pick first item or keep empty
    default_index = 0 if tickers else None

    # Single selectbox with built-in type-to-filter dropdown (matches your screenshot)
    selected_ticker = st.selectbox(
        "Ticker",
        options=tickers if tickers else ["SAMPLE"],
        index=default_index,
        placeholder="Type to filter (e.g., HPG, VNM, FPT)",
        label_visibility="collapsed",
    )

    st.markdown("---")
    st.header("Report")
    report_tab = report_selector()

# Scope data by ticker and recent years
scoped = df[df["Ticker"] == selected_ticker].copy()
if "display_year" in scoped.columns:
    # keep up to last 10 distinct years
    yrs = (
        scoped["display_year"]
        .dropna()
        .astype(str)
        .unique()
        .tolist()
    )
    yrs = sorted(yrs, key=sort_year_label)
    recent = yrs[-10:]
    scoped = scoped[scoped["display_year"].astype(str).isin(recent)]

# Title
st.markdown('<div class="main-title">Corporate Financial Dashboard</div>', unsafe_allow_html=True)

# KPI row
k1, k2, k3 = st.columns(3)
with k1:
    st.markdown('<div class="kpi-card">', unsafe_allow_html=True)
    st.markdown('<div class="kpi-label">Net Revenue (last)</div>', unsafe_allow_html=True)
    rev = get_latest_value(scoped, ["Net Revenue", "Revenue", "Doanh thu", "NetRevenue"])
    st.markdown(f'<div class="kpi-value">{rev}</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

with k2:
    st.markdown('<div class="kpi-card">', unsafe_allow_html=True)
    st.markdown('<div class="kpi-label">Gross Margin</div>', unsafe_allow_html=True)
    gm = get_latest_pct(scoped, ["Gross Profit", "GrossProfit", "Lợi nhuận gộp"], ["Net Revenue", "Revenue", "Doanh thu"])
    st.markdown(f'<div class="kpi-value">{gm}</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

with k3:
    st.markdown('<div class="kpi-card">', unsafe_allow_html=True)
    st.markdown('<div class="kpi-label">ROE</div>', unsafe_allow_html=True)
    roe = get_latest_value(scoped, ["ROE", "Return on Equity"])
    st.markdown(f'<div class="kpi-value">{roe}</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

st.markdown("")

# Render ONE section based on sidebar selection (avoid double tabs issue)
if report_tab == "Financial":
    if financial is not None:
        financial.render(scoped)
    else:
        st.info("Financial module not found.")
elif report_tab == "Sentiment":
    if sentiment is not None:
        sentiment.render(scoped)
    else:
        st.info("Sentiment module not found.")
else:  # Summary
    if summary is not None:
        summary.render(scoped)
    else:
        st.info("Summary module not found.")
