from typing import Tuple
import pandas as pd
import numpy as np
from .utils import load_yaml

def load_configs():
    app_cfg = load_yaml("config/app.yaml")
    path_cfg = load_yaml("config/paths.yaml")
    map_cfg = load_yaml("config/mappings.yaml")
    return app_cfg, path_cfg, map_cfg

def load_financial_long(path_cfg, map_cfg) -> pd.DataFrame:
    path = path_cfg["paths"]["financial_csv"]
    df = pd.read_csv(path)
    m = map_cfg["financial"]
    df = df.rename(columns={
        m["ticker"]: "ticker",
        m["period"]: "period",
        m["statement"]: "statement",
        m["account"]: "account",
        m["value"]: "value",
    })
    df["statement"] = df["statement"].astype(str).str.lower().str.strip()
    df["account"] = df["account"].astype(str).str.strip()
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df["period"] = pd.to_numeric(df["period"], errors="coerce").astype("Int64")
    df = df.dropna(subset=["ticker", "period", "statement", "account", "value"])
    return df

def filter_by_ticker_years(df: pd.DataFrame, ticker: str, years: int) -> pd.DataFrame:
    x = df[df["ticker"].astype(str).str.upper() == str(ticker).upper()].copy()
    if x.empty:
        return x
    years_sorted = sorted([int(y) for y in x["period"].dropna().unique()])
    last_year = max(years_sorted)
    first_keep = last_year - years + 1
    return x[(x["period"] >= first_keep) & (x["period"] <= last_year)]
