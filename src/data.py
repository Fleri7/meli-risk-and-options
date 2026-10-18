"""Download and cache daily prices and FRED series to data/prices/.

Every series is saved as one CSV so the notebooks run offline and a broken
API call never changes a result after the fact.
"""

import io
import sys
from pathlib import Path

import pandas as pd
import requests
import yfinance as yf

START = "2015-01-01"
OUT_DIR = Path(__file__).resolve().parents[1] / "data" / "prices"

TICKERS = [
    "MELI", "QQQ", "SPY", "EEM",
    "NU", "STNE", "PAGS", "SE", "AMZN",
    "BRL=X", "MXN=X", "ARS=X",
    "GGAL", "GGAL.BA", "YPF", "YPFD.BA", "PAM", "PAMP.BA", "BMA", "BMA.BA",
    "EMB", "IEF", "DBC", "^BVSP", "^MXX", "^MERV",
    "EBAY", "ETSY", "SHOP", "PYPL",
]

FRED_SERIES = [
    "DGS10", "DGS1MO", "SOFR", "VIXCLS", "VXNCLS", "VXAZNCLS", "DEXBZUS", "DEXMXUS",
    "IRSTCI01BRM156N", "IRSTCI01MXM156N",
]


def file_name(ticker):
    return ticker.replace("=", "_").replace("^", "") + ".csv"


def download_prices():
    for t in TICKERS:
        df = yf.Ticker(t).history(start=START, auto_adjust=False)
        if df.empty:
            print(f"{t}: no data", file=sys.stderr)
            continue
        df.index = df.index.tz_localize(None).date
        df.index.name = "date"
        df[["Open", "High", "Low", "Close", "Adj Close", "Volume"]].to_csv(OUT_DIR / file_name(t))
        print(f"{t}: {len(df)} rows")


def download_fred():
    for s in FRED_SERIES:
        r = requests.get(f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={s}", timeout=60)
        r.raise_for_status()
        df = pd.read_csv(io.StringIO(r.text))
        df.columns = ["date", s]
        df = df[df["date"] >= START]
        df.to_csv(OUT_DIR / f"{s}.csv", index=False)
        print(f"{s}: {len(df)} rows")


if __name__ == "__main__":
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    download_prices()
    download_fred()
