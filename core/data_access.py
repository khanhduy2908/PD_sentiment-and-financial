import os
import io
import pandas as pd
from typing import List, Optional, Tuple, Dict, Any

CANDIDATE_PATHS = [
    "data/bctc_final.csv",
    "/mnt/data/bctc_final.csv",
]

# =========================
# Path utilities
# =========================
def resolve_csv_path(candidates: Optional[List[str]] = None) -> Tuple[str, List[str]]:
    candidates = candidates or CANDIDATE_PATHS
    tried = []
    for p in candidates:
        tried.append(p)
        if os.path.exists(p):
            return p, tried
    raise FileNotFoundError(f"CSV not found. Tried: {', '.join(tried)}")

# =========================
# Robust CSV reader
# =========================
def _is_probably_excel_bytes(b: bytes) -> bool:
    # XLSX (zip-based) thường mở đầu bằng b'PK\x03\x04'
    return b[:2] == b"PK"

def _detect_header_and_sep(text: str) -> Tuple[int, str]:
    """
    Tìm dòng header hợp lệ đầu tiên + delimiter hợp lý.
    Header hợp lệ: sau khi split phải có >= 3 cột.
    Trả về (header_line_index, sep).
    """
    lines = [ln for ln in text.splitlines()]

    # Ưu tiên dòng chứa 'ticker' nếu có
    for i, ln in enumerate(lines[:200]):
        for sep in [",", ";", "\t"]:
            cells = [c.strip() for c in ln.split(sep)]
            if len(cells) >= 3:
                lower = ",".join(cells).lower()
                if "ticker" in lower or "mã" in lower or "symbol" in lower:
                    return i, sep

    # Nếu không có 'ticker', chọn dòng có nhiều cột nhất
    best = (-1, ",", 0)  # (line_idx, sep, ncols)
    for i, ln in enumerate(lines[:200]):
        for sep in [",", ";", "\t"]:
            ncols = len([c for c in ln.split(sep)])
            if ncols > best[2]:
                best = (i, sep, ncols)
    if best[0] >= 0 and best[2] >= 3:
        return best[0], best[1]

    # fallback: coi dòng 0 là header, sep ','
    return 0, ","

def _read_csv_robust(path: str) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Đọc CSV cực kỳ chịu lỗi:
    - Dò encoding
    - Dò delimiter
    - Bỏ các dòng rác trước header
    - Trả info parse để hiển thị
    """
    with open(path, "rb") as f:
        raw = f.read()

    if len(raw) == 0:
        raise ValueError("CSV file is empty.")

    if _is_probably_excel_bytes(raw):
        raise ValueError(
            "This file looks like an Excel (.xlsx) renamed to .csv (zip header detected). "
            "Please export to a real CSV (File → Save As → CSV UTF-8)."
        )

    encodings = ["utf-8-sig", "utf-8", "utf-16", "utf-16le", "utf-16be", "latin-1"]

    last_err = None
    for enc in encodings:
        try:
            text = raw.decode(enc, errors="ignore")
        except Exception as e:
            last_err = e
            continue

        header_idx, sep = _detect_header_and_sep(text)

        # Cắt bỏ phần trước header
        cleaned = "\n".join(text.splitlines()[header_idx:])

        try:
            df = pd.read_csv(
                io.StringIO(cleaned),
                sep=sep,
                engine="python",
            )
            if df.shape[1] <= 1:
                # delimiter này không đúng -> thử tiếp
                last_err = ValueError("Only 1 column after split -> wrong delimiter")
                continue
            info = {"encoding": enc, "sep": sep, "skiprows": header_idx}
            return df, info
        except Exception as e:
            last_err = e
            continue

    raise ValueError(
        "Cannot parse CSV with common encodings/separators "
        f"(last error: {last_err})"
    )

def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]

    # Chuẩn hoá 'ticker'
    if "ticker" not in df.columns:
        guess = None
        for key in ("ticker", "mã", "ma", "symbol", "ck"):
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

    # Các cột text chính
    for col in ("statement", "account", "period"):
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()

    return df

def load_financial_csv(csv_path: Optional[str] = None) -> pd.DataFrame:
    # Tìm path thực sự
    if csv_path is None:
        path, _ = resolve_csv_path()
    else:
        path = csv_path
        if not os.path.exists(path):
            # Cho phép người dùng truyền 'data/bctc_final.csv' hoặc '/mnt/data/...'
            try_path, _ = resolve_csv_path()
            path = try_path

    df, _ = _read_csv_robust(path)
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
    # Nếu có 'period' thì giữ 10 kỳ gần nhất
    if "period" in out.columns:
        out = out.sort_values("period", ascending=False).groupby(  # type: ignore
            by=[c for c in out.columns if c != "period"], as_index=False
        ).head(years)
    return out

# ====== tiện ích hiển thị parse info ở sidebar (optional) ======
def preview_parse_info() -> Dict[str, Any]:
    try:
        path, _ = resolve_csv_path()
        df, info = _read_csv_robust(path)
        return {"path": path, **info, "columns": list(df.columns)[:10]}
    except Exception as e:
        return {"error": str(e)}
