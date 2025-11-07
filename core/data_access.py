# core/data_access.py
import os
import re
import pandas as pd

_YR_RE = re.compile(r"(\d{4})")

# Tự động nhận dạng cột (không cần YAML). Yêu cầu file có 5 cột logic:
# ticker | period | statement | account | value
_SYNONYMS = {
    "ticker":   ["ticker", "symbol", "code", "stock", "ma_cp", "ma"],
    "period":   ["period", "year", "nam", "ky", "ky_bao_cao"],
    "statement":["statement", "sheet", "loai_bao_cao", "phan"],
    "account":  ["account", "item", "chi_tieu", "khoan_muc", "line"],
    "value":    ["value", "amount", "gia_tri", "so_tien", "val"],
}

def _map_columns(df: pd.DataFrame) -> pd.DataFrame:
    cols = {c.lower().strip(): c for c in df.columns}
    mapping = {}
    for k, alts in _SYNONYMS.items():
        found = None
        for a in alts:
            if a in cols:
                found = cols[a]; break
        if not found:
            raise ValueError(f"Column for '{k}' not found. Given columns: {list(df.columns)}")
        mapping[found] = k
    return df.rename(columns=mapping)

def _extract_year_num(p):
    if pd.isna(p): return None
    m = _YR_RE.search(str(p))
    return int(m.group(1)) if m else None

def load_financial_long(csv_path: str = "data/bctc_final.csv") -> pd.DataFrame:
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"CSV not found: {csv_path}")
    df = pd.read_csv(csv_path)
    df = _map_columns(df)
    # Chuẩn hoá
    df["ticker"]   = df["ticker"].astype(str).str.upper().str.strip()
    df["period"]   = df["period"].astype(str).str.strip()          # ví dụ: 2024F
    df["statement"]= df["statement"].astype(str).str.lower().str.strip()
    df["account"]  = df["account"].astype(str).str.strip()
    df["value"]    = pd.to_numeric(df["value"], errors="coerce")
    df = df.dropna(subset=["ticker","period","statement","account","value"])
    return df

def _sort_periods(periods):
    def key(p):
        y = _extract_year_num(p) or 0
        isF = str(p).lower().endswith("f")
        return (y, 1 if isF else 0, str(p))
    return sorted(periods, key=key)

def filter_by_ticker_years(df: pd.DataFrame, ticker: str, years: int = 10) -> pd.DataFrame:
    x = df[df["ticker"] == str(ticker).upper()].copy()
    if x.empty: return x
    periods = _sort_periods(x["period"].unique().tolist())
    real = [p for p in periods if not str(p).lower().endswith("f")]
    last_ref = real[-1] if real else periods[-1]
    last_y = _extract_year_num(last_ref) or 0
    min_keep = last_y - years + 1
    x = x[x["period"].apply(lambda p: (_extract_year_num(p) or 0) >= min_keep)]
    ordered = _sort_periods(sorted(set(x["period"])))
    x["period"] = pd.Categorical(x["period"], categories=ordered, ordered=True)
    return x
