import os, io, re, csv
import pandas as pd
from typing import List, Optional, Tuple, Dict, Any
from pandas.errors import EmptyDataError, ParserError

# Các vị trí có thể chứa CSV (ưu tiên file bạn đã để trong /data)
CANDIDATE_PATHS = [
    "data/bctc_final.csv",
    "/mnt/data/bctc_final.csv",
]

def resolve_csv_path(candidates: Optional[List[str]] = None) -> Tuple[str, List[str]]:
    tried = []
    for p in (candidates or CANDIDATE_PATHS):
        tried.append(p)
        if os.path.exists(p):
            return p, tried
    raise FileNotFoundError(f"CSV not found. Tried: {', '.join(tried)}")

# ---------- Helpers ----------
def _is_xlsx_bytes(b: bytes) -> bool:
    return b[:2] == b"PK"  # XLSX (zip) có header 'PK'

def _strip_control_chars(s: str) -> str:
    # bỏ BOM/zero-width/etc.
    return s.replace("\ufeff", "").replace("\x00", "")

def _guess_header_and_sep(lines: List[str]) -> Tuple[int, str]:
    """
    Chọn dòng header hợp lệ đầu tiên + delimiter tối ưu.
    Tiêu chí: dòng có ≥3 cột và chứa ít nhất 1 ký tự chữ cái.
    Ưu tiên dòng có 'ticker'/'mã'/'symbol' trong text.
    """
    def is_header_like(cells: List[str]) -> bool:
        if len(cells) < 3: 
            return False
        text = " ".join(cells).lower()
        return any(ch.isalpha() for ch in text)

    # 1) Ưu tiên dòng có 'ticker'/'mã'/'symbol'
    for i, ln in enumerate(lines[:300]):
        for sep in [",", ";", "\t"]:
            cells = [c.strip() for c in ln.split(sep)]
            if is_header_like(cells):
                joined = " ".join(cells).lower()
                if any(k in joined for k in ("ticker", "mã", "ma ", "symbol")):
                    return i, sep

    # 2) Chọn dòng có nhiều cột nhất
    best = (-1, ",", 0)
    for i, ln in enumerate(lines[:300]):
        for sep in [",", ";", "\t"]:
            n = len(ln.split(sep))
            if n > best[2]:
                best = (i, sep, n)
    if best[0] >= 0 and best[2] >= 3:
        return best[0], best[1]

    return 0, ","  # fallback

def _pandas_try_read(text: str, sep: str) -> pd.DataFrame:
    # pandas engine=python cho phép sep phức tạp; on_bad_lines='skip' để lờ dòng bẩn
    return pd.read_csv(io.StringIO(text), sep=sep, engine="python", on_bad_lines="skip")

def _csv_manual_parse(text: str, sep: str) -> pd.DataFrame:
    # parse bằng csv module khi pandas chịu thua
    reader = csv.reader(io.StringIO(text), delimiter=sep)
    rows = [row for row in reader if any(cell.strip() for cell in row)]
    if not rows or len(rows[0]) < 2:
        raise EmptyDataError("manual csv parse: no valid rows")
    header = [c.strip() for c in rows[0]]
    data = [[c.strip() for c in r] for r in rows[1:]]
    # pad rows nếu thiếu cột
    width = len(header)
    for r in data:
        if len(r) < width:
            r += [""] * (width - len(r))
    return pd.DataFrame(data, columns=header)

def _read_csv_robust(path: str) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    raw = open(path, "rb").read()
    if not raw:
        raise EmptyDataError("file is empty")
    if _is_xlsx_bytes(raw):
        raise ValueError(
            "This file looks like an Excel (.xlsx) renamed to .csv. "
            "Please export a real CSV (Save As → CSV UTF-8)."
        )

    enc_candidates = ["utf-8-sig", "utf-8", "utf-16", "utf-16le", "utf-16be", "cp1258", "latin-1"]
    last_err: Optional[Exception] = None

    for enc in enc_candidates:
        try:
            text = raw.decode(enc, errors="ignore")
        except Exception as e:
            last_err = e
            continue

        text = _strip_control_chars(text)
        lines = text.splitlines()
        # bỏ các dòng rỗng đầu file
        while lines and not lines[0].strip():
            lines.pop(0)
        if not lines:
            last_err = EmptyDataError("no visible lines after stripping")
            continue

        header_idx, sep = _guess_header_and_sep(lines)
        cleaned = "\n".join(lines[header_idx:])

        # Thử pandas với sep đoán được
        try:
            df = _pandas_try_read(cleaned, sep)
            if df.shape[1] <= 1:
                # có thể sep khác: thử tất cả sep
                for s in [",", ";", "\t"]:
                    try:
                        df2 = _pandas_try_read(cleaned, s)
                        if df2.shape[1] > 1:
                            return df2, {"encoding": enc, "sep": s, "skiprows": header_idx}
                    except Exception as e2:
                        last_err = e2
                        pass
                # thử infer tự động
                try:
                    df3 = pd.read_csv(io.StringIO(cleaned), sep=None, engine="python", on_bad_lines="skip")
                    if df3.shape[1] > 1:
                        return df3, {"encoding": enc, "sep": "infer", "skiprows": header_idx}
                except Exception as e3:
                    last_err = e3
            else:
                return df, {"encoding": enc, "sep": sep, "skiprows": header_idx}
        except Exception as e:
            last_err = e
            # Thử manual csv parser
            try:
                df4 = _csv_manual_parse(cleaned, sep)
                return df4, {"encoding": enc, "sep": sep, "skiprows": header_idx, "manual": True}
            except Exception as e4:
                last_err = e4
                continue

    raise ValueError(f"Cannot parse CSV with common encodings/separators (last error: {last_err})")

def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]
    # map ticker
    if "ticker" not in df.columns:
        guess = None
        for key in ("ticker", "mã", "ma", "symbol", "ck"):
            for c in df.columns:
                if key.lower() in str(c).lower():
                    guess = c; break
            if guess: break
        if guess: df = df.rename(columns={guess: "ticker"})

    if "ticker" in df.columns:
        df["ticker"] = df["ticker"].astype(str).str.upper().str.strip()

    for col in ("statement", "account", "period", "year"):
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()

    return df

# ========== Public APIs ==========
def load_financial_csv(csv_path: Optional[str] = None) -> pd.DataFrame:
    if csv_path and os.path.exists(csv_path):
        path = csv_path
    else:
        path, _ = resolve_csv_path()
    df, _info = _read_csv_robust(path)
    df = _normalize_columns(df)
    if df.empty:
        raise ValueError("CSV parsed but empty.")
    return df

def list_tickers(csv_path: Optional[str] = None) -> List[str]:
    df = load_financial_csv(csv_path)
    if "ticker" not in df.columns:
        return []
    tks = (
        df["ticker"].dropna().astype(str).str.upper().str.strip().unique().tolist()
    )
    return sorted([t for t in tks if t and t != "NAN"])

def filter_by_ticker_years(df: pd.DataFrame, ticker: str, years: int = 10) -> pd.DataFrame:
    out = df.copy()
    if "ticker" in out.columns and ticker:
        out = out[out["ticker"].astype(str).str.upper() == ticker.upper()].copy()
    # nếu có period/year thì giữ 10 kỳ gần nhất
    time_col = "period" if "period" in out.columns else ("year" if "year" in out.columns else None)
    if time_col:
        # convert to sortable
        out[time_col] = out[time_col].astype(str)
        out = out.sort_values(time_col, ascending=False)
        # giữ tối đa 'years' mẫu cho mỗi (statement, account)
        keys = [c for c in ["statement", "account"] if c in out.columns]
        if keys:
            out = out.groupby(keys, as_index=False).head(years)
        else:
            out = out.head(years)
    return out

def preview_parse_info() -> Dict[str, Any]:
    try:
        path, _ = resolve_csv_path()
        raw = open(path, "rb").read()
        size = len(raw)
        info: Dict[str, Any] = {"path": path, "size_bytes": size}
        df, pi = _read_csv_robust(path)
        info.update(pi)
        info["columns"] = list(df.columns)[:12]
        return info
    except Exception as e:
        return {"error": str(e)}
