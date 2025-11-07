# core/data_access.py
import os
import re
import pandas as pd

# Tự động map cột -> (ticker, period, statement, account, value)
_SYNONYMS = {
    "ticker":   ["ticker", "symbol", "code", "stock", "ma_cp", "ma"],
    "period":   ["period", "year", "nam", "ky", "ky_bao_cao"],
    "statement":["statement", "sheet", "loai_bao_cao", "phan"],
    "account":  ["account", "item", "chi_tieu", "khoan_muc", "line"],
    "value":    ["value", "amount", "gia_tri", "so_tien", "val"],
}
_YR_RE = re.compile(r"(\d{4})")

def _map_columns(df: pd.DataFrame) -> pd.DataFrame:
    cols = {c.lower().strip(): c for c in df.columns}
    mapping = {}
    for k, alts in _SYNONYMS.items():
        src = next((cols[a] for a in alts if a in cols), None)
        if not src:
            raise ValueError(f"Column for '{k}' not found. Given columns: {list(df.columns)}")
        mapping[src] = k
    return df.rename(columns=mapping)

def load_financial_long(csv_path: str = "data/bctc_final.csv") -> pd.DataFrame:
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"CSV not found: {csv_path}")
    df = pd.read_csv(csv_path)
    df = _map_columns(df)
    # Chuẩn hóa
    df["ticker"]    = df["ticker"].astype(str).str.upper().str.strip()
    df["period"]    = df["period"].astype(str).str.strip()  # giữ 2024F
    df["statement"] = df["statement"].astype(str).str.lower().str.strip()
    df["account"]   = df["account"].astype(str).str.strip()
    df["value"]     = pd.to_numeric(df["value"], errors="coerce")
    df = df.dropna(subset=["ticker","period","statement","account","value"])
    return df

def _year_num(p):
    if pd.isna(p): return 0
    m = _YR_RE.search(str(p))
    return int(m.group(1)) if m else 0

def _sort_periods(periods):
    def key(p):
        y = _year_num(p)
        isF = str(p).lower().endswith("f")
        return (y, 1 if isF else 0, str(p))
    return sorted(periods, key=key)

def filter_by_ticker_years(df: pd.DataFrame, ticker: str, years: int = 10) -> pd.DataFrame:
    x = df[df["ticker"] == str(ticker).upper()].copy()
    if x.empty: 
        return x
    periods = _sort_periods(x["period"].unique().tolist())
    real = [p for p in periods if not str(p).lower().endswith("f")]
    last_ref = real[-1] if real else periods[-1]
    last_y = _year_num(last_ref)
    min_keep = last_y - years + 1
    x = x[x["period"].apply(lambda p: _year_num(p) >= min_keep)]
    ordered = _sort_periods(sorted(set(x["period"])))
    x["period"] = pd.Categorical(x["period"], categories=ordered, ordered=True)
    return x
