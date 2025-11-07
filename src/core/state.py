
from dataclasses import dataclass, field
from typing import Optional
import pandas as pd

@dataclass
class AppState:
    ticker: str = ""
    years: int = 10
    freq: str = "Q"  # reserved for later
    fin_df: Optional[pd.DataFrame] = field(default=None)   # long format: ticker, period, statement, account, value
