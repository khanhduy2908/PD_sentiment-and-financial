import os
import pandas as pd
from typing import List, Optional, Tuple

# Thử theo thứ tự: repo/data và /mnt/data (nơi bạn đã up)
CANDIDATE_PATHS = [
    "data/bctc_final.csv",
    "/mnt/data/bctc_final.csv",
]

def resolve_csv_path(candidates: Optional[List[str]] = None) -> Tuple[str, List[str]]:
    candidates = candidates or CANDIDATE_PATHS
    tried = []
    for p in candidates:
        tried.append(p)
        if os.path.exists(p):
            return p, tried
    raise FileNotFoundError(f"CSV not found. Tried: {', '.join(tried)}")

def _is_probably_excel_bytes(sample: bytes) -> bool:
    # XLSX là zip-based, thường mở đầu bằng b'PK\x03\x04'
    return sample[:2] == b"PK"

def _read_csv_strict(csv_path: str) -> pd.DataFrame:
    # 1) đọc một khúc đầu để đoán delimiter + phát hiện Excel giả CSV
    with open(csv_path, "rb") as f:
        head = f.read(4096)

    if _is_probably_excel_bytes(head):
        raise ValueError(
            "This file looks like an Excel (.xlsx) renamed to .csv (zip header detected). "
            "Please export to a real CSV from Excel (File → Save As → CSV UTF-8)."
        )

    # đoán delimiter dựa trên tần suất
    text = head.decode("utf-8-sig", errors="ignore")
    comma = text.count(",")
    semi  = text.count(";")
    tabs  = text.count("\t")

    seps = []
    if comma >= semi and comma >= tabs and comma > 0:
        seps = ["," , ";", "\t"]
    elif semi >= tabs and semi > 0:
        seps = [";", ",", "\t"]
    elif tabs > 0:
        seps = ["\t", ",", ";"]
    else:
        # fallback vẫn thử các phương án
        seps = [",", ";", "\t"]

    encodings = ["utf-8-sig", "utf-8", "latin-1"]

    last_err = None
    for enc in encodings:
        for sep in seps:
            try:
                df = pd.read_csv(csv_path, sep=sep, encoding=enc, engine="python")
                # nếu chỉ ra 1 cột rất dài => sep sai
                if df.shape[1] <= 1:
                    continue
                return df
            except Exception as e:
                last_err = e
                continue

    raise ValueError(
        "Cannot parse CSV with common delimiters/encodings. "
        "Ensure it's a real CSV (not XLSX renamed) and uses ',', ';' or TAB. "
        f"Detail: {last_err}"
    )

def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]

    # chuẩn hoá cột ticker
    if "ticker" not in df.columns:
        guess = None
        for key in ("mã", "ma", "symbol", "ck", "ticker"):
            for c in df.columns:
                if key.lower() in c.lower():
                    guess = c
                    break
            if guess:
                break
        if guess:
            df = df.rename(columns={guess: "ticker"})

    if "ticker" in df.columns:
        df["ticker"] = df["ticker"].astype(str).str.upper().str.strip()

    # chuẩn hoá các cột gợi ý (nếu có)
    for col in ("statement", "account", "period"):
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()

    return df

def load_financial_csv(csv_path: Optional[str] = None) -> pd.DataFrame:
    path, tried = resolve_csv_path(CANDIDATE_PATHS if csv_path is None else [csv_path])
    df = _read_csv_strict(path)
    df = _normalize_columns(df)
    if df.empty:
        raise ValueError(f"CSV parsed but empty. Path: {path}")
    return df

def list_tickers(csv_path: Optional[str] = None) -> List[str]:
    df = load_financial_csv(csv_path)
    if "ticker" not in df.columns:
        return []
    tickers = (
        df["ticker"]
        .dropna()
        .astype(str)
        .str.upper()
        .str.strip()
        .unique()
        .tolist()
    )
    tickers = sorted([t for t in tickers if t and t != "NAN"])
    return tickers

def filter_by_ticker_years(df: pd.DataFrame, ticker: str, years: int = 10) -> pd.DataFrame:
    out = df.copy()
    if "ticker" in out.columns and ticker:
        out = out[out["ticker"].astype(str).str.upper() == ticker.upper()].copy()

    # Nếu có period thì lấy 10 kỳ gần nhất theo period (string sort)
    if "period" in out.columns:
        out = (
            out.sort_values("period", ascending=False)
              .groupby(list(set(out.columns) - {"period"}), as_index=False)
              .head(years)
        )
    return out
