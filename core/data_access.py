# core/data_access.py
import os
import re
import io
import pandas as pd

# Synonyms để auto-map về schema chuẩn
_SYNONYMS = {
    "ticker":   ["ticker","symbol","code","stock","ma_cp","ma"],
    "period":   ["period","year","nam","ky","ky_bao_cao"],
    "statement":["statement","sheet","loai_bao_cao","phan","group"],
    "account":  ["account","item","chi_tieu","khoan_muc","line","ten_chi_tieu"],
    "value":    ["value","amount","gia_tri","so_tien","val"],
}

_YR_COL_RE = re.compile(r"^\s*(20\d{2})(?:F)?\s*$", re.IGNORECASE)
_YR_CELL_RE = re.compile(r"(20\d{2})(F)?", re.IGNORECASE)

def _parse_number(v):
    """Chuẩn hóa số kiểu Việt & string lẫn NaN."""
    if pd.isna(v): return None
    s = str(v).strip()
    if s == "" or s.lower() in {"nan","none","-"}: return None
    # Nếu là format VN: 10.277,19  ->  10277.19
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".")
    else:
        # Nếu chỉ có ',' dùng làm thập phân
        if "," in s and "." not in s:
            s = s.replace(",", ".")
        # nếu chỉ có '.' giữ nguyên
    try:
        return float(s)
    except Exception:
        return None

def _map_columns_long(df: pd.DataFrame) -> pd.DataFrame:
    """Map cột khi file đã là long-format."""
    lower = {c.lower().strip(): c for c in df.columns}
    mapping = {}
    for std, alts in _SYNONYMS.items():
        src = next((lower[a] for a in alts if a in lower), None)
        if not src:
            raise ValueError(
                f"Column for '{std}' not found. Columns: {list(df.columns)}"
            )
        mapping[src] = std
    out = df.rename(columns=mapping)
    out["ticker"]    = out["ticker"].astype(str).str.upper().str.strip()
    out["period"]    = out["period"].astype(str).str.strip()
    out["statement"] = out["statement"].astype(str).str.lower().str.strip()
    out["account"]   = out["account"].astype(str).str.strip()
    out["value"]     = out["value"].apply(_parse_number)
    out = out.dropna(subset=["ticker","period","statement","account","value"])
    return out

def _detect_year_columns(df: pd.DataFrame):
    yrs = []
    for c in df.columns:
        if _YR_COL_RE.match(str(c)):
            yrs.append(str(c).strip())
    return yrs

def _wide_to_long(df: pd.DataFrame) -> pd.DataFrame:
    """
    Chuyển bảng dạng:
      ticker | statement | account | 2013 | 2014 | ... | 2028F
    -> long: ticker, period, statement, account, value
    """
    cols = [c for c in df.columns]
    lower = {c.lower().strip(): c for c in cols}

    # bắt buộc có account
    acc_col = next((lower[a] for a in _SYNONYMS["account"] if a in lower), None)
    if not acc_col:
        # thử đoán: cột đầu tiên
        acc_col = cols[0]

    # optional
    tic_col = next((lower[a] for a in _SYNONYMS["ticker"] if a in lower), None)
    stm_col = next((lower[a] for a in _SYNONYMS["statement"] if a in lower), None)

    year_cols = _detect_year_columns(df)
    if not year_cols:
        raise ValueError("Cannot detect year columns (2013..2028F).")

    id_vars = [acc_col]
    if tic_col: id_vars.append(tic_col)
    if stm_col: id_vars.append(stm_col)

    melt = df.melt(id_vars=id_vars, value_vars=year_cols,
                   var_name="period", value_name="value")

    # hoàn thiện các cột
    melt["account"] = melt[acc_col].astype(str).str.strip()
    melt["ticker"]  = (melt[tic_col].astype(str).str.upper().str.strip()
                       if tic_col else "TICK")  # default 1 mã nếu thiếu
    melt["statement"] = (melt[stm_col].astype(str).str.lower().str.strip()
                         if stm_col else "income")  # default nếu thiếu
    melt["period"]  = melt["period"].astype(str).str.strip()
    melt["value"]   = melt["value"].apply(_parse_number)

    melt = melt[["ticker","period","statement","account","value"]]
    melt = melt.dropna(subset=["value"])
    return melt

def _try_read_csv(csv_path: str) -> pd.DataFrame:
    # thử encoding/sep khác nhau
    encodings = ["utf-8", "utf-8-sig", "cp1258", "latin1"]
    seps = [",", ";", "\t"]
    last_err = None
    for enc in encodings:
        for sep in seps:
            try:
                df = pd.read_csv(csv_path, encoding=enc, sep=sep, engine="python")
                if df is not None and len(df.columns) > 1:
                    return df
            except Exception as e:
                last_err = e
                continue
    # lần cuối: cố đọc raw rồi tự split theo dấu chấm phẩy
    try:
        with open(csv_path, "rb") as f:
            raw = f.read()
        text = raw.decode("utf-8", errors="ignore")
        # heuristics: nếu có nhiều dấu ';' thì split theo ';'
        sep = ";" if text.count(";") > text.count(",") else ","
        df = pd.read_csv(io.StringIO(text), sep=sep, engine="python")
        if len(df.columns) > 1:
            return df
    except Exception as e:
        last_err = e
    raise last_err if last_err else ValueError("Cannot read CSV with any fallback.")

def load_financial_long(csv_path: str = "data/bctc_final.csv") -> pd.DataFrame:
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"CSV not found: {csv_path}")

    # 1) thử CSV với nhiều fallback
    try:
        df = _try_read_csv(csv_path)
    except Exception:
        # 2) nếu thất bại, thử đọc như Excel
        try:
            df = pd.read_excel(csv_path, engine="openpyxl")
        except Exception as e:
            raise ValueError(
                f"Cannot parse file '{csv_path}' as CSV or Excel. Detail: {e}"
            )

    if df.empty:
        raise ValueError(f"File '{csv_path}' is empty or has no visible columns.")

    # 3) xác định long hay wide
    lower_cols = [c.lower().strip() for c in df.columns]
    has_long = all(any(a in lower_cols for a in _SYNONYMS[k]) for k in ["ticker","period","statement","account","value"])
    if has_long:
        out = _map_columns_long(df)
    else:
        out = _wide_to_long(df)

    # sắp xếp period theo năm và hậu tố F
    def _year_key(p):
        if pd.isna(p): return (0, 0)
        m = _YR_CELL_RE.search(str(p))
        if not m: return (0, 0)
        y = int(m.group(1)); isF = (m.group(2) is not None)
        return (y, 1 if isF else 0)

    cats = sorted(out["period"].astype(str).unique(), key=_year_key)
    out["period"] = pd.Categorical(out["period"], categories=cats, ordered=True)
    return out

def filter_by_ticker_years(df: pd.DataFrame, ticker: str, years: int = 10) -> pd.DataFrame:
    t = str(ticker).upper()
    x = df[df["ticker"] == t].copy()
    if x.empty:
        return x
    # tìm năm cuối cùng trong dữ liệu thật (không F)
    real = [p for p in x["period"].cat.categories if not str(p).lower().endswith("f")]
    last_ref = real[-1] if real else x["period"].cat.categories[-1]
    last_year = int(_YR_CELL_RE.search(str(last_ref)).group(1))
    min_keep = last_year - years + 1

    def _keep(p):
        m = _YR_CELL_RE.search(str(p))
        if not m: return False
        return int(m.group(1)) >= min_keep

    x = x[x["period"].astype(str).map(_keep)]
    cats = [p for p in x["period"].cat.categories if _keep(p)]
    x["period"] = pd.Categorical(x["period"].astype(str), categories=cats, ordered=True)
    return x
