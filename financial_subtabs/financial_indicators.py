# financial_subtabs/financial_indicators.py
from __future__ import annotations
import re
from typing import Dict, List, Iterable
import numpy as np
import pandas as pd
import streamlit as st

# ==========================
# Helpers & alias matching
# ==========================

def _norm(s: str) -> str:
    """Normalize a column/label for fuzzy match: lower + keep letters/digits only."""
    return re.sub(r"[^a-z0-9]+", "", str(s).lower())

def _pickcol(df: pd.DataFrame, candidates: Iterable[str]) -> str | None:
    if df is None or df.empty:
        return None
    cols_norm = { _norm(c): c for c in df.columns }
    for c in candidates:
        key = _norm(c)
        if key in cols_norm:
            return cols_norm[key]
    # second pass: contains
    for c in candidates:
        key = _norm(c)
        for knorm, raw in cols_norm.items():
            if key and key in knorm:
                return raw
    return None

def safe_div(a, b):
    try:
        a = float(a) if a is not None else np.nan
        b = float(b) if b is not None else np.nan
        if not np.isfinite(a) or not np.isfinite(b) or b == 0:
            return np.nan
        return a / b
    except Exception:
        return np.nan

def _match_alias(columns: Iterable[str], patterns: List[str]) -> List[str]:
    """Return list of column names that match any alias pattern."""
    results = []
    norm_cols = {c: _norm(c) for c in columns}
    pats = [ _norm(p) for p in patterns ]
    for col, ncol in norm_cols.items():
        for p in pats:
            if p and p in ncol:
                results.append(col)
                break
    return results

# ---- Alias dictionary (bắt cột rộng rãi) ----
ALIAS: Dict[str, List[str]] = {
    # Income statement
    "revenue": [
        "net revenue", "revenue", "net sales", "doanh thu", "doanhthu", "doanhthu thuần"
    ],
    "cogs": [
        "cogs", "cost of goods sold", "giá vốn", "gia von", "giavonhangban"
    ],
    "gross_profit": [
        "gross profit", "loi nhuan gop", "lợi nhuận gộp"
    ],
    "ebit": [
        "ebit", "operating profit", "operating income",
        "profit(loss) from business activities", "loi nhuan tu hoat dong kinh doanh",
        "lnkd", "lợi nhuận từ hoạt động kinh doanh"
    ],
    "ebitda": [
        "ebitda"
    ],
    "interest_exp": [
        "interest expense", "interest expenses", "chi phi lai vay", "chi phí lãi vay"
    ],
    "net_profit": [
        "net profit", "net income", "profit after tax", "lợi nhuận sau thuế", "lnst"
    ],
    # Balance sheet (current)
    "current_assets": [
        "current assets", "tài sản ngắn hạn", "tsnh"
    ],
    "cash": [
        "cash and cash equivalents", "tiền và tương đương tiền", "tien"
    ],
    "receivables": [
        "accounts receivable", "phai thu", "phải thu", "trade receivables"
    ],
    "inventory": [
        "inventory", "inventories", "hàng tồn kho", "hang ton kho", "htk"
    ],
    "current_liab": [
        "current liabilities", "nợ phải trả ngắn hạn", "no ngan han"
    ],
    # Balance sheet (totals)
    "total_assets": [
        "total assets", "tong tai san", "tổng tài sản"
    ],
    "total_liab": [
        "liabilities", "total liabilities", "tong no phai tra", "tổng nợ phải trả"
    ],
    "equity": [
        "equity", "owner's equity", "vốn chủ sở hữu", "von chu so huu"
    ],
    "st_debt": [
        "short-term loans", "short-term borrowings", "vay ngan han", "no ngan han vay"
    ],
    "lt_debt": [
        "long-term loans", "long-term borrowings", "vay dai han", "no dai han vay"
    ],
    # Fallback operating income if ebit missing
    "operating_income": [
        "operating income", "lnkd", "profit(loss) from business activities"
    ],
    # Depreciation for EBITDA build if needed
    "depr": [
        "depreciation", "khau hao", "depreciation of fixed assets"
    ],
}

# ==========================
# Extract series (WIDE / LONG)
# ==========================

def _extract_series_wide(df_indexed_by_year: pd.DataFrame, alias_key: str) -> pd.Series:
    """
    df_indexed_by_year: index = year label, columns = indicators (wide form).
    Return a numeric series aligned with the index. If multiple columns match, sum them.
    """
    pats = ALIAS.get(alias_key, [])
    hits = _match_alias(df_indexed_by_year.columns, pats)
    # Always return a float series with same index (even if empty)
    if not hits:
        return pd.Series(index=df_indexed_by_year.index, dtype=float)
    sub = df_indexed_by_year.loc[:, list(hits)].apply(pd.to_numeric, errors="coerce")
    ser = sub.sum(axis=1)
    return ser

def _extract_series_long(fin_df: pd.DataFrame, statements: List[str], alias_key: str) -> pd.Series:
    """
    Long-form support: expect columns like [Statement, LineItem, Year, Value]
    Returns a series indexed by Year label.
    """
    stmt_col = _pickcol(fin_df, ["Statement", "BCTC", "Loại", "Sheet"])
    item_col = _pickcol(fin_df, ["LineItem", "Item", "Chỉ tiêu", "Chi tieu"])
    year_col = _pickcol(fin_df, ["display_year", "Year", "Năm", "Nam", "year_label"])
    val_col  = _pickcol(fin_df, ["Value", "Giá trị", "Gia tri", "Amount"])
    if not all([stmt_col, item_col, year_col, val_col]):
        return pd.Series(dtype=float)

    df = fin_df[[stmt_col, item_col, year_col, val_col]].copy()
    df[year_col] = df[year_col].astype(str)
    df[val_col]  = pd.to_numeric(df[val_col], errors="coerce")

    # Filter statement
    if statements:
        mask_stmt = df[stmt_col].astype(str).str.lower().apply(_norm).str.contains("|".join([_norm(s) for s in statements]))
        df = df[mask_stmt]

    # Match line items by alias
    pats = ALIAS.get(alias_key, [])
    if not pats:
        return pd.Series(dtype=float)
    mask_item = df[item_col].astype(str).apply(_norm).apply(lambda s: any(_norm(p) in s for p in pats))
    df = df[mask_item]

    if df.empty:
        return pd.Series(dtype=float)

    ser = df.groupby(year_col, as_index=True)[val_col].sum()
    # ensure numeric index ordering if year-like
    try:
        ser = ser.reindex(sorted(ser.index, key=lambda x: int(re.sub(r"[^0-9\-]", "", x) or 0)))
    except Exception:
        ser = ser.sort_index()
    return ser

def fetch_metric_series(fin_df: pd.DataFrame, alias_key: str) -> pd.Series:
    """
    Try long-form first, then wide-form. Return numeric Series indexed by year (string).
    """
    # Long-form attempt across any statement
    ser = _extract_series_long(fin_df, ["income", "balance", "cash"], alias_key)
    if not ser.empty:
        return pd.to_numeric(ser, errors="coerce")

    # Wide-form fallback: need a year-like column
    y = _pickcol(fin_df, ["display_year", "year", "Year", "year_label", "Năm", "Nam"])
    if y is None:
        # create a display year from index if needed
        tmp = fin_df.copy()
        tmp["display_year"] = tmp.index.astype(str)
        y = "display_year"
    base = (fin_df.drop_duplicates(subset=[y])
                  .set_index(fin_df[y].astype(str))
                  .sort_index())
    return _extract_series_wide(base, alias_key)

# ==========================
# Indicator computation
# ==========================

INDICATOR_ORDER = [
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

def _avg_series(ser: pd.Series) -> pd.Series:
    """Average with previous period (t + t-1)/2 for turnover/ROA/ROE denominators."""
    if ser is None or ser.empty:
        return pd.Series(dtype=float)
    s = pd.to_numeric(ser, errors="coerce")
    # align by numeric-sorted index if possible
    try:
        order = sorted(s.index, key=lambda x: int(re.sub(r"[^0-9\-]", "", x) or 0))
        s = s.reindex(order)
    except Exception:
        s = s.sort_index()
    return (s + s.shift(1)) / 2.0

def _first_non_nan(*vals):
    for v in vals:
        if v is not None and np.isfinite(v):
            return v
    return np.nan

def compute_indicators(fin_df: pd.DataFrame) -> pd.DataFrame:
    # Fetch core series
    S = {k: fetch_metric_series(fin_df, k) for k in [
        "revenue","cogs","gross_profit","ebit","ebitda","interest_exp","net_profit",
        "current_assets","cash","receivables","inventory","current_liab",
        "total_assets","total_liab","equity","st_debt","lt_debt","operating_income","depr"
    ]}

    # Construct helpers
    years = sorted(set().union(*[set(s.index) for s in S.values() if not s.empty]))
    if not years:
        return pd.DataFrame(columns=["No data"], index=INDICATOR_ORDER)

    years = sorted(years, key=lambda x: int(re.sub(r"[^0-9\-]", "", x) or 0))

    # Build total debt and ebitda if missing
    total_debt = (pd.to_numeric(S.get("st_debt"), errors="coerce").reindex(years) if not S["st_debt"].empty else 0)\
               + (pd.to_numeric(S.get("lt_debt"), errors="coerce").reindex(years) if not S["lt_debt"].empty else 0)
    total_debt = total_debt.replace([np.inf,-np.inf], np.nan)

    if S["ebitda"].empty:
        # EBITDA ≈ EBIT + Depreciation (fallback)
        ebitda = (pd.to_numeric(S["ebit"], errors="coerce").reindex(years)) \
               + (pd.to_numeric(S["depr"], errors="coerce").reindex(years))
    else:
        ebitda = pd.to_numeric(S["ebitda"], errors="coerce").reindex(years)

    # Averages for turnover/returns
    avg_assets  = _avg_series(pd.to_numeric(S["total_assets"], errors="coerce").reindex(years))
    avg_equity  = _avg_series(pd.to_numeric(S["equity"], errors="coerce").reindex(years))
    avg_ar      = _avg_series(pd.to_numeric(S["receivables"], errors="coerce").reindex(years))
    avg_inv     = _avg_series(pd.to_numeric(S["inventory"], errors="coerce").reindex(years))

    # Convenience getters
    def val(series_key, y):
        ser = pd.to_numeric(S[series_key], errors="coerce").reindex(years)
        return float(ser.get(y, np.nan)) if ser is not None else np.nan

    # Compute indicators per year
    data: Dict[str, List[float]] = {ind: [] for ind in INDICATOR_ORDER}

    for y in years:
        revenue      = val("revenue", y)
        cogs         = val("cogs", y)
        gross_profit = val("gross_profit", y)
        ebit         = val("ebit", y)
        interest_exp = val("interest_exp", y)
        net_profit   = val("net_profit", y)

        ca   = val("current_assets", y)
        cash = val("cash", y)
        ar   = val("receivables", y)
        inv  = val("inventory", y)
        cl   = val("current_liab", y)

        ta   = val("total_assets", y)
        tl   = val("total_liab", y)
        eq   = val("equity", y)
        sd   = val("st_debt", y)
        ld   = val("lt_debt", y)

        td   = float(total_debt.get(y, np.nan)) if isinstance(total_debt, pd.Series) else np.nan
        ebt_da = float(ebitda.get(y, np.nan)) if isinstance(ebitda, pd.Series) else np.nan

        # Averages
        A_assets = float(avg_assets.get(y, np.nan)) if isinstance(avg_assets, pd.Series) else np.nan
        A_equity = float(avg_equity.get(y, np.nan)) if isinstance(avg_equity, pd.Series) else np.nan
        A_ar     = float(avg_ar.get(y, np.nan)) if isinstance(avg_ar, pd.Series) else np.nan
        A_inv    = float(avg_inv.get(y, np.nan)) if isinstance(avg_inv, pd.Series) else np.nan

        # 1. Current Ratio
        data["Current Ratio"].append(safe_div(ca, cl))

        # 2. Quick Ratio  (ưu tiên (CA - Inventory)/CL; fallback (Cash+AR)/CL)
        qr1 = safe_div((ca - inv) if np.isfinite(ca) and np.isfinite(inv) else np.nan, cl)
        qr2 = safe_div(_first_non_nan(cash, 0) + _first_non_nan(ar, 0), cl)
        data["Quick Ratio"].append(qr1 if np.isfinite(qr1) else qr2)

        # 3. Working Capital to Total Assets
        wc_ta = safe_div((_first_non_nan(ca, np.nan) - _first_non_nan(cl, np.nan)), ta)
        data["Working Capital to Total Assets"].append(wc_ta)

        # 4. Debt to Assets  (dùng Total Liabilities khi không có debt tách bạch)
        data["Debt to Assets"].append(safe_div(_first_non_nan(td, tl), ta))

        # 5. Debt to Equity
        data["Debt to Equity"].append(safe_div(_first_non_nan(td, tl), eq))

        # 6. Equity to Liabilities
        data["Equity to Liabilities"].append(safe_div(eq, tl))

        # 7. Long Term Debt to Assets
        data["Long Term Debt to Assets"].append(safe_div(ld, ta))

        # 8. Net Debt to Equity  (Total Debt - Cash) / Equity
        net_debt = _first_non_nan(td, tl)
        if np.isfinite(net_debt) and np.isfinite(cash):
            net_debt = net_debt - cash
        data["Net Debt to Equity"].append(safe_div(net_debt, eq))

        # 9. Receivables Turnover = Revenue / Avg AR
        data["Receivables Turnover"].append(safe_div(revenue, A_ar))

        # 10. Inventory Turnover = COGS / Avg Inventory (fallback: Revenue / Avg Inv)
        inv_to = safe_div(cogs, A_inv)
        if not np.isfinite(inv_to):
            inv_to = safe_div(revenue, A_inv)
        data["Inventory Turnover"].append(inv_to)

        # 11. Asset Turnover = Revenue / Avg Total Assets
        data["Asset Turnover"].append(safe_div(revenue, A_assets))

        # 12. ROA = Net Profit / Avg Total Assets
        data["ROA"].append(safe_div(net_profit, A_assets))

        # 13. ROE = Net Profit / Avg Equity
        data["ROE"].append(safe_div(net_profit, A_equity))

        # 14. EBIT to Assets = EBIT / Avg Total Assets
        data["EBIT to Assets"].append(safe_div(ebit, A_assets))

        # 15. Operating Income to Debt = Operating Income (≈ EBIT) / Total Debt
        op_inc = ebit if np.isfinite(ebit) else val("operating_income", y)
        data["Operating Income to Debt"].append(safe_div(op_inc, _first_non_nan(td, tl)))

        # 16. Net Profit Margin = Net Profit / Revenue
        data["Net Profit Margin"].append(safe_div(net_profit, revenue))

        # 17. Gross Margin = Gross Profit / Revenue
        data["Gross Margin"].append(safe_div(gross_profit, revenue))

        # 18. Interest Coverage = EBIT / Interest Expense
        data["Interest Coverage"].append(safe_div(ebit, interest_exp))

        # 19. EBITDA to Interest = EBITDA / Interest Expense
        data["EBITDA to Interest"].append(safe_div(ebt_da, interest_exp))

        # 20. Total Debt to EBITDA = Total Debt / EBITDA
        data["Total Debt to EBITDA"].append(safe_div(_first_non_nan(td, tl), ebt_da))

    view = pd.DataFrame(data, index=years).T  # rows = indicators, cols = years

    # Cosmetic: round ratios to 4 decimals, margins to 4, cover divisions
    view = view.replace([np.inf, -np.inf], np.nan)

    return view

# ==========================
# Streamlit render
# ==========================

def _format_df_for_display(df: pd.DataFrame) -> pd.DataFrame:
    """Apply % formatting for margin/return metrics, leave turnover as numeric."""
    if df.empty:
        return df
    # Which are % ratios?
    as_percent = {
        "Working Capital to Total Assets",
        "Debt to Assets", "Debt to Equity", "Equity to Liabilities",
        "Long Term Debt to Assets", "Net Debt to Equity",
        "ROA", "ROE", "EBIT to Assets", "Net Profit Margin", "Gross Margin"
    }
    out = df.copy()
    # limit decimals for non-percent
    for r in out.index:
        if r in as_percent:
            out.loc[r] = out.loc[r].apply(lambda x: "" if pd.isna(x) else f"{x:.4%}")
        else:
            out.loc[r] = out.loc[r].apply(lambda x: "" if pd.isna(x) else f"{x:,.4f}")
    return out

def render(fin_df: pd.DataFrame):
    st.markdown("""
    <div style="background:#0d3b66;color:#fff;padding:10px 16px;border-radius:10px;
                font-weight:650;display:inline-block;margin:6px 0;">
      FINANCIAL INDICATORS (computed)
    </div>
    """, unsafe_allow_html=True)

    view = compute_indicators(fin_df)
    if view.empty:
        st.info("Không đủ dữ liệu để tính các chỉ số. Vui lòng đảm bảo các cột doanh thu, COGS, tài sản, nợ, vốn CSH, HTK, phải thu, v.v. có mặt trong CSV (wide) hoặc long-form.")
        return

    styled = _format_df_for_display(view)
    st.dataframe(styled, use_container_width=True, hide_index=False)
