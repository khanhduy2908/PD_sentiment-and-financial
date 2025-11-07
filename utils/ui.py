
import numpy as np

def fmt_ratio(x):
    if x is None: return "-"
    try:
        v = float(x)
        if not np.isfinite(v): return "-"
        if -1.5 <= v <= 1.5:
            return f"{v:.2%}"
        return f"{v:,.2f}"
    except Exception:
        return "-"
