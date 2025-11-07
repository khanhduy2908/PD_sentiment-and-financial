import pandas as pd
import numpy as np
from typing import List, Dict, Tuple

def select_statement(df: pd.DataFrame, key: str) -> pd.DataFrame:
    return df[df["statement"].str.contains(key, case=False, na=False)].copy()

def _income_row_spec() -> List[Dict]:
    return [
        {"label": "INCOME STATEMENT", "keywords": [], "style": "header"},
        {"label": "Net Revenue", "keywords": ["net revenue", "revenue", "sales"], "style": "bold"},
        {"label": "Cost of Goods Sold (COGS)", "keywords": ["cogs", "cost of goods"], "style": None},
        {"label": "Gross Profit", "keywords": ["gross profit"], "style": "bold"},
        {"label": "Financial Income", "keywords": ["financial income"], "style": None},
        {"label": "Financial Expenses", "keywords": ["financial expenses"], "style": None},
        {"label": "Profit/(Loss) from Joint Ventures", "keywords": ["joint venture"], "style": None},
        {"label": "Selling Expenses", "keywords": ["selling expense"], "style": None},
        {"label": "General and Administrative Expenses", "keywords": ["administrative", "g&a"], "style": None},
        {"label": "Profit/(Loss) from Business Activities", "keywords": ["operating profit","profit from operations","ebit"], "style": "bold"},
        {"label": "Other Income, Net", "keywords": ["other income"], "style": None},
        {"label": "Net Profit/(Loss) Before Tax", "keywords": ["profit before tax","pre-tax profit"], "style": "bold"},
        {"label": "Corporate Income Tax Expense", "keywords": ["income tax expense","corporate income tax"], "style": None},
        {"label": "Net Profit/(Loss) After Tax", "keywords": ["net income","net profit","profit after tax"], "style": "bold"},
        {"label": "Basic Earnings Per Share (VND)", "keywords": ["eps","earnings per share"], "style": None},
        {"label": "INCOME STATEMENT ASSUMPTIONS", "keywords": [], "style": "header"},
        {"label": "Profitability Ratio from Joint Ventures", "keywords": ["profitability ratio from joint ventures"], "style": None},
        {"label": "Selling Expense Ratio", "keywords": ["selling expense ratio"], "style": None},
        {"label": "General and Administrative Expense Ratio", "keywords": ["administrative expense ratio"], "style": None},
        {"label": "Financial Revenue Ratio", "keywords": ["financial revenue ratio"], "style": None},
        {"label": "Financial Expenses", "keywords": ["financial expenses ratio"], "style": None},
        {"label": "Other Income Ratio", "keywords": ["other income ratio"], "style": None},
        {"label": "Corporate Income Tax Rate", "keywords": ["corporate income tax rate"], "style": None},
        {"label": "Total Investment (Short-Term Investment Value + Long-Term Investment Value)", "keywords": ["total investment"], "style": None},
        {"label": "Interest Rate on Loans", "keywords": ["interest rate on loans"], "style": None},
    ]

def _match_and_sum(df: pd.DataFrame, keywords: List[str]) -> pd.Series:
    if not keywords:
        return pd.Series(dtype=float)
    mask = df["account"].str.lower().apply(lambda s: any(kw in s for kw in keywords))
    s = df[mask].groupby("period")["value"].sum().sort_index()
    return s

def build_income_table(fin_filtered: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
    income = select_statement(fin_filtered, "income")
    if income.empty:
        return pd.DataFrame(), pd.DataFrame()
    years = list(income["period"].cat.categories) if hasattr(income["period"], "cat") else sorted(income["period"].unique())
    spec = _income_row_spec()
    rows, styles = [], []
    def get_row_by_name(name):
        for r in rows:
            if r.name == name: return r
        return None
    for item in spec:
        label, stype = item["label"], item["style"]
        if stype == "header":
            rows.append(pd.Series(name=label, data={y: np.nan for y in years}))
            styles.append(stype); continue
        s = _match_and_sum(income, [k.lower() for k in item["keywords"]])
        row = pd.Series(index=years, dtype=float, name=label)
        row.loc[s.index] = s.values
        if label == "Gross Profit" and row.isna().all():
            nr = get_row_by_name("Net Revenue")
            cogs = get_row_by_name("Cost of Goods Sold (COGS)")
            if nr is not None and cogs is not None:
                row = nr - cogs
        rows.append(row); styles.append(stype)
    table = pd.DataFrame(rows)
    style_meta = pd.DataFrame({"style": styles}, index=table.index)
    return table, style_meta

def _format_number(v):
    if pd.isna(v): return ""
    try:
        if abs(v) >= 100: return f"{v:,.0f}"
        return f"{v:,.2f}"
    except Exception:
        return str(v)

def style_table(table: pd.DataFrame, style_meta: pd.DataFrame):
    def header_style(row):
        t = style_meta.loc[row.name, "style"] if row.name in style_meta.index else None
        return ["background-color:#1E3A8A;color:white;font-weight:700;"]*len(row) if t=="header" else [""]*len(row)
    def bold_style(row):
        t = style_meta.loc[row.name, "style"] if row.name in style_meta.index else None
        return ["font-weight:700;"]*len(row) if t=="bold" else [""]*len(row)
    return (table.style
            .format(_format_number)
            .apply(header_style, axis=1)
            .apply(bold_style, axis=1)
            .set_properties(**{"text-align":"right"})
            .set_table_styles([{"selector":"th","props":[("text-align","left")]}]))

def pivot_statement(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty: return pd.DataFrame()
    pv = df.pivot_table(index="account", columns="period", values="value", aggfunc="sum")
    return pv.sort_index()
