import os
import io
import pandas as pd
from typing import List

CSV_PATH_DEFAULT = "data/bctc_final.csv"

def _ensure_csv_path(csv_path: str):
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"File not found: {csv_path}")
    _, ext = os.path.splitext(csv_path)
    if ext.lower() != ".csv":
        raise ValueError(f"Expected a CSV file, got '{ext}'. Please save/export as real CSV (not Excel).")

def _read_csv_strict(csv_path: str) -> pd.DataFrame:
    """
    Đọc CSV 'thật' (không đọc Excel giả CSV). Có sniff dấu phân cách.
    Không dùng openpyxl. Nếu không parse được -> raise lỗi gợi ý đúng nguyên nhân.
    """
    _ensure_csv_path(csv_path)

    # Đọc thử vài dòng đầu để đoán sep
    with open(csv_path, "rb") as f:
        head = f.read(4096)
    sample = head.decode("utf-8-sig", errors="ignore")

    # Ưu tiên dấu phẩy, nếu không có thử ; rồi \t
    if sample.count(",") >= sample.count(";") and sample.count(",") > 0:
        seps_to_try = [","]
    else:
        seps_to_try = [";", ",", "\t"]

    encodings = ["utf-8-sig", "utf-8", "latin-1"]

    last_err = None
    for enc in encodings:
        for sep in seps_to_try:
            try:
                df = pd.read_csv(csv_path, sep=sep, encoding=enc, engine="python")
                # Nếu chỉ có 1 cột rất dài -> sep sai, thử tiếp
                if df.shape[1] <= 1:
                    continue
                return df
            except Exception as e:
                last_err = e
                continue

    raise ValueError(
        "Cannot parse CSV. Make sure the file is a real CSV (not an .xlsx renamed).\n"
        f"Detail: {last_err}"
    )

def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]

    # Tìm & chuẩn hoá cột ticker
    cols_lower = {c.lower(): c for c in df.columns}
    if "ticker" not in df.columns:
        guess = None
        for k in ["mã", "ma", "symbol", "ck", "ticker"]:
            for c in df.columns:
                if k in c.lower():
                    guess = c; break
            if guess: break
        if guess:
            df = df.rename(columns={guess: "ticker"})
        else:
            # Không có ticker thì vẫn trả về, phần UI sẽ cảnh báo
            pass

    # Chuẩn hoá ticker upper
    if "ticker" in df.columns:
        df["ticker"] = df["ticker"].astype(str).str.upper().str.strip()

    # Chuẩn hoá 'statement' nếu có
    if "statement" in df.columns:
        df["statement"] = df["statement"].astype(str).str.strip().str.lower()

    # Chuẩn hoá 'account' nếu có
    if "account" in df.columns:
        df["account"] = df["account"].astype(str).str.strip()

    # Chuẩn hoá 'period' nếu có
    if "period" in df.columns:
        df["period"] = df["period"].astype(str).str.strip()

    return df

def load_financial_csv(csv_path: str = CSV_PATH_DEFAULT) -> pd.DataFrame:
    """Đọc CSV-only và chuẩn hoá cột cơ bản."""
    df = _read_csv_strict(csv_path)
    return _normalize_columns(df)

def list_tickers(csv_path: str = CSV_PATH_DEFAULT) -> List[str]:
    """Trả về danh sách ticker duy nhất (upper, sort)."""
    df = load_financial_csv(csv_path)
    if "ticker" not in df.columns:
        return []
    tickers = sorted([t for t in df["ticker"].dropna().astype(str).str.upper().unique() if t])
    return tickers

def filter_by_ticker_years(df: pd.DataFrame, ticker: str, years: int = 10) -> pd.DataFrame:
    """
    Lọc theo ticker; nếu có cột period thì lấy 10 kỳ gần nhất (sắp xếp theo period).
    Nếu là wide-format (các cột 2013..2028F) thì trả nguyên DF theo ticker (tabs sẽ pivot hiển thị).
    """
    if "ticker" in df.columns and ticker:
        df = df[df["ticker"].astype(str).str.upper() == ticker.upper()].copy()

    if "period" in df.columns:
        # sắp xếp giảm dần theo period (string), rồi lấy head 'years'
        df = df.sort_values("period", ascending=False).groupby(list(set(df.columns) - {"period"}), as_index=False)\
               .head(years)

    return df
