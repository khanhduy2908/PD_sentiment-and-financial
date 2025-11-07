import pandas as pd

def pivot_statement(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()
    pv = df.pivot_table(index="account", columns="period", values="value", aggfunc="sum")
    pv = pv.sort_index()
    return pv

def select_statement(df: pd.DataFrame, key: str) -> pd.DataFrame:
    return df[df["statement"].str.contains(key, case=False, na=False)].copy()
