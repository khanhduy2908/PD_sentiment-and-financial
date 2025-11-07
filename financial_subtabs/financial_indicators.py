# financial_subtabs/financial_indicators.py
# English-only labels. No icons.
from __future__ import annotations

import numpy as np
import pandas as pd
import streamlit as st

###############################################################################
# Column alias map (robust to your dataset's naming variants)
###############################################################################
ALIASES = {
    "year": ["display_year", "Year", "year_label", "year"],
    "revenue": [
        "Net Revenue", "Revenue", "Net Sales", "Sales", "Operating revenue",
        "Doanh thu", "Doanh thu thuần"
    ],
    "cogs": [
        "Cost of Goods Sold (COGS)", "COGS", "Cost of goods sold", "Giá vốn"
    ],
    "gross_profit": [
        "Gross Profit", "Gross profit", "Lợi nhuận gộp"
    ],
    "ebit": [
        "Operating Profit", "Operating Income", "EBIT",
        "Profit/(Loss) from Business Activities", "Lợi nhuận từ HĐKD"
    ],
    "interest_exp": [
        "Interest Expenses", "Interest expense", "Chi phí lãi vay"
    ],
    "net_profit": [
        "Net Profit/(Loss) After Tax", "Net Profit After Tax",
        "Profit after tax", "Lợi nhuận sau thuế", "Net_Profit"
    ],
    "current_assets": [
        "CURRENT ASSETS (Bn. VND)", "Current assets", "Tài sản ngắn hạn", "Current_Assets"
    ],
    "cash": [
        "Cash and Cash Equivalents", "Cash & equivalents", "Tiền và tương đương tiền", "Cash"
    ],
    "receivables": [
        "Accounts Receivable", "Trade receivables", "Phải thu khách hàng", "Receivables"
    ],
    "inventory": [
        "Inventory, Net", "Inventories", "Hàng tồn kho", "Net Inventories"
    ],
    "current_liabilities": [
        "Short-Term Liabilities", "Current liabilities", "Nợ ngắn hạn", "Current_Liabilities"
    ],
    "total_assets": [
        "TOTAL ASSETS", "Total assets", "Tổng tài sản", "Total_Assets"
    ],
    "total_liab": [
        "LIABILITIES", "Total liabilities", "Tổng nợ phải trả", "Total_Liabilities"
    ],
    "equity": [
        "EQUITY", "Owner’s equity", "Vốn chủ sở hữu", "Equity", "OWNER'S EQUITY(Bn.VND)"
    ],
    "st_debt": [
        "Short-Term Loans", "Short-term borrowings", "Vay ngắn hạn"
    ],
    "lt_debt": [
        "Long-Term Loans", "Long-term borrowings", "Vay dài hạn"
    ],
    "depr": [
        "Depreciation of Fixed Assets and Investment Properties",
        "Depreciation expense", "Khấu hao TSCĐ"
    ],
    "amort": [
        "Amortization of Goodwill", "Amortization", "Phân bổ"
    ],
}

###############################################################################
# Helpers
###############################################################################
def _pickcol(df: pd.DataFrame, candidates: list[str]) -> str | None:
    if not candidates:
        return None
    cols_lower = {c.lower(): c for c in df.columns}
    for cand in candidates:
        if cand in df.columns:
            return cand
        lc = cand.lower()
        if lc in cols_lower:
            return cols_lower[lc]
    return None

def _year_col(df: pd.DataFrame) -> str:
    y = _pickcol(df, ALIASES["year"])
    if y is None:
        raise KeyError("Year column not found. Please ensure your data has a year/display_year column.")
    return y

def _ensure_numeric(s: pd.Series) -> pd.Series:
    return pd.to_numeric(s, errors="coerce")

def _get_series(df: pd.DataFrame, alias_key: str) -> pd.Series:
    """Try to read a wide-format column (single column). If multiple aliases present,
    sum them (rare but safe). Return numeric Series aligned by year index."""
    ycol = _year_col(df)
    base = df.drop_duplicates(subset=[ycol]).set_index(ycol).sort_index()
    hits = [_pickcol(base, [cand]) for cand in ALIASES.get(alias_key, [])]
    hits = [h for h in hits if h is not None]
    if not hits:
        return pd.Series(dtype=float)
    ser = _ensure_numeric(base[hits]).sum(axis=1) if len(hits) > 1 else _ensure_numeric(base[hits[0]])
    ser.name = alias_key
    return ser

def _avg_series(s: pd.Series) -> pd.Series:
    """Average with prior year when available."""
    if s.empty:
        return s
    return (s + s.shift(1)) / 2.0

def _safe_div(num: pd.Series, den: pd.Series, default=np.nan) -> pd.Series:
    out = num.astype(float) / den.astype(float)
    out = out.replace([np.inf, -np.inf], np.nan)
    return out.fillna(default)

def _fmt_percent(x: float) -> str:
    if pd.isna(x):
        return ""
    return f"{x:.2%}"

def _fmt_multiple(x: float) -> str:
    if pd.isna(x):
        return ""
    return f"{x:,.2f}"

def _fmt_ratio(x: float) -> str:
    # general ratio formatting (e.g., Debt/Equity, Current Ratio)
    if pd.isna(x):
        return ""
    return f"{x:,.2f}"

###############################################################################
# Core calculation
###############################################################################
METADATA = [
    # (Display name, key)
    ("Current Ratio", "current_ratio"),
    ("Quick Ratio", "quick_ratio"),
    ("Working Capital to Total Assets", "wc_to_assets"),
    ("Debt to Assets", "debt_to_assets"),
    ("Debt to Equity", "debt_to_equity"),
    ("Equity to Liabilities", "equity_to_liabilities"),
    ("Long Term Debt to Assets", "lt_debt_to_assets"),
    ("Net Debt to Equity", "net_debt_to_equity"),
    ("Receivables Turnover", "recv_turnover"),
    ("Inventory Turnover", "inv_turnover"),
    ("Asset Turnover", "asset_turnover"),
    ("ROA", "roa_pct"),
    ("ROE", "roe_pct"),
    ("EBIT to Assets", "ebit_to_assets_pct"),
    ("Operating Income to Debt", "ebit_to_debt"),
    ("Net Profit Margin", "npm_pct"),
    ("Gross Margin", "gm_pct"),
    ("Interest Coverage", "interest_coverage"),
    ("EBITDA to Interest", "ebitda_to_interest"),
    ("Total Debt to EBITDA", "debt_to_ebitda"),
]

# Which keys display as percentages:
PCT_KEYS = {"roa_pct", "roe_pct", "ebit_to_assets_pct", "npm_pct", "gm_pct"}

def compute_indicators(fin_df: pd.DataFrame) -> pd.DataFrame:
    ycol = _year_col(fin_df)

    # Pull base series
    revenue   = _get_series(fin_df, "revenue")
    cogs      = _get_series(fin_df, "cogs")
    gross_p   = _get_series(fin_df, "gross_profit")
    ebit      = _get_series(fin_df, "ebit")
    int_exp   = _get_series(fin_df, "interest_exp")
    net_pft   = _get_series(fin_df, "net_profit")

    cur_assets = _get_series(fin_df, "current_assets")
    cash       = _get_series(fin_df, "cash")
    recv       = _get_series(fin_df, "receivables")
    inv        = _get_series(fin_df, "inventory")

    cur_liab   = _get_series(fin_df, "current_liabilities")
    tot_assets = _get_series(fin_df, "total_assets")
    tot_liab   = _get_series(fin_df, "total_liab")
    equity     = _get_series(fin_df, "equity")
    st_debt    = _get_series(fin_df, "st_debt")
    lt_debt    = _get_series(fin_df, "lt_debt")

    # debt proxies
    total_debt = pd.Series(dtype=float, index=tot_liab.index)
    if not st_debt.empty or not lt_debt.empty:
        # sum available parts (missing treated as 0)
        total_debt = _ensure_numeric(st_debt).reindex(tot_liab.index).fillna(0) + \
                     _ensure_numeric(lt_debt).reindex(tot_liab.index).fillna(0)
    else:
        # Fallback: use total liabilities if explicit debt not present
        total_debt = _ensure_numeric(tot_liab).copy()

    # depreciation & amortization (for EBITDA)
    depr  = _get_series(fin_df, "depr")
    amort = _get_series(fin_df, "amort")
    da    = pd.Series(dtype=float, index=ebit.index)
    if not depr.empty or not amort.empty:
        da = _ensure_numeric(depr).reindex(ebit.index).fillna(0) + \
             _ensure_numeric(amort).reindex(ebit.index).fillna(0)
    # EBITDA
    ebitda = pd.Series(dtype=float, index=ebit.index)
    if not ebit.empty:
        ebitda = _ensure_numeric(ebit).reindex(ebit.index).fillna(0) + da.reindex(ebit.index).fillna(0)

    # rolling averages for turnover / ROA / ROE / asset-based metrics
    recv_avg   = _avg_series(recv)
    inv_avg    = _avg_series(inv)
    assets_avg = _avg_series(tot_assets)
    equity_avg = _avg_series(equity)

    # Indicators
    indicators = {}

    # Liquidity
    indicators["current_ratio"]     = _safe_div(cur_assets, cur_liab)
    quick_num = pd.Series(dtype=float, index=cur_assets.index)
    if "cash" in cash.index or not cash.empty:
        quick_num = cash.reindex(cur_assets.index).fillna(0) + recv.reindex(cur_assets.index).fillna(0)
    else:
        # fallback: (current assets - inventory)
        quick_num = cur_assets.reindex(inv.index).fillna(0) - inv.reindex(cur_assets.index).fillna(0)
    indicators["quick_ratio"]       = _safe_div(quick_num, cur_liab)
    indicators["wc_to_assets"]      = _safe_div(cur_assets - cur_liab, tot_assets)

    # Leverage & structure
    indicators["debt_to_assets"]        = _safe_div(total_debt, tot_assets)
    indicators["debt_to_equity"]        = _safe_div(total_debt, equity)
    indicators["equity_to_liabilities"] = _safe_div(equity, tot_liab)
    indicators["lt_debt_to_assets"]     = _safe_div(lt_debt, tot_assets)
    indicators["net_debt_to_equity"]    = _safe_div(total_debt - cash.reindex(total_debt.index).fillna(0), equity)

    # Efficiency
    indicators["recv_turnover"] = _safe_div(revenue, recv_avg.replace(0, np.nan))
    indicators["inv_turnover"]  = _safe_div(cogs, inv_avg.replace(0, np.nan))
    indicators["asset_turnover"] = _safe_div(revenue, assets_avg.replace(0, np.nan))

    # Profitability
    indicators["roa_pct"]            = _safe_div(net_pft, assets_avg.replace(0, np.nan))
    indicators["roe_pct"]            = _safe_div(net_pft, equity_avg.replace(0, np.nan))
    indicators["ebit_to_assets_pct"] = _safe_div(ebit, assets_avg.replace(0, np.nan))
    indicators["npm_pct"]            = _safe_div(net_pft, revenue.replace(0, np.nan))
    indicators["gm_pct"]             = _safe_div(gross_p, revenue.replace(0, np.nan))

    # Coverage
    indicators["interest_coverage"]  = _safe_div(ebit, int_exp.replace(0, np.nan))
    indicators["ebitda_to_interest"] = _safe_div(ebitda, int_exp.replace(0, np.nan))
    indicators["debt_to_ebitda"]     = _safe_div(total_debt, ebitda.replace(0, np.nan))

    # Assemble wide table (rows = metrics, columns = years)
    all_years = fin_df[_year_col(fin_df)].astype(str).unique().tolist()
    all_years = sorted(all_years, key=lambda x: (x.endswith("F"), x))  # put forecasts (e.g., 2024F) at end if present

    out = pd.DataFrame(index=[m[1] for m in METADATA], columns=all_years, dtype=float)
    for disp, key in METADATA:
        s = indicators.get(key, pd.Series(dtype=float))
        if not s.empty:
            # align to string years
            sv = s.copy()
            sv.index = sv.index.astype(str)
            out.loc[key, sv.index] = sv.values

    # Replace index with display names
    out.insert(0, "Metric", [m[0] for m in METADATA])
    out = out.set_index("Metric")

    return out

###############################################################################
# Rendering
###############################################################################
def render(fin_df: pd.DataFrame):
    st.subheader("FINANCIAL INDICATORS (computed)")

    view = compute_indicators(fin_df)
    if view.empty:
        st.info("No sufficient data to compute indicators. Please verify the dataset headers.")
        return

    # Format per-row
    formatted = view.copy()
    for disp, key in METADATA:
        row = view.loc[disp]
        if key in PCT_KEYS:
            formatted.loc[disp] = row.apply(_fmt_percent)
        else:
            # multiples / ratios
            formatted.loc[disp] = row.apply(_fmt_ratio)

    st.dataframe(formatted, use_container_width=True, hide_index=False)
