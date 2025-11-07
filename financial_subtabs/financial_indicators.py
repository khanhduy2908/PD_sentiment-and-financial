
import streamlit as st
import pandas as pd
import numpy as np
import re
from utils.transforms import build_display_year_column, sort_year_labels

def _pickcol(df: pd.DataFrame, cands):
    lower = {c.lower(): c for c in df.columns}
    for c in cands:
        if c in df.columns: return c
        lc = c.lower()
        if lc in lower: return lower[lc]
    return None

def _safe_num(x):
    try:
        return float(pd.to_numeric(x, errors="coerce"))
    except Exception:
        return np.nan

def _sdiv(a, b):
    a = _safe_num(a); b = _safe_num(b)
    if b is None or b == 0 or not np.isfinite(b): return np.nan
    return a / b

def _avg(a, b):
    a = _safe_num(a); b = _safe_num(b)
    if np.isfinite(a) and np.isfinite(b): return (a + b) / 2.0
    return a if np.isfinite(a) else b

STMT_IS = ["INCOME_STATEMENT","INCOME STATEMENT","P/L","PROFIT_AND_LOSS","PROFIT OR LOSS"]
STMT_BS_A = ["BALANCE_SHEET_ASSETS","BALANCE SHEET (ASSETS)","ASSETS"]
STMT_BS_L = ["BALANCE_SHEET_LIAB","BALANCE SHEET (LIABILITIES)","LIABILITIES"]
STMT_BS_E = ["BALANCE_SHEET_EQUITY","BALANCE SHEET (EQUITY)","EQUITY"]
STMT_CF = ["CASHFLOW_STATEMENT","CASH FLOW STATEMENT","CASHFLOW"]

ALIASES = {
    "revenue": [r"^net\s*revenue", r"^revenue", r"^net\s*sales", r"^doanh thu"],
    "cogs": [r"^cogs", r"^cost of goods sold", r"^giá vốn"],
    "gross_profit": [r"^gross\s*profit", r"^lợi nhuận gộp"],
    "ebit": [r"operating profit|ebit|business activities", r"lợi nhuận thuần từ hoạt động kinh doanh"],
    "interest_exp": [r"interest.*expense", r"^chi phí lãi vay"],
    "net_profit": [r"net profit.*after|profit after tax|pat|lợi nhuận sau thuế"],
    "current_assets": [r"^current assets", r"tài sản ngắn hạn"],
    "cash": [r"^cash.*equivalents|^cash$", r"tiền và tương đương tiền", r"tiền$"],
    "receivables": [r"accounts receivable|phải thu"],
    "inventory": [r"^inventory|hàng tồn kho"],
    "current_liab": [r"^current liabilities|nợ ngắn hạn"],
    "total_assets": [r"^total assets|tổng tài sản"],
    "total_liab": [r"^total liabilities|tổng nợ phải trả"],
    "equity": [r"^equity|owner.*equity|vốn chủ sở hữu"],
    "st_debt": [r"short[- ]?term loans|vay ngắn hạn"],
    "lt_debt": [r"long[- ]?term loans|vay dài hạn"],
    "total_debt": [r"^total debt|tổng nợ vay"],
    "da": [r"depreciation.*amortization|khấu hao|hao mòn", r"depreciation of fixed assets"],
}

def _match_alias(cols, pats):
    hits = []
    for c in cols:
        cl = c.lower().strip()
        for pat in pats:
            if re.search(pat, cl):
                hits.append(c); break
    return hits

def _extract_series_wide(df: pd.DataFrame, alias_key: str):
    pats = ALIASES.get(alias_key, [])
    hits = _match_alias(df.columns, pats)
    if not hits:
        return pd.Series(dtype=float)
    ser = pd.to_numeric(df[hits], errors="coerce").sum(axis=1)
    return ser

def _extract_series_long(df: pd.DataFrame, statements, alias_key: str):
    scol = _pickcol(df, ["statement","section"])
    lcol = _pickcol(df, ["lineitem","line_item","line_item_name","item","account"])
    vcol = _pickcol(df, ["value","amount"])
    ycol = _pickcol(df, ["display_year","year_label","year"])
    if not (scol and lcol and vcol and ycol):
        return pd.Series(dtype=float)
    mask = df[scol].astype(str).str.upper().isin(statements)
    sub = df[mask].copy()
    if sub.empty:
        return pd.Series(dtype=float)
    pats = ALIASES.get(alias_key, [])
    lk = sub[lcol].astype(str)
    row_mask = pd.Series(False, index=sub.index)
    for pat in pats:
        row_mask |= lk.str.lower().str.contains(pat, na=False, regex=True)
    if not row_mask.any():
        return pd.Series(dtype=float)
    agg = sub[row_mask].groupby(sub[ycol].astype(str))[vcol].sum(min_count=1)
    agg = pd.to_numeric(agg, errors="coerce")
    return agg

def fetch_metric_series(fin_df: pd.DataFrame, alias_key: str):
    fin_df = fin_df.copy()
    fin_df = build_display_year_column(fin_df)
    if alias_key in ("revenue","cogs","gross_profit","ebit","interest_exp","net_profit"):
        ser = _extract_series_long(fin_df, STMT_IS, alias_key)
    elif alias_key in ("da",):
        ser = _extract_series_long(fin_df, STMT_CF, alias_key)
        if ser.empty:
            ser = _extract_series_long(fin_df, STMT_IS, alias_key)
    else:
        ser_a = _extract_series_long(fin_df, STMT_BS_A, alias_key)
        ser_l = _extract_series_long(fin_df, STMT_BS_L, alias_key)
        ser_e = _extract_series_long(fin_df, STMT_BS_E, alias_key)
        ser = ser_a if not ser_a.empty else (ser_l if not ser_l.empty else ser_e)
    if ser.empty:
        y = _pickcol(fin_df, ["display_year","year_label","year"])
        base = fin_df.drop_duplicates(subset=[y]).set_index(y).sort_index()
        ser = _extract_series_wide(base, alias_key)
    return ser

def compute_indicators(fin_df: pd.DataFrame) -> pd.DataFrame:
    fin_df = build_display_year_column(fin_df)
    years = sort_year_labels(fin_df["display_year"].astype(str).unique().tolist())
    keys = ["revenue","cogs","gross_profit","ebit","interest_exp","net_profit",
            "current_assets","cash","receivables","inventory","current_liab",
            "total_assets","total_liab","equity","st_debt","lt_debt","total_debt","da"]
    series = {k: fetch_metric_series(fin_df, k) for k in keys}

    def getv(s, y):
        try:
            return float(s.get(str(y), np.nan))
        except Exception:
            return np.nan

    rows = []
    for i, y in enumerate(years):
        y_prev = years[i-1] if i > 0 else None
        revenue = getv(series["revenue"], y)
        cogs = getv(series["cogs"], y)
        gross_profit = getv(series["gross_profit"], y)
        ebit = getv(series["ebit"], y)
        interest_exp = getv(series["interest_exp"], y)
        net_profit = getv(series["net_profit"], y)
        cur_assets = getv(series["current_assets"], y)
        cash = getv(series["cash"], y)
        receivables = getv(series["receivables"], y)
        inventory = getv(series["inventory"], y)
        cur_liab = getv(series["current_liab"], y)
        tot_assets = getv(series["total_assets"], y)
        tot_liab = getv(series["total_liab"], y)
        equity = getv(series["equity"], y)
        st_debt = getv(series["st_debt"], y)
        lt_debt = getv(series["lt_debt"], y)
        total_debt = getv(series["total_debt"], y)
        if not np.isfinite(total_debt):
            total_debt = (st_debt if np.isfinite(st_debt) else 0.0) + (lt_debt if np.isfinite(lt_debt) else 0.0)
        da = getv(series["da"], y)
        ebitda = (ebit if np.isfinite(ebit) else np.nan) + (da if np.isfinite(da) else 0.0)

        if y_prev is not None:
            receivables_prev = getv(series["receivables"], y_prev)
            inventory_prev = getv(series["inventory"], y_prev)
            assets_prev = getv(series["total_assets"], y_prev)
        else:
            receivables_prev = np.nan
            inventory_prev = np.nan
            assets_prev = np.nan

        avg_recv = _avg(receivables, receivables_prev)
        avg_inv = _avg(inventory, inventory_prev)
        avg_assets = _avg(tot_assets, assets_prev)

        current_ratio = _sdiv(cur_assets, cur_liab)
        quick_ratio = _sdiv((cur_assets - inventory if np.isfinite(cur_assets) and np.isfinite(inventory) else np.nan), cur_liab)
        wc_to_ta = _sdiv((cur_assets - cur_liab) if np.isfinite(cur_assets) and np.isfinite(cur_liab) else np.nan, tot_assets)
        d_to_a = _sdiv(total_debt, tot_assets)
        d_to_e = _sdiv(total_debt, equity)
        e_to_l = _sdiv(equity, tot_liab)
        ltd_to_a = _sdiv(lt_debt, tot_assets)
        net_debt_to_e = _sdiv((total_debt - cash) if np.isfinite(total_debt) and np.isfinite(cash) else np.nan, equity)
        recv_turnover = _sdiv(revenue, avg_recv)
        inv_turnover = _sdiv(cogs if np.isfinite(cogs) else revenue, avg_inv)
        asset_turnover = _sdiv(revenue, avg_assets)
        roa = _sdiv(net_profit, tot_assets)
        roe = _sdiv(net_profit, equity)
        ebit_to_assets = _sdiv(ebit, tot_assets)
        op_inc_to_debt = _sdiv(ebit, total_debt)
        npm = _sdiv(net_profit, revenue)
        gm = _sdiv(gross_profit if np.isfinite(gross_profit) else (revenue - cogs if np.isfinite(revenue) and np.isfinite(cogs) else np.nan), revenue)
        interest_coverage = _sdiv(ebit, interest_exp)
        ebitda_to_interest = _sdiv(ebitda, interest_exp)
        td_to_ebitda = _sdiv(total_debt, ebitda)

        rows += [
            {"Metric":"Current Ratio","Year":y,"Value":current_ratio},
            {"Metric":"Quick Ratio","Year":y,"Value":quick_ratio},
            {"Metric":"Working Capital to Total Assets","Year":y,"Value":wc_to_ta},
            {"Metric":"Debt to Assets","Year":y,"Value":d_to_a},
            {"Metric":"Debt to Equity","Year":y,"Value":d_to_e},
            {"Metric":"Equity to Liabilities","Year":y,"Value":e_to_l},
            {"Metric":"Long Term Debt to Assets","Year":y,"Value":ltd_to_a},
            {"Metric":"Net Debt to Equity","Year":y,"Value":net_debt_to_e},
            {"Metric":"Receivables Turnover","Year":y,"Value":recv_turnover},
            {"Metric":"Inventory Turnover","Year":y,"Value":inv_turnover},
            {"Metric":"Asset Turnover","Year":y,"Value":asset_turnover},
            {"Metric":"ROA","Year":y,"Value":roa},
            {"Metric":"ROE","Year":y,"Value":roe},
            {"Metric":"EBIT to Assets","Year":y,"Value":ebit_to_assets},
            {"Metric":"Operating Income to Debt","Year":y,"Value":op_inc_to_debt},
            {"Metric":"Net Profit Margin","Year":y,"Value":npm},
            {"Metric":"Gross Margin","Year":y,"Value":gm},
            {"Metric":"Interest Coverage","Year":y,"Value":interest_coverage},
            {"Metric":"EBITDA to Interest","Year":y,"Value":ebitda_to_interest},
            {"Metric":"Total Debt to EBITDA","Year":y,"Value":td_to_ebitda},
        ]

    ind_df = pd.DataFrame(rows)
    if ind_df.empty:
        return pd.DataFrame()
    pivot = ind_df.pivot_table(index="Metric", columns="Year", values="Value", aggfunc="first")

    def _fmt(x):
        if x is None or (not np.isfinite(x)): return "-"
        try:
            v = float(x)
            if -1.5 <= v <= 1.5:
                return f"{v:.2%}"
            return f"{v:,.2f}"
        except Exception:
            return "-"
    return pivot.applymap(_fmt)

def render(fin_df: pd.DataFrame):
    st.subheader("FINANCIAL INDICATORS (computed)")
    view = compute_indicators(fin_df)
    if view.empty:
        st.info("Không đủ dữ liệu để tính các chỉ số. Vui lòng đảm bảo CSV có các mục IS/BS/CF cần thiết.")
    else:
        st.dataframe(view, use_container_width=True)
