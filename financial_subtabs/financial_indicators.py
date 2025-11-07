# financial_subtabs/financial_indicators.py
import unicodedata, re
from typing import List, Dict, Iterable, Optional
import numpy as np
import pandas as pd
import streamlit as st

# ---------------- Helpers ----------------
def _strip_accents(s:str) -> str:
    s = unicodedata.normalize("NFD", str(s))
    return "".join(ch for ch in s if unicodedata.category(ch) != "Mn")

def _canon(s:str) -> str:
    s = _strip_accents(s).lower()
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()

def _vn_to_float(x) -> float:
    """Convert '1.234.567,89' or '1 234 567' -> 1234567.89"""
    if pd.isna(x):
        return np.nan
    s = str(x).strip()
    # remove spaces
    s = s.replace(" ", "")
    # if looks like vi-locale (comma decimal), swap
    if re.search(r",\d{1,3}$", s) and s.count(",") == 1:
        s = s.replace(".", "").replace(",", ".")
    else:
        s = s.replace(",", "")
    try:
        return float(s)
    except Exception:
        return pd.to_numeric(x, errors="coerce")

def _ensure_numeric(s: pd.Series) -> pd.Series:
    return s.map(_vn_to_float)

def _sdiv(a: pd.Series, b: pd.Series) -> pd.Series:
    out = _ensure_numeric(a) / _ensure_numeric(b)
    return out.replace([np.inf, -np.inf], np.nan)

def _yearlike_columns(df: pd.DataFrame) -> List[str]:
    cols = []
    for c in df.columns:
        if re.fullmatch(r"\d{4}(?:[A-Z]?)", str(c)) or re.search(r"\d{4}", str(c)):
            cols.append(c)
    return cols

def _label_column(df: pd.DataFrame) -> Optional[str]:
    # pick a text-heavy, non-year column (the line-item/metric column)
    year_cols = set(_yearlike_columns(df))
    cand = [c for c in df.columns if c not in year_cols]
    if not cand:
        return None
    # choose the column with most distinct text labels
    best, bestn = None, -1
    for c in cand:
        ntext = df[c].astype(str).nunique()
        if ntext > bestn:
            best, bestn = c, ntext
    return best

# ---------------- Aliases ----------------
ALIASES: Dict[str, List[str]] = {
    # P&L
    "revenue": [
        "net revenue","revenue","net sales","sales",
        "doanh thu thuần","doanh thu"
    ],
    "cogs": [
        "cost of goods sold (cogs)","cost of goods sold","cogs",
        "gia von","giá vốn","giá vốn hàng bán"
    ],
    "gross_profit": ["gross profit","lợi nhuận gộp","loi nhuan gop"],
    "ebit": [
        "ebit","operating profit","operating income",
        "profit/(loss) from business activities",
        "profit from business activities",
        "lợi nhuận từ hoạt động kinh doanh","lợi nhuận hoạt động"
    ],
    "interest_expenses": [
        "interest expense","interest expenses",
        "interest expense on loans (vnd) (q)",
        "chi phí lãi vay","chi phi lai vay"
    ],
    "financial_expenses": [
        "financial expenses","chi phí tài chính","chi phi tai chinh"
    ],
    "net_income": [
        "net profit/(loss) after tax","net profit after tax",
        "profit after tax","lợi nhuận sau thuế","loi nhuan sau thue"
    ],
    "depreciation": [
        "depreciation","amortization",
        "depreciation of fixed assets and investment properties",
        "khấu hao","khau hao"
    ],
    # Balance sheet
    "current_assets": ["current assets","tài sản ngắn hạn","tai san ngan han","current assets (vnd)"],
    "cash": ["cash and cash equivalents","cash","tiền và tương đương tiền","tien va tuong duong tien"],
    "receivables": ["accounts receivable","trade receivables","phải thu","phai thu"],
    "inventory": ["inventory, net","inventory","inventories","hàng tồn kho","hang ton kho"],
    "current_liabilities": ["current liabilities","nợ ngắn hạn","no ngan han"],
    "total_assets": ["total assets","tổng tài sản","tong tai san"],
    "total_liabilities": ["liabilities","total liabilities","tổng nợ phải trả","tong no phai tra"],
    "equity": ["equity","owner's equity","vốn chủ sở hữu","von chu so huu"],
    "st_debt": ["short-term loans","short term loans","short term debt","short-term loans and financial lease payables"],
    "lt_debt": ["long-term loans","long term loans","long term debt","long-term loans and financial lease payables"],
    "ebitda": ["ebitda"],
    "total_debt": ["total debt","total interest bearing debt","tổng dư nợ","tong du no"],
}

# -------- column matching (wide) --------
def _match_columns(columns: Iterable[str], alias_list: List[str]) -> List[str]:
    canon_map = {_canon(c): c for c in columns}
    hits = []
    for raw in alias_list:
        key = _canon(raw)
        if key in canon_map:
            hits.append(canon_map[key]); continue
        # fuzzy contains
        for k, orig in canon_map.items():
            if key and key in k:
                hits.append(orig)
    # keep original order, unique
    seen, out = set(), []
    for c in columns:
        if c in hits and c not in seen:
            out.append(c); seen.add(c)
    return out

def _series_from_wide(df: pd.DataFrame, alias_key: str) -> pd.Series:
    hits = _match_columns(df.columns, ALIASES.get(alias_key, []))
    if not hits:
        return pd.Series(dtype=float)
    if len(hits) == 1:
        return _ensure_numeric(df[hits[0]]).rename(alias_key)
    return _ensure_numeric(df[hits]).sum(axis=1, skipna=True).rename(alias_key)

# -------- row matching (long) --------
def _row_match_index(idx: Iterable[str], alias_list: List[str]) -> Optional[str]:
    cmap = {_canon(i): i for i in idx}
    for raw in alias_list:
        key = _canon(raw)
        if key in cmap:
            return cmap[key]
        for k, orig in cmap.items():
            if key and key in k:
                return orig
    return None

def _series_from_long(df: pd.DataFrame, alias_key: str) -> pd.Series:
    years = _yearlike_columns(df)
    if not years:
        return pd.Series(dtype=float)
    label_col = _label_column(df)
    if not label_col:
        return pd.Series(dtype=float)
    idx_row = _row_match_index(df[label_col].astype(str).tolist(), ALIASES.get(alias_key, []))
    if not idx_row:
        return pd.Series(dtype=float)
    row = df[df[label_col].astype(str) == idx_row][years]
    if row.empty:
        return pd.Series(dtype=float)
    s = row.iloc[0]
    s = _ensure_numeric(s)
    s.name = alias_key
    s.index.name = "Year"
    return s

def _extract_series(fin_df: pd.DataFrame, alias_key: str) -> pd.Series:
    """Try wide first; if empty, try long."""
    # wide guess: years are the index already
    s = _series_from_wide(fin_df, alias_key)
    if s.size > 0 and not s.dropna().empty:
        return s
    # long format
    return _series_from_long(fin_df.reset_index(drop=True), alias_key)

def _total_debt(fin_df: pd.DataFrame) -> pd.Series:
    s = _extract_series(fin_df, "total_debt")
    if s.size > 0 and not s.dropna().empty:
        return s
    st_ = _extract_series(fin_df, "st_debt")
    lt_ = _extract_series(fin_df, "lt_debt")
    if st_.size or lt_.size:
        st_ = st_.reindex(sorted(set(st_.index) | set(lt_.index)))
        lt_ = lt_.reindex(st_.index)
        return (st_.add(lt_, fill_value=np.nan)).rename("total_debt")
    # fallback: total liabilities
    return _extract_series(fin_df, "total_liabilities").rename("total_debt")

def _ebitda(fin_df: pd.DataFrame) -> pd.Series:
    s = _extract_series(fin_df, "ebitda")
    if s.size > 0 and not s.dropna().empty:
        return s
    ebit = _extract_series(fin_df, "ebit")
    dep  = _extract_series(fin_df, "depreciation")
    if ebit.size and dep.size:
        return ebit.add(dep, fill_value=np.nan).rename("ebitda")
    return pd.Series(dtype=float)

# ------------- compute -------------
ORDER = [
    "Current Ratio","Quick Ratio","Working Capital to Total Assets",
    "Debt to Assets","Debt to Equity","Equity to Liabilities",
    "Long Term Debt to Assets","Net Debt to Equity",
    "Receivables Turnover","Inventory Turnover","Asset Turnover",
    "ROA","ROE","EBIT to Assets","Operating Income to Debt",
    "Net Profit Margin","Gross Margin","Interest Coverage",
    "EBITDA to Interest","Total Debt to EBITDA",
]

def compute_indicators(fin_df: pd.DataFrame) -> pd.DataFrame:
    # Base series (auto-align by year labels)
    revenue  = _extract_series(fin_df, "revenue")
    cogs     = _extract_series(fin_df, "cogs")
    gross_pf = _extract_series(fin_df, "gross_profit")
    if gross_pf.empty and revenue.size and cogs.size:
        gross_pf = revenue.sub(cogs, fill_value=np.nan).rename("gross_profit")

    ebit     = _extract_series(fin_df, "ebit")
    interest = _extract_series(fin_df, "interest_expenses")
    if interest.empty:
        # fallback: when only "Financial expenses" exists (still acceptable for coverage)
        interest = _extract_series(fin_df, "financial_expenses")

    net_inc  = _extract_series(fin_df, "net_income")

    ca   = _extract_series(fin_df, "current_assets")
    cash = _extract_series(fin_df, "cash")
    ar   = _extract_series(fin_df, "receivables")
    inv  = _extract_series(fin_df, "inventory")
    cl   = _extract_series(fin_df, "current_liabilities")
    ta   = _extract_series(fin_df, "total_assets")
    tl   = _extract_series(fin_df, "total_liabilities")
    eq   = _extract_series(fin_df, "equity")
    lt   = _extract_series(fin_df, "lt_debt")
    td   = _total_debt(fin_df)
    ebd  = _ebitda(fin_df)

    # Quick assets
    if ca.size and inv.size:
        qa = ca.sub(inv, fill_value=np.nan)
    elif cash.size and ar.size:
        qa = cash.add(ar, fill_value=np.nan)
    else:
        qa = pd.Series(dtype=float)

    metrics = {
        "Current Ratio": _sdiv(ca, cl),
        "Quick Ratio": _sdiv(qa, cl),
        "Working Capital to Total Assets": _sdiv(ca.sub(cl, fill_value=np.nan), ta),
        "Debt to Assets": _sdiv(td if td.size else tl, ta),
        "Debt to Equity": _sdiv(td if td.size else tl, eq),
        "Equity to Liabilities": _sdiv(eq, tl),
        "Long Term Debt to Assets": _sdiv(lt, ta),
        "Net Debt to Equity": _sdiv(td.sub(cash, fill_value=np.nan), eq),
        "Receivables Turnover": _sdiv(revenue, ar),
        "Inventory Turnover": _sdiv(cogs, inv),
        "Asset Turnover": _sdiv(revenue, ta),
        "ROA": _sdiv(net_inc, ta),
        "ROE": _sdiv(net_inc, eq),
        "EBIT to Assets": _sdiv(ebit, ta),
        "Operating Income to Debt": _sdiv(ebit, td if td.size else tl),
        "Net Profit Margin": _sdiv(net_inc, revenue),
        "Gross Margin": _sdiv(gross_pf, revenue),
        "Interest Coverage": _sdiv(ebit, interest),
        "EBITDA to Interest": _sdiv(ebd, interest),
        "Total Debt to EBITDA": _sdiv(td, ebd),
    }

    df = pd.DataFrame(metrics)
    # sort columns (years)
    labels = df.index.astype(str)
    year_num = pd.to_numeric(labels.str.extract(r"(\d{4})", expand=False), errors="coerce")
    df = df.assign(__sort_year__=year_num, __lbl__=labels).sort_values(["__sort_year__", "__lbl__"]).drop(columns="__sort_year__")
    df.index.name = "Year"

    view = df.T
    view = view.loc[[k for k in ORDER if k in view.index]]
    return view

# ------------- UI -------------
def render(fin_df: pd.DataFrame):
    st.subheader("FINANCIAL INDICATORS")
    view = compute_indicators(fin_df)
    if view.empty or view.columns.size == 0:
        st.info("No sufficient data to compute indicators. Please verify naming in your dataset.")
        return
    st.dataframe(view, use_container_width=True, hide_index=False)
