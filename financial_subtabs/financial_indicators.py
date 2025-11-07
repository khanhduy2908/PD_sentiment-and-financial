# financial_subtabs/financial_indicators.py
import unicodedata
import re
from typing import List, Dict, Iterable
import numpy as np
import pandas as pd
import streamlit as st

# -------------------------------
# Helpers
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
    s = _strip_accents(s).lower()
    s = re.sub(r"[^a-z0-9]+", " ", s)
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
    a = _ensure_numeric_series(a)
    b = _ensure_numeric_series(b)
    out = a / b
    out.replace([np.inf, -np.inf], np.nan, inplace=True)
    return out

# -------------------------------
# Year column & base shaping
# -------------------------------
def _year_col(df: pd.DataFrame) -> str | None:
    candidates = ["display_year", "year_label", "year", "Year", "FY", "fy"]
    lower_map = {c.lower(): c for c in df.columns}
    for c in candidates:
        if c in df.columns:
            return c
        if c.lower() in lower_map:
            return lower_map[c.lower()]
    for c in df.columns:
        vc = df[c].astype(str).str.fullmatch(r"\d{4}[A-Z]?").sum()
        if vc >= max(1, int(0.5 * len(df))):
            return c
    return None

def _build_base(fin_df: pd.DataFrame) -> pd.DataFrame:
    ycol = _year_col(fin_df)
    if ycol is None:
        tmp = fin_df.copy()
        tmp["__year__"] = pd.to_numeric(tmp.get("Year", tmp.index), errors="coerce")
        base = tmp.drop_duplicates(subset=["__year__"]).set_index("__year__").sort_index()
        base.index.name = "Year"
        return base
    base = fin_df.drop_duplicates(subset=[ycol]).copy()
    base[ycol] = base[ycol].astype(str)
    sort_key = base[ycol].str.extract(r"(\d{4})", expand=False).astype(float)
    base = base.assign(__sort_year__=sort_key).sort_values(["__sort_year__", ycol])
    base = base.drop(columns="__sort_year__").set_index(ycol)
    return base

# -------------------------------
# Aliases
# -------------------------------
ALIASES: Dict[str, List[str]] = {
    "revenue": ["net revenue", "revenue", "net sales", "sales", "doanh thu", "doanh thu thuần"],
    "cogs": ["cost of goods sold", "cogs", "gia von", "giá vốn", "giá vốn hàng bán"],
    "gross_profit": ["gross profit", "loi nhuan gop", "lợi nhuận gộp"],
    "financial_income": ["financial income", "financial revenue", "thu nhap tai chinh", "doanh thu tai chinh"],
    "financial_expenses": ["financial expenses", "chi phi tai chinh"],
    "ebit": [
        "ebit", "operating profit", "operating income",
        "profit from business activities", "profit loss from business activities",
        "loi nhuan hoat dong", "loi nhuan tu hoat dong kinh doanh"
    ],
    "interest_expenses": ["interest expense", "interest expenses", "interest paid", "chi phi lai vay"],
    "net_income": ["net profit after tax", "profit after tax", "net profit loss after tax", "loi nhuan sau thue", "net income"],
    "depreciation": ["depreciation", "amortization", "depreciation of fixed assets", "khau hao", "khấu hao"],
    "current_assets": ["current assets", "tai san ngan han"],
    "cash": ["cash and cash equivalents", "cash", "tien va tuong duong tien", "tiền"],
    "receivables": ["accounts receivable", "trade receivables", "phai thu", "phải thu"],
    "inventory": ["inventory", "inventories", "hang ton kho", "hàng tồn kho"],
    "current_liabilities": ["current liabilities", "no ngan han", "nợ ngắn hạn"],
    "total_assets": ["total assets", "tong tai san", "tổng tài sản"],
    "total_liabilities": ["total liabilities", "tong no phai tra", "tổng nợ phải trả"],
    "equity": ["equity", "owner s equity", "owner's equity", "von chu so huu", "vốn chủ sở hữu"],
    "st_debt": [
        "short term loans", "short term borrowings", "short term debt",
        "short term loans and financial lease payables", "no vay ngan han"
    ],
    "lt_debt": [
        "long term loans", "long term borrowings", "long term debt",
        "long term loans and financial lease payables", "no vay dai han"
    ],
    "ebitda": ["ebitda"],
    "total_debt": ["total debt", "total interest bearing debt", "tong du no"],
}

def _build_col_lookup(columns: Iterable[str]) -> Dict[str, str]:
    return {_canon(c): c for c in columns}

def _match_columns(columns: Iterable[str], alias_list: List[str]) -> List[str]:
    canon_map = _build_col_lookup(columns)
    hits = []
    for raw in alias_list:
        key = _canon(raw)
        if key in canon_map:
            hits.append(canon_map[key])
            continue
        for ccanon, orig in canon_map.items():
            if key and key in ccanon:
                hits.append(orig)
    uniq, seen = [], set()
    for c in columns:
        if c in hits and c not in seen:
            uniq.append(c); seen.add(c)
    return uniq

def _get_series_from_alias(base: pd.DataFrame, alias_key: str) -> pd.Series:
    alias = ALIASES.get(alias_key, [])
    hits = _match_columns(base.columns, alias)
    if not hits:
        return pd.Series(dtype=float)
    if len(hits) == 1:
        return _ensure_numeric_series(base[hits[0]]).rename(alias_key)
    return _ensure_numeric_frame(base[hits]).sum(axis=1, skipna=True).rename(alias_key)

def _coalesce(*series: Iterable[pd.Series]) -> pd.Series:
    for s in series:
        if isinstance(s, pd.Series) and s.size > 0:
            return s
    return pd.Series(dtype=float)

def _total_debt(base: pd.DataFrame) -> pd.Series:
    td = _get_series_from_alias(base, "total_debt")
    if not td.empty:
        return td
    sd = _get_series_from_alias(base, "st_debt")
    ld = _get_series_from_alias(base, "lt_debt")
    if not sd.empty or not ld.empty:
        sd = sd.reindex(base.index, fill_value=np.nan)
        ld = ld.reindex(base.index, fill_value=np.nan)
        return (sd.add(ld, fill_value=np.nan)).rename("total_debt")
    return _get_series_from_alias(base, "total_liabilities").rename("total_debt")

def _ebitda(base: pd.DataFrame) -> pd.Series:
    ebitda = _get_series_from_alias(base, "ebitda")
    if not ebitda.empty:
        return ebitda
    ebit = _get_series_from_alias(base, "ebit")
    dep  = _get_series_from_alias(base, "depreciation")
    if ebit.empty or dep.empty:
        return pd.Series(dtype=float)
    return ebit.add(dep, fill_value=np.nan).rename("ebitda")

# -------------------------------
# Compute indicators
# -------------------------------
def compute_indicators(fin_df: pd.DataFrame) -> pd.DataFrame:
    base = _build_base(fin_df)

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

    lt_debt    = _get_series_from_alias(base, "lt_debt")
    tot_debt   = _total_debt(base)
    ebitda     = _ebitda(base)

    if gross_p.empty and not revenue.empty and not cogs.empty:
        gross_p = (revenue - cogs).rename("gross_profit")

    if not curr_assets.empty and not inv.empty:
        quick_assets = curr_assets - inv
    elif not cash.empty and not recv.empty:
        quick_assets = cash.add(recv, fill_value=np.nan)
    else:
        quick_assets = pd.Series(dtype=float)

    indicators = {
        "Current Ratio": _sdiv(curr_assets, curr_liab),
        "Quick Ratio": _sdiv(quick_assets, curr_liab),
        "Working Capital to Total Assets": _sdiv(curr_assets - curr_liab, tot_assets),
        "Debt to Assets": _coalesce(_sdiv(tot_liab, tot_assets), _sdiv(tot_debt, tot_assets)),
        "Debt to Equity": _coalesce(_sdiv(tot_debt, equity), _sdiv(tot_liab, equity)),
        "Equity to Liabilities": _sdiv(equity, tot_liab),
        "Long Term Debt to Assets": _sdiv(lt_debt, tot_assets),
        "Net Debt to Equity": _sdiv(tot_debt - cash, equity),
        "Receivables Turnover": _sdiv(revenue, recv),
        "Inventory Turnover": _sdiv(cogs, inv),
        "Asset Turnover": _sdiv(revenue, tot_assets),
        "ROA": _sdiv(net_inc, tot_assets),
        "ROE": _sdiv(net_inc, equity),
        "EBIT to Assets": _sdiv(ebit, tot_assets),
        "Operating Income to Debt": _coalesce(_sdiv(ebit, tot_debt), _sdiv(ebit, tot_liab)),
        "Net Profit Margin": _sdiv(net_inc, revenue),
        "Gross Margin": _sdiv(gross_p, revenue),
        "Interest Coverage": _sdiv(ebit, interest),
        "EBITDA to Interest": _sdiv(ebitda, interest),
        "Total Debt to EBITDA": _sdiv(tot_debt, ebitda),
    }

    df_out = pd.DataFrame(indicators)

    # FIX: sort by a numeric year key while the year is the INDEX (not a column)
    labels = df_out.index.astype(str)
    year_num = pd.to_numeric(labels.str.extract(r"(\d{4})", expand=False), errors="coerce")
    df_out = df_out.assign(__sort_year__=year_num, __lbl__=labels) \
                   .sort_values(["__sort_year__", "__lbl__"]) \
                   .drop(columns="__sort_year__")
    df_out.index.name = "Year"

    view = df_out.T

    desired_order = [
        "Current Ratio","Quick Ratio","Working Capital to Total Assets",
        "Debt to Assets","Debt to Equity","Equity to Liabilities",
        "Long Term Debt to Assets","Net Debt to Equity",
        "Receivables Turnover","Inventory Turnover","Asset Turnover",
        "ROA","ROE","EBIT to Assets","Operating Income to Debt",
        "Net Profit Margin","Gross Margin","Interest Coverage",
        "EBITDA to Interest","Total Debt to EBITDA",
    ]
    view = view.loc[[k for k in desired_order if k in view.index]]
    return view

# -------------------------------
# Renderer
# -------------------------------
def render(fin_df: pd.DataFrame):
    st.subheader("FINANCIAL INDICATORS")
    view = compute_indicators(fin_df)
    if view.empty:
        st.info("No sufficient data to compute indicators. Please verify column names in the dataset.")
        return
    st.dataframe(view, use_container_width=True, hide_index=False)
