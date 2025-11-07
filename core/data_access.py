import re
import pandas as pd
from .utils import load_yaml

_YR_RE = re.compile(r"(\d{4})")

def _extract_year_num(p):
    if pd.isna(p):
        return None
    m = _YR_RE.search(str(p))
    return int(m.group(1)) if m else None

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
    df["period"] = df["period"].astype(str).str.strip()
    df = df.dropna(subset=["ticker", "period", "statement", "account", "value"])
    return df

def _sort_periods(periods):
    def key(p):
        y = _extract_year_num(p) or 0
        isF = str(p).lower().endswith('f')
        return (y, 1 if isF else 0, str(p))
    return sorted(periods, key=key)

def filter_by_ticker_years(df: pd.DataFrame, ticker: str, years: int) -> pd.DataFrame:
    x = df[df["ticker"].astype(str).str.upper() == str(ticker).upper()].copy()
    if x.empty:
        return x
    periods = _sort_periods(x["period"].unique().tolist())
    real_years = [p for p in periods if not str(p).lower().endswith('f')]
    last_ref = real_years[-1] if real_years else periods[-1]
    last_y = _extract_year_num(last_ref) or 0
    min_keep = last_y - years + 1
    def keep(p):
        y = _extract_year_num(p) or 0
        return y >= min_keep
    x = x[x["period"].apply(keep)]
    ordered = _sort_periods(sorted(set(x["period"])))
    x["period"] = pd.Categorical(x["period"], categories=ordered, ordered=True)
    return x
