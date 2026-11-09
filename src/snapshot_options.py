"""Save one snapshot of the option chains for MELI and the earnings panel per trading day.

Nasdaq's delayed quotes (about 15 minutes) only show the current chain, so option
history has to be built up from these daily files: data/options/<TICKER>_YYYY-MM-DD.csv
Files saved before Nov 5, 2026 came from Yahoo and have a yf_iv column.

MELI keeps every expiry. Panel names keep expiries within PANEL_MAX_DAYS and at
least the first PANEL_MIN_EXPIRIES (names with only monthly or quarterly cycles),
so the two expiries after each Oct-Nov 2026 release that the earnings estimators
need are always saved.
"""

import re
import sys
import time
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import requests

PANEL = [
    "AMX", "BBD", "PYPL", "EBAY", "ETSY", "YPF", "AMZN", "VALE", "SHOP", "ITUB",
    "CPNG", "SE", "PBR", "NU", "STNE", "PAGS", "XP", "GGAL", "BABA", "INTR", "DLO",
]
TICKERS = ["MELI"] + PANEL
PANEL_MAX_DAYS = 75
PANEL_MIN_EXPIRIES = 3
OUT_DIR = Path(__file__).resolve().parents[1] / "data" / "options"
NY = ZoneInfo("America/New_York")
URL = "https://api.nasdaq.com/api/quote/{}/option-chain"
PARAMS = {"assetclass": "stocks", "limit": 10000, "fromdate": "all", "todate": "undefined",
          "excode": "oprac", "callput": "callput", "money": "all", "type": "all"}
HEADERS = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}


def retry(fn, attempts=4, wait=10):
    for i in range(attempts):
        try:
            return fn()
        except Exception as e:
            if i == attempts - 1:
                raise
            print(f"retry {i + 1}: {e}", file=sys.stderr)
            time.sleep(wait * (i + 1))


def fetch(ticker):
    r = requests.get(URL.format(ticker), params=PARAMS, headers=HEADERS, timeout=60)
    r.raise_for_status()
    return r.json()["data"]


def number(x):
    return float(x.replace(",", "")) if x and x != "--" else None


def contracts(rows):
    out, expiry = [], None
    for x in rows:
        if x["expirygroup"]:
            expiry = datetime.strptime(x["expirygroup"], "%B %d, %Y").date().isoformat()
            continue
        for prefix, kind in (("c", "call"), ("p", "put")):
            out.append({
                "expiry": expiry, "type": kind, "strike": number(x["strike"]),
                "lastPrice": number(x[f"{prefix}_Last"]), "bid": number(x[f"{prefix}_Bid"]), "ask": number(x[f"{prefix}_Ask"]),
                "volume": number(x[f"{prefix}_Volume"]), "openInterest": number(x[f"{prefix}_Openinterest"]),
            })
    return pd.DataFrame(out)


def snapshot_ticker(ticker, now):
    out = OUT_DIR / f"{ticker}_{now:%Y-%m-%d}.csv"
    if out.exists():
        print(f"{out.name} already saved")
        return

    chain = retry(lambda: fetch(ticker))
    df = contracts(chain["table"]["rows"])
    if ticker != "MELI":
        expiries = sorted(df["expiry"].unique())
        keep = [
            e for i, e in enumerate(expiries)
            if i < PANEL_MIN_EXPIRIES or (date.fromisoformat(e) - now.date()).days <= PANEL_MAX_DAYS
        ]
        df = df[df["expiry"].isin(keep)]

    spot = float(re.search(r"\$([\d,.]+)", chain["lastTrade"]).group(1).replace(",", ""))
    df.insert(0, "snapshot_time", datetime.now(NY).isoformat(timespec="seconds"))
    df.insert(1, "spot", spot)
    df["mid"] = (df["bid"] + df["ask"]) / 2

    df.to_csv(out, index=False)
    print(f"saved {len(df)} contracts, {df['expiry'].nunique()} expiries, spot {spot:.2f} -> {out.name}")
    time.sleep(1)


def snapshot():
    now = datetime.now(NY)
    if now.weekday() >= 5:
        print("weekend, skipping")
        return
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    failed = []
    for ticker in TICKERS:
        try:
            snapshot_ticker(ticker, now)
        except Exception as e:
            print(f"{ticker} failed: {e}", file=sys.stderr)
            failed.append(ticker)
    if failed:
        print(f"failed: {', '.join(failed)}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    snapshot()
