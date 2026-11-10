"""Equity betas for the cost of capital: MELI and peers against the S&P 500.

60 monthly log returns on dividend-adjusted closes, October 2021 to September 2026,
the same window as the beta on the Inputs sheet of excel/meli_dcf.xlsx.
"""

import numpy as np
import pandas as pd
import statsmodels.api as sm

from exposure import OUT, close

START, END = "2021-10-01", "2026-09-30"
GROUPS = {
    "MELI": "MELI",
    "AMZN": "Commerce", "EBAY": "Commerce", "SHOP": "Commerce", "ETSY": "Commerce", "SE": "Commerce",
    "PYPL": "Payments", "DLO": "Payments",
    "NU": "Bank-like fintech", "PAGS": "Bank-like fintech", "STNE": "Bank-like fintech", "INTR": "Bank-like fintech",
}


def monthly(ticker):
    return np.log(close(ticker).resample("ME").last()).diff()


def main():
    market = monthly("SPY")
    rows = []
    for t, group in GROUPS.items():
        r = pd.concat([monthly(t), market], axis=1, keys=["y", "x"], sort=True).loc[START:END].dropna()
        fit = sm.OLS(r.y, sm.add_constant(r.x)).fit()
        rows.append({"ticker": t, "group": group, "months": len(r), "beta": fit.params.x, "se": fit.bse.x, "r2": fit.rsquared})
    df = pd.DataFrame(rows)
    df.to_csv(OUT / "betas.csv", index=False)
    print(df.round(3).to_string(index=False))


if __name__ == "__main__":
    main()
