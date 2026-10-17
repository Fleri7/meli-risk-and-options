"""Save one snapshot of the option chains for MELI and the earnings panel per trading day.

yfinance only serves the current chain, so option history has to be built up
from these daily files: data/options/<TICKER>_YYYY-MM-DD.csv

MELI keeps every expiry. Panel names keep expiries within PANEL_MAX_DAYS and at
least the first PANEL_MIN_EXPIRIES (names with only monthly or quarterly cycles),
so the two expiries after each Oct-Nov 2026 release that the earnings estimators
need are always saved.
"""

import sys
import time
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import yfinance as yf

PANEL = [
    "AMX", "BBD", "PYPL", "EBAY", "ETSY", "YPF", "AMZN", "VALE", "SHOP", "ITUB",
    "CPNG", "SE", "PBR", "NU", "STNE", "PAGS", "XP", "GGAL", "BABA",
]
TICKERS = ["MELI"] + PANEL
PANEL_MAX_DAYS = 75
PANEL_MIN_EXPIRIES = 3
OUT_DIR = Path(__file__).resolve().parents[1] / "data" / "options"
NY = ZoneInfo("America/New_York")


def retry(fn, attempts=4, wait=10):
    for i in range(attempts):
        try:
            return fn()
        except Exception as e:
            if i == attempts - 1:
                raise
            print(f"retry {i + 1}: {e}", file=sys.stderr)
            time.sleep(wait * (i + 1))


def spot_price(tk):
    hist = tk.history(period="1d", interval="1m")
    if hist.empty:
        hist = tk.history(period="5d")
    return float(hist["Close"].iloc[-1])


def snapshot_ticker(ticker, now):
    out = OUT_DIR / f"{ticker}_{now:%Y-%m-%d}.csv"
    if out.exists():
        print(f"{out.name} already saved")
        return

    tk = yf.Ticker(ticker)
    expiries = retry(lambda: tk.options)
    if ticker != "MELI":
        expiries = [
            e for i, e in enumerate(expiries)
            if i < PANEL_MIN_EXPIRIES or (date.fromisoformat(e) - now.date()).days <= PANEL_MAX_DAYS
        ]
    spot = retry(lambda: spot_price(tk))

    frames = []
    for exp in expiries:
        chain = retry(lambda: tk.option_chain(exp))
        for kind, df in (("call", chain.calls), ("put", chain.puts)):
            frames.append(df.assign(expiry=exp, type=kind))
        time.sleep(0.5)

    df = pd.concat(frames, ignore_index=True)
    df.insert(0, "snapshot_time", now.isoformat(timespec="seconds"))
    df.insert(1, "spot", spot)
    df["mid"] = (df["bid"] + df["ask"]) / 2
    df = df.rename(columns={"impliedVolatility": "yf_iv"})

    df.to_csv(out, index=False)
    print(f"saved {len(df)} contracts, {len(expiries)} expiries, spot {spot:.2f} -> {out.name}")


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
