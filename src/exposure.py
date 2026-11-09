"""H2: currency betas for MELI and peers, compared with the DCF exposure ranges.

Currency returns are the change in the US$ value of the local currency, so a
positive beta means the stock gains when the local currency strengthens.
"""

from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm

PRICES = Path(__file__).resolve().parents[1] / "data" / "prices"
OUT = Path(__file__).resolve().parents[1] / "data" / "results"

PRIMARY_START = "2021-11-01"  # five years, matching the equity beta window and today's business mix
FULL_START = "2015-01-01"
FACTORS = ["BRL", "MXN", "ARS_CCL"]
LAGS = {"D": 5, "W": 4, "M": 3}

# US$-listed names, and locally listed names converted to US$ at the local rate
PEERS_USD = ["NU", "STNE", "PAGS", "INTR", "DLO", "SE", "AMZN", "EBAY", "ETSY", "SHOP", "PYPL"]
PEERS_LOCAL = ["MGLU3", "BHIA3"]


def close(ticker, column="Adj Close"):
    return pd.read_csv(PRICES / f"{ticker}.csv", index_col=0, parse_dates=True)[column].rename(ticker)


def series(name):
    return pd.read_csv(PRICES / f"{name}.csv", index_col=0, parse_dates=True).iloc[:, 0].dropna().rename(name)


def levels():
    px = pd.DataFrame({
        "MELI": close("MELI"), "QQQ": close("QQQ"), "SPY": close("SPY"), "EEM": close("EEM"),
        "BRL": 1 / series("PTAX"), "MXN": 1 / series("DEXMXUS"), "ARS_CCL": 1 / series("CCL"), "ARS_OFF": 1 / series("BCRA_USD"),
    })
    for t in PEERS_USD:
        px[t] = close(t)
    for t in PEERS_LOCAL:
        px[t] = series(t) / series("PTAX").reindex(series(t).index).ffill()
    return px.sort_index().ffill(limit=3)


def returns(px, freq):
    if freq == "D":
        sampled = px
    elif freq == "W":
        sampled = px.resample("W-WED").last()
    else:
        sampled = px.resample("ME").last()
    return np.log(sampled).diff()


def fit(r, y, market, start, freq):
    cols = ([market] if market else []) + FACTORS
    d = r.loc[start:, [y] + cols].dropna()
    res = sm.OLS(d[y], sm.add_constant(d[cols])).fit(cov_type="HAC", cov_kwds={"maxlags": LAGS[freq]})
    return res, len(d)


def rows(r, y, market, start, freq, label):
    res, n = fit(r, y, market, start, freq)
    ci = res.conf_int(alpha=0.10)
    return [
        {"stock": y, "spec": label, "freq": freq, "market": market or "none", "start": start, "n": n, "factor": f,
         "beta": res.params[f], "se": res.bse[f], "ci90_low": ci.loc[f, 0], "ci90_high": ci.loc[f, 1],
         "r2": res.rsquared}
        for f in FACTORS
    ]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    px = levels()
    r = {f: returns(px, f) for f in "DWM"}

    out = rows(r["W"], "MELI", "QQQ", PRIMARY_START, "W", "primary")
    out += rows(r["W"], "MELI", None, PRIMARY_START, "W", "total")
    out += rows(r["W"], "MELI", "QQQ", FULL_START, "W", "full sample")
    for m in ("SPY", "EEM"):
        out += rows(r["W"], "MELI", m, PRIMARY_START, "W", f"market {m}")
    for f in "DM":
        out += rows(r[f], "MELI", "QQQ", PRIMARY_START, f, f"horizon {f}")
    for t in PEERS_USD + list(PEERS_LOCAL):
        out += rows(r["W"], t, "QQQ", PRIMARY_START, "W", "peer")
    df = pd.DataFrame(out)
    df.to_csv(OUT / "h2_betas.csv", index=False)

    w = r["W"][["MELI", "QQQ"] + FACTORS].dropna()
    roll = {}
    for end in range(52, len(w)):
        d = w.iloc[end - 52:end]
        roll[d.index[-1]] = sm.OLS(d["MELI"], sm.add_constant(d[["QQQ"] + FACTORS])).fit().params[FACTORS]
    pd.DataFrame(roll).T.to_csv(OUT / "h2_rolling_betas.csv", index_label="date")
    return df


if __name__ == "__main__":
    pd.set_option("display.width", 200)
    print(main().round(3).to_string())
