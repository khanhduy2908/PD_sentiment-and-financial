import pandas as pd
import numpy as np

def _find_series(df, keywords):
    mask = df["account"].str.lower().apply(lambda s: any(kw in s for kw in keywords))
    s = (df[mask].groupby("period")["value"].sum().sort_index())
    return s

def build_indicators(fin_long: pd.DataFrame, kw: dict) -> pd.DataFrame:
    income = fin_long[fin_long["statement"].str.contains("income", case=False, na=False)]
    balance = fin_long[fin_long["statement"].str.contains("balance", case=False, na=False)]
    cashflow = fin_long[fin_long["statement"].str.contains("cash", case=False, na=False)]

    rev = _find_series(income, [k.lower() for k in kw["income"]["net_revenue"]])
    cogs = _find_series(income, [k.lower() for k in kw["income"]["cogs"]])
    ebit = _find_series(income, [k.lower() for k in kw["income"]["ebit"]])
    ni  = _find_series(income, [k.lower() for k in kw["income"]["net_income"]])
    ta  = _find_series(balance, [k.lower() for k in kw["balance"]["total_assets"]])
    te  = _find_series(balance, [k.lower() for k in kw["balance"]["total_equity"]])
    tl  = _find_series(balance, [k.lower() for k in kw["balance"]["total_liabilities"]])
    ocf = _find_series(cashflow,[k.lower() for k in kw["cashflow"]["ocf"]])

    df = pd.DataFrame({
        "Revenue": rev,
        "COGS": cogs,
        "EBIT": ebit,
        "NetIncome": ni,
        "TotalAssets": ta,
        "TotalEquity": te,
        "TotalLiabilities": tl,
        "OperatingCF": ocf
    })

    df["GrossProfit"] = df["Revenue"] - df["COGS"]
    df["GrossMargin"] = df["GrossProfit"] / df["Revenue"].replace(0, np.nan)
    df["EBITMargin"]  = df["EBIT"] / df["Revenue"].replace(0, np.nan)
    df["NetMargin"]   = df["NetIncome"] / df["Revenue"].replace(0, np.nan)
    df["ROA"]         = df["NetIncome"] / df["TotalAssets"].replace(0, np.nan)
    df["ROE"]         = df["NetIncome"] / df["TotalEquity"].replace(0, np.nan)
    df["Leverage"]    = df["TotalAssets"] / df["TotalEquity"].replace(0, np.nan)
    df["DebtToAssets"]= df["TotalLiabilities"] / df["TotalAssets"].replace(0, np.nan)
    df["OCF_to_Debt"] = df["OperatingCF"] / df["TotalLiabilities"].replace(0, np.nan)
    return df
