# financial_subtabs/financial_indicators.py
import unicodedata
import re
from typing import List, Dict, Iterable
import numpy as np
import pandas as pd
import streamlit as st

# -------------------------------
# 0) Helpers: normalization & safe math
# -------------------------------
def _strip_accents(s: str) -> str:
    try:
        s = unicodedata.normalize("NFD", s)
        s = "".join(ch for ch in s if unicodedata.category(ch) != "Mn")
    except Exception:
        pass
    return s

def _canon(s: str) -> str:
    if s is None:
        return ""
    s = str(s)
    s = _strip_accents(s)
    s = s.lower()
    s = re.sub(r"[^a-z0-9]+", " ", s)  # keep letters/digits, collapse others
    s = re.sub(r"\s+", " ", s).strip()
    return s

def _ensure_numeric_frame(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for c in out.columns:
        out[c] = pd.to_numeric(out[c], errors="coerce")
    return out.replace([np.inf, -np.inf], np.nan)

def _ensure_numeric_series(s: pd.Series) -> pd.Series:
    return pd.to_numeric(s, errors="coerce").replace([np.inf, -np.inf], np.nan)

def _sdiv(a: pd.Series, b: pd.Series) -> pd.Series:
    """Safe divide aligned on index."""
    a = _ensure_numeric_series(a)
    b = _ensure_numeric_series(b)
    out = a / b
    out.replace([np.inf, -np.inf], np.nan, inplace=True)
    return out

# -------------------------------
# 1) Year column & base shaping
# -------------------------------
def _year_col(df: pd.DataFrame) -> str:
    candidates = ["display_year", "year_label", "year", "Year", "FY", "fy"]
    lower_map = {c.lower(): c for c in df.columns}
    for c in candidates:
        if c in df.columns:
            return c
        if c.lower() in lower_map:
            return lower_map[c.lower()]
    # Fallback: try any column that looks like a year label
    for c in df.columns:
        vc = df[c].astype(str).str.fullmatch(r"\d{4}[A-Z]?").sum()
        if vc >= max(1, int(0.5 * len(df))):
            return c
    # last resort: create sequential index as year
    return None

def _build_base(fin_df: pd.DataFrame) -> pd.DataFrame:
    """
    Returns a wide frame indexed by year (ascending) with all original columns preserved.
    If multiple rows per year exist, keeps the last one.
    """
    ycol = _year_col(fin_df)
    if ycol is None:
        # fabricate a year index if truly absent
        tmp = fin_df.copy()
        tmp["__year__"] = pd.to_numeric(tmp.get("Year", tmp.index), errors="coerce")
        base = tmp.drop_duplicates(subset=["__year__"]).set_index("__year__").sort_index()
        base.index.name = "Year"
        return base
    base = fin_df.drop_duplicates(subset=[ycol]).copy()
    base[ycol] = base[ycol].astype(str)
    # normalize labels like "2024F" → "2024F" (keep as label), but sort by numeric part
    # extract numeric prefix for sorting
    sort_key = base[ycol].str.extract(r"(\d{4})", expand=False).astype(float)
    base = base.assign(__sort_year__=sort_key).sort_values(["__sort_year__", ycol])
    base = base.drop(columns="__sort_year__")
    base = base.set_index(ycol)
    return base

# -------------------------------
# 2) Alias dictionary
# -------------------------------
# Define flexible alias lists. Add more if your CSV uses different headers.
ALIASES: Dict[str, List[str]] = {
    # Income / margins
    "revenue": [
        "net revenue", "revenue", "net sales", "sales", "doanh thu", "doanh thu thuần"
    ],
    "cogs": [
        "cost of goods sold", "cogs", "gia von", "giá vốn", "giá vốn hàng bán"
    ],
    "gross_profit": [
        "gross profit", "loi nhuan gop", "lợi nhuận gộp"
    ],
    "financial_income": [
        "financial income", "financial revenue", "thu nhap tai chinh", "doanh thu tai chinh"
    ],
    "financial_expenses": [
        "financial expenses", "chi phi tai chinh"
    ],
    "ebit": [
        "ebit", "operating profit", "operating income", "profit from business activities",
        "loi nhuan hoat dong", "loi nhuan tu hoat dong kinh doanh",
        "profit loss from business activities"
    ],
    "interest_expenses": [
        "interest expense", "interest expenses", "interest paid", "chi phi lai vay"
    ],
    "net_income": [
        "net profit after tax", "profit after tax", "net profit loss after tax",
        "loi nhuan sau thue", "loi nhuan ròng", "net income"
    ],
    "other_income": [
        "other income", "other income net"
    ],
    "tax_expense": [
        "corporate income tax expense", "income tax expense", "thue thu nhap doanh nghiep"
    ],
    "depreciation": [
        "depreciation", "amortization", "depreciation of fixed assets",
        "khau hao", "khấu hao"
    ],
    # Balance sheet core
    "current_assets": [
        "current assets", "tai san ngan han"
    ],
    "cash": [
        "cash and cash equivalents", "cash", "tien va tuong duong tien", "tiền"
    ],
    "receivables": [
        "accounts receivable", "trade receivables", "phai thu", "phải thu"
    ],
    "inventory": [
        "inventory", "inventories", "hang ton kho", "hàng tồn kho"
    ],
    "current_liabilities": [
        "current liabilities", "no ngan han", "nợ ngắn hạn"
    ],
    "total_assets": [
        "total assets", "tong tai san", "tổng tài sản"
    ],
    "total_liabilities": [
        "total liabilities", "tong no phai tra", "tổng nợ phải trả"
    ],
    "equity": [
        "equity", "owner s equity", "owner's equity", "von chu so huu", "vốn chủ sở hữu"
    ],
    "st_debt": [
        "short term loans", "short term borrowings", "short term debt",
        "short term loans and financial lease payables", "no vay ngan han"
    ],
    "lt_debt": [
        "long term loans", "long term borrowings", "long term debt",
        "long term loans and financial lease payables", "no vay dai han"
    ],
    # Optional helpful aliases
    "ebitda": [
        "ebitda"
    ],
    "total_debt": [
        "total debt", "tong du no", "total interest bearing debt"
    ],
}

# Precompile canonical map for faster matching
def _build_col_lookup(columns: Iterable[str]) -> Dict[str, str]:
    return {_canon(c): c for c in columns}

def _match_columns(columns: Iterable[str], alias_list: List[str]) -> List[str]:
    """Return concrete column names in 'columns' that match any alias pattern."""
    canon_map = _build_col_lookup(columns)
    hits = []
    for raw in alias_list:
        key = _canon(raw)
        # exact canonical match
        if key in canon_map:
            hits.append(canon_map[key])
            continue
        # loose contains match (word boundaries)
        for ccanon, orig in canon_map.items():
            if key and key in ccanon:
                hits.append(orig)
    # keep unique, preserve original order of the DataFrame columns
    uniq = []
    seen = set()
    for c in columns:
        if c in hits and c not in seen:
            uniq.append(c)
            seen.add(c)
    return uniq

def _get_series_from_alias(base: pd.DataFrame, alias_key: str) -> pd.Series:
    """Sum across all columns that match the alias list (wide format)."""
    alias = ALIASES.get(alias_key, [])
    hits = _match_columns(base.columns, alias)
    if not hits:
        return pd.Series(dtype=float)
    if len(hits) == 1:
        return _ensure_numeric_series(base[hits[0]]).rename(alias_key)
    # sum multiple numeric columns
    ser = _ensure_numeric_frame(base[hits]).sum(axis=1, skipna=True).rename(alias_key)
    return ser

def _coalesce(*series: Iterable[pd.Series]) -> pd.Series:
    """Return the first non-empty series (by length)."""
    for s in series:
        if isinstance(s, pd.Series) and s.size > 0:
            return s
    return pd.Series(dtype=float)

# -------------------------------
# 3) Compute indicators
# -------------------------------
def _total_debt(base: pd.DataFrame) -> pd.Series:
    """Prefer explicit total_debt; else sum st_debt + lt_debt; else fallback to total_liabilities."""
    td = _get_series_from_alias(base, "total_debt")
    if not td.empty:
        return td
    sd = _get_series_from_alias(base, "st_debt")
    ld = _get_series_from_alias(base, "lt_debt")
    if not sd.empty or not ld.empty:
        sd = sd.reindex(base.index, fill_value=np.nan)
        ld = ld.reindex(base.index, fill_value=np.nan)
        return (sd.add(ld, fill_value=np.nan)).rename("total_debt")
    # last resort
    tl = _get_series_from_alias(base, "total_liabilities")
    return tl.rename("total_debt")

def _ebitda(base: pd.DataFrame) -> pd.Series:
    ebitda = _get_series_from_alias(base, "ebitda")
    if not ebitda.empty:
        return ebitda
    ebit = _get_series_from_alias(base, "ebit")
    dep  = _get_series_from_alias(base, "depreciation")
    if ebit.empty or dep.empty:
        # Try reconstruct from financial income/expenses if needed (conservative)
        return pd.Series(dtype=float)
    out = ebit.add(dep, fill_value=np.nan).rename("ebitda")
    return out

def compute_indicators(fin_df: pd.DataFrame) -> pd.DataFrame:
    base = _build_base(fin_df)

    # Pull essentials
    revenue   = _get_series_from_alias(base, "revenue")
    cogs      = _get_series_from_alias(base, "cogs")
    gross_p   = _get_series_from_alias(base, "gross_profit")
    ebit      = _get_series_from_alias(base, "ebit")
    interest  = _get_series_from_alias(base, "interest_expenses")
    net_inc   = _get_series_from_alias(base, "net_income")

    curr_assets = _get_series_from_alias(base, "current_assets")
    cash       = _get_series_from_alias(base, "cash")
    recv       = _get_series_from_alias(base, "receivables")
    inv        = _get_series_from_alias(base, "inventory")

    curr_liab  = _get_series_from_alias(base, "current_liabilities")
    tot_assets = _get_series_from_alias(base, "total_assets")
    tot_liab   = _get_series_from_alias(base, "total_liabilities")
    equity     = _get_series_from_alias(base, "equity")

    st_debt    = _get_series_from_alias(base, "st_debt")
    lt_debt    = _get_series_from_alias(base, "lt_debt")
    tot_debt   = _total_debt(base)
    ebitda     = _ebitda(base)

    # Fallbacks used in some ratios
    if gross_p.empty and not revenue.empty and not cogs.empty:
        gross_p = (revenue - cogs).rename("gross_profit")

    # Quick Assets best-effort
    if not curr_assets.empty and not inv.empty:
        quick_assets = curr_assets - inv
    elif not cash.empty and not recv.empty:
        quick_assets = cash.add(recv, fill_value=np.nan)
    else:
        quick_assets = pd.Series(dtype=float)

    # Indicators
    indicators = {}

    indicators["Current Ratio"] = _sdiv(curr_assets, curr_liab)
    indicators["Quick Ratio"] = _sdiv(quick_assets, curr_liab)
    indicators["Working Capital to Total Assets"] = _sdiv(curr_assets - curr_liab, tot_assets)

    # Capital structure
    # Prefer total liabilities for Debt/Assets; for Debt/Equity we prefer interest-bearing debt
    indicators["Debt to Assets"] = _coalesce(_sdiv(tot_liab, tot_assets), _sdiv(tot_debt, tot_assets))
    indicators["Debt to Equity"] = _coalesce(_sdiv(tot_debt, equity), _sdiv(tot_liab, equity))
    indicators["Equity to Liabilities"] = _sdiv(equity, tot_liab)
    indicators["Long Term Debt to Assets"] = _sdiv(lt_debt, tot_assets)
    indicators["Net Debt to Equity"] = _sdiv(tot_debt - cash, equity)

    # Efficiency
    indicators["Receivables Turnover"] = _sdiv(revenue, recv)   # year-end approx if no average
    indicators["Inventory Turnover"]   = _sdiv(cogs, inv)       # year-end approx if no average
    indicators["Asset Turnover"]       = _sdiv(revenue, tot_assets)

    # Profitability
    indicators["ROA"]                 = _sdiv(net_inc, tot_assets)
    indicators["ROE"]                 = _sdiv(net_inc, equity)
    indicators["EBIT to Assets"]      = _sdiv(ebit, tot_assets)
    indicators["Operating Income to Debt"] = _coalesce(_sdiv(ebit, tot_debt), _sdiv(ebit, tot_liab))
    indicators["Net Profit Margin"]   = _sdiv(net_inc, revenue)
    indicators["Gross Margin"]        = _sdiv(gross_p, revenue)

    # Coverage
    indicators["Interest Coverage"]   = _sdiv(ebit, interest)
    indicators["EBITDA to Interest"]  = _sdiv(ebitda, interest)
    indicators["Total Debt to EBITDA"]= _sdiv(tot_debt, ebitda)

    # Assemble table: rows = indicator, cols = years (ascending by numeric core)
    df_out = pd.DataFrame(indicators)
    # df_out currently indexed by year labels; ensure sensible sorting by numeric prefix
    idx = pd.Index(df_out.index.astype(str), name="Year")
    sort_key = idx.to_series().str.extract(r"(\d{4})", expand=False).astype(float)
    df_out = df_out.assign(__sort_year__=sort_key).sort_values(["__sort_year__", "Year"])
    df_out = df_out.drop(columns="__sort_year__")

    # transpose: rows=indicators, cols=years
    view = df_out.T

    # Nice order required by you
    desired_order = [
        "Current Ratio",
        "Quick Ratio",
        "Working Capital to Total Assets",
        "Debt to Assets",
        "Debt to Equity",
        "Equity to Liabilities",
        "Long Term Debt to Assets",
        "Net Debt to Equity",
        "Receivables Turnover",
        "Inventory Turnover",
        "Asset Turnover",
        "ROA",
        "ROE",
        "EBIT to Assets",
        "Operating Income to Debt",
        "Net Profit Margin",
        "Gross Margin",
        "Interest Coverage",
        "EBITDA to Interest",
        "Total Debt to EBITDA",
    ]
    # keep only those computed
    ordered = [k for k in desired_order if k in view.index]
    view = view.loc[ordered]

    # Optional: format ratios to 4 decimals; leave intensity/turnovers raw.
    # To keep numeric for download/sort, do not cast to strings here.
    return view

# -------------------------------
# 4) Streamlit renderer
# -------------------------------
def render(fin_df: pd.DataFrame):
    st.subheader("FINANCIAL INDICATORS")

    view = compute_indicators(fin_df)
    if view.empty:
        st.info("No sufficient data to compute indicators. Please verify column names in the dataset.")
        return

    # Display
    st.dataframe(
        view,
        use_container_width=True,
        hide_index=False
    )
