"""Download and cache daily prices and FRED series to data/prices/.

Every series is saved as one CSV so the notebooks run offline and a broken
API call never changes a result after the fact.
"""

import io
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import requests
import yfinance as yf

START = "2010-01-01"
OUT_DIR = Path(__file__).resolve().parents[1] / "data" / "prices"

TICKERS = [
    "MELI", "QQQ", "SPY", "EEM",
    "NU", "STNE", "PAGS", "SE", "AMZN",
    "BRL=X", "MXN=X", "ARS=X",
    "GGAL", "GGAL.BA", "YPF", "YPFD.BA", "PAM", "PAMP.BA", "BMA", "BMA.BA",
    "EMB", "IEF", "DBC", "^BVSP", "^MXX", "^MERV", "ARGT",
    "EBAY", "ETSY", "SHOP", "PYPL",
]

EARNINGS_CIKS = {
    "MELI": 1099590, "AMZN": 1018724, "EBAY": 1065088, "ETSY": 1370637, "SHOP": 1594805, "PYPL": 1633917,
}

FRED_SERIES = [
    "DGS10", "DGS1MO", "SOFR", "VIXCLS", "VXNCLS", "VXAZNCLS", "DEXBZUS", "DEXMXUS",
    "IRSTCI01BRM156N", "IRSTCI01MXM156N",
]


def file_name(ticker):
    return ticker.replace("=", "_").replace("^", "") + ".csv"


def download_prices():
    # end is exclusive, so today's unfinished session is never cached as a close
    today = datetime.now(ZoneInfo("America/New_York")).date().isoformat()
    for t in TICKERS:
        df = yf.Ticker(t).history(start=START, end=today, auto_adjust=False)
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


def download_bcra():
    """Official wholesale peso rate (Com. A 3500) from the BCRA API, one year per call."""
    rows = []
    today = datetime.now(ZoneInfo("America/Argentina/Buenos_Aires")).date().isoformat()
    for year in range(int(START[:4]), int(today[:4]) + 1):
        r = requests.get(
            "https://api.bcra.gob.ar/estadisticascambiarias/v1.0/Cotizaciones/USD",
            params={"fechadesde": f"{year}-01-01", "fechahasta": min(f"{year}-12-31", today)},
            timeout=60,
        )
        r.raise_for_status()
        rows += [(d["fecha"], d["detalle"][0]["tipoCotizacion"]) for d in r.json()["results"] if d["detalle"]]
    df = pd.DataFrame(rows, columns=["date", "ars_per_usd"]).sort_values("date")
    df.to_csv(OUT_DIR / "BCRA_USD.csv", index=False)
    print(f"BCRA_USD: {len(df)} rows")


def download_earnings_dates():
    """Earnings release dates from 8-K Item 2.02 filings on EDGAR (times are UTC)."""
    headers = {"User-Agent": "meli-risk-and-options research project"}
    rows = []
    for ticker, cik in EARNINGS_CIKS.items():
        r = requests.get(f"https://data.sec.gov/submissions/CIK{cik:010d}.json", headers=headers, timeout=60)
        r.raise_for_status()
        f = r.json()["filings"]["recent"]
        rows += [
            (ticker, f["filingDate"][i], f["acceptanceDateTime"][i], f["accessionNumber"][i])
            for i in range(len(f["form"]))
            if f["form"][i] == "8-K" and "2.02" in f["items"][i]
        ]
    df = pd.DataFrame(rows, columns=["ticker", "filing_date", "accepted_utc", "accession"])
    df["accepted_et"] = (
        pd.to_datetime(df["accepted_utc"], utc=True).dt.tz_convert("America/New_York").dt.strftime("%Y-%m-%d %H:%M")
    )
    df = df.sort_values(["ticker", "filing_date"])
    df.to_csv(OUT_DIR.parent / "earnings_dates.csv", index=False)
    print(f"earnings_dates: {len(df)} rows")


if __name__ == "__main__":
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    download_prices()
    download_fred()
    download_bcra()
    download_earnings_dates()
