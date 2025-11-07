# core/transforms.py
import pandas as pd
import numpy as np
from typing import List, Dict, Tuple

# ---------- helpers cơ bản (giữ nguyên hành vi cũ) ----------
def pivot_statement(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()
    pv = df.pivot_table(index="account", columns="period", values="value", aggfunc="sum")
    pv = pv.sort_index()
    return pv

def select_statement(df: pd.DataFrame, key: str) -> pd.DataFrame:
    return df[df["statement"].str.contains(key, case=False, na=False)].copy()

# ---------- cấu hình hàng chuẩn cho Income ----------
def _income_row_spec() -> List[Dict]:
    """
    Mỗi phần tử: {label, keywords, style}
    - label: tên dòng hiển thị
    - keywords: các từ khóa để match account (contains, case-insensitive)
    - style: 'header' | 'bold' | None
    Thứ tự trong list = thứ tự hiển thị.
    """
    return [
        {"label": "INCOME STATEMENT", "keywords": [], "style": "header"},

        {"label": "Net Revenue", "keywords": ["net revenue", "revenue", "sales"], "style": "bold"},
        {"label": "Cost of Goods Sold (COGS)", "keywords": ["cogs", "cost of goods"], "style": None},
        {"label": "Gross Profit", "keywords": ["gross profit"], "style": "bold"},
        {"label": "Financial Income", "keywords": ["financial income", "interest income", "dividend income"], "style": None},
        {"label": "Financial Expenses", "keywords": ["financial expense", "interest expense"], "style": None},
        {"label": "Selling Expenses", "keywords": ["selling expense"], "style": None},
        {"label": "General and Administrative Expenses", "keywords": ["administrative", "g&a", "general and administrative"], "style": None},
        {"label": "Profit/(Loss) from Business Activities", "keywords": ["operating profit", "profit from operations", "ebit"], "style": "bold"},
        {"label": "Other Income, Net", "keywords": ["other income"], "style": None},
        {"label": "Net Profit/(Loss) Before Tax", "keywords": ["profit before tax", "pre-tax profit"], "style": "bold"},
        {"label": "Corporate Income Tax Expense", "keywords": ["corporate income tax", "income tax expense"], "style": None},
        {"label": "Net Profit/(Loss) After Tax", "keywords": ["net profit", "net income", "profit after tax"], "style": "bold"},
        {"label": "Basic Earnings Per Share (VND)", "keywords": ["basic earnings per share", "basic eps", "eps"], "style": None},

        {"label": "INCOME STATEMENT ASSUMPTIONS", "keywords": [], "style": "header"},
        {"label": "Profitability Ratio from Joint Ventures", "keywords": ["profitability ratio from joint ventures"], "style": None},
        {"label": "Selling Expense Ratio", "keywords": ["selling expense ratio"], "style": None},
        {"label": "General and Administrative Expense Ratio", "keywords": ["administrative expense ratio"], "style": None},
        {"label": "Financial Revenue Ratio", "keywords": ["financial revenue ratio"], "style": None},
        {"label": "Financial Expense Ratio", "keywords": ["financial expense ratio"], "style": None},
        {"label": "Other Income Ratio", "keywords": ["other income ratio"], "style": None},
        {"label": "Corporate Income Tax Rate", "keywords": ["corporate income tax rate"], "style": None},
        {"label": "Total Investment (Short-Term Investment Value + Long-Term)", "keywords": ["total investment"], "style": None},
        {"label": "Interest Rate on Loans", "keywords": ["interest rate on loans"], "style": None},
    ]

# ---------- xây dựng bảng Income theo spec ----------
def _match_and_sum(income_df: pd.DataFrame, keywords: List[str]) -> pd.Series:
    """Tìm các account có chứa bất kỳ keyword nào và cộng theo năm."""
    if not keywords:
        return pd.Series(dtype=float)
    mask = income_df["account"].str.lower().apply(
        lambda s: any(kw in s for kw in keywords)
    )
    s = (
        income_df[mask]
        .groupby("period")["value"]
        .sum()
        .sort_index()
    )
    return s

def build_income_table(fin_filtered: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Trả về:
      - table: DataFrame đã sắp xếp + có hàng header
      - style_meta: DataFrame 1 cột 'style' để biết hàng nào là header/bold
    """
    if fin_filtered.empty:
        return pd.DataFrame(), pd.DataFrame()

    income = select_statement(fin_filtered, "income")
    if income.empty:
        return pd.DataFrame(), pd.DataFrame()

    spec = _income_row_spec()
    years = sorted(income["period"].dropna().unique().tolist())
    rows = []
    styles = []

    # Với mỗi label trong spec: tổng hợp theo keywords; nếu không có dữ liệu → để trống (NaN)
    for item in spec:
        label = item["label"]
        stype = item["style"]
        if stype == "header":
            # hàng header: chỉ chứa NaN phần số
            rows.append(pd.Series(name=label, data={y: np.nan for y in years}))
            styles.append(stype)
            continue

        s = _match_and_sum(income, [k.lower() for k in item["keywords"]])
        # đưa về cùng cột years
        row = pd.Series(index=years, dtype=float, name=label)
        row.loc[s.index] = s.values
        rows.append(row)
        styles.append(stype)

    table = pd.DataFrame(rows)
    style_meta = pd.DataFrame({"style": styles}, index=table.index)

    # Nếu muốn tính một số dòng không có sẵn (ví dụ Gross Profit = Revenue - COGS) ta có thể bổ sung ở đây.
    # Chỉ tính nếu một trong 2 dòng thiếu.
    if "Gross Profit" in table.index:
        if table.loc["Gross Profit"].isna().all():
            if "Net Revenue" in table.index and "Cost of Goods Sold (COGS)" in table.index:
                table.loc["Gross Profit"] = table.loc["Net Revenue"] - table.loc["Cost of Goods Sold (COGS)"]

    return table, style_meta

# ---------- định dạng số & style ----------
def _format_number(v: float) -> str:
    if pd.isna(v):
        return ""
    # Hiển thị dạng ngắn gọn: số nguyên nếu lớn, 2 chữ số thập phân nếu nhỏ
    if abs(v) >= 100:
        return f"{v:,.0f}"
    return f"{v:,.2f}"

def style_income_table(table: pd.DataFrame, style_meta: pd.DataFrame):
    """Trả về pandas Styler với header xanh dương, dòng bold và căn phải đẹp."""
    def highlight_headers(row):
        style = style_meta.loc[row.name, "style"] if row.name in style_meta.index else None
        if style == "header":
            return ["background-color: #1E3A8A; color: white; font-weight: 700;"] * len(row)
        return ["" for _ in row]

    def bold_important(row):
        style = style_meta.loc[row.name, "style"] if row.name in style_meta.index else None
        if style == "bold":
            return ["font-weight: 700;"] * len(row)
        return ["" for _ in row]

    styler = (
        table.style
        .format(_format_number)
        .apply(highlight_headers, axis=1)
        .apply(bold_important, axis=1)
        .set_properties(**{"text-align": "right"})
        .set_table_styles([{"selector": "th", "props": [("text-align", "left")]}])
    )
    return styler
