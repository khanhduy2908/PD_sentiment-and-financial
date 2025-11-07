
import pandas as pd
import numpy as np
import re

def build_display_year_column(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    if "display_year" in df.columns:
        return df
    ycol = None
    for c in ["Year","year","Năm","nam"]:
        if c in df.columns:
            ycol = c; break
    if ycol is None:
        ycol = "Year"
        df[ycol] = np.nan
    df["display_year"] = df[ycol].astype(str).str.replace(r"\.0$","",regex=True)
    return df

def sort_year_labels(labels):
    def _key(s):
        s = str(s)
        base = re.sub(r"[^0-9]","", s)
        try:
            n = int(base)
        except:
            n = 0
        isF = s.endswith("F") or s.endswith("f")
        return (n, 1 if isF else 0)
    return sorted(labels, key=_key)

def pivot_long_to_table(fin_df: pd.DataFrame, stmt_names):
    scol = _pick(fin_df, ["statement","section"])
    lcol = _pick(fin_df, ["lineitem","line_item","line_item_name","item","account"])
    vcol = _pick(fin_df, ["value","amount"])
    ycol = _pick(fin_df, ["display_year","year_label","year"])
    if not (scol and lcol and vcol and ycol):
        return pd.DataFrame()

    mask = fin_df[scol].astype(str).str.upper().isin([s.upper() for s in stmt_names])
    sub = fin_df[mask].copy()
    if sub.empty: return pd.DataFrame()
    sub[ycol] = sub[ycol].astype(str)
    tab = sub.pivot_table(index=lcol, columns=ycol, values=vcol, aggfunc="sum")
    tab = tab.reindex(columns=sort_year_labels(tab.columns))
    return tab

def _pick(df, cands):
    lower = {c.lower(): c for c in df.columns}
    for c in cands:
        if c in df.columns: return c
        if c.lower() in lower: return lower[c.lower()]
    return None
