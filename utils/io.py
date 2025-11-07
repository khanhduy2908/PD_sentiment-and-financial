
import os
import pandas as pd

def read_csv_smart():
    for path in ["bctc_final.csv", os.path.join("data","bctc_final.csv"), "/mnt/data/bctc_final.csv"]:
        if os.path.exists(path):
            for enc in ("utf-8-sig","utf-8","latin1"):
                try:
                    df = pd.read_csv(path, encoding=enc)
                    if df.shape[1] == 0:
                        continue
                    return df
                except Exception:
                    continue
    raise FileNotFoundError("bctc_final.csv not found in repo root or ./data/.")
