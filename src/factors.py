"""H1 (regional vs country-specific shocks) and H3 (Argentina at the CCL).

Decision rules, fixed before estimation.

H1 is supported if all three hold, rejected if the regional beta is not positive
or a country beta exceeds it at the 5% level, and inconclusive otherwise:
  1. the regional beta is positive (5%, one-sided);
  2. it exceeds each country-specific beta (5%, one-sided);
  3. the regional share of MELI's variance exceeds the three country shares
     combined, with the 90% bootstrap interval above zero.

H3 is supported if all three hold, rejected if the official rate beats the CCL,
and inconclusive otherwise:
  1. with both rates and Argentine equities in US$ in one regression, the CCL beta is
     positive (5%, one-sided) over the two control periods;
  2. the official-rate beta is not positive at that level;
  3. the CCL beta rises with the CCL-official gap (5%, one-sided).
"""

import numpy as np
import pandas as pd
import statsmodels.api as sm

from exposure import OUT, PRICES, close, series

START = "2015-01-01"
WINDOW = 156
LAGS = 4
BOOT = 2000
SEED = 7

COUNTRIES = {"Brazil": ["BRL", "BVSP"], "Mexico": ["MXN", "MXX"], "Argentina": ["ARS_CCL", "ARG_EQ"]}
SERIES = ["BRL", "BVSP", "MXN", "MXX", "ARS_CCL", "ARG_EQ", "SPREAD", "DBC"]
VALUE_SHARES = {"Brazil": 0.425, "Mexico": 0.306, "Argentina": 0.234}

CONTROL_PERIODS = [("2011-10-31", "2015-12-16"), ("2019-09-01", "2025-04-11")]
EVENTS = {
    "Argentina PASO crash (country)": ("2019-08-07", "2019-08-14"),
    "Argentina devaluation (country)": ("2023-12-06", "2023-12-20"),
    "Brazil runoff (country)": ("2026-10-21", "2026-10-28"),
    "March 2020 (regional)": ("2020-02-19", "2020-03-18"),
    "2022 rate shock (regional)": ("2022-01-05", "2022-06-15"),
}


def weekly(s):
    return np.log(s).resample("W-WED").last().diff()


def weekly_returns():
    c = series("CCL")
    official = series("BCRA_USD")
    mxn = series("DEXMXUS")
    # Argentine equities in US$: the four ADRs, since the official Merval series has gaps from 2016 and ends in April 2024
    arg_equity = pd.concat([weekly(close(t, "Close")) for t in ("GGAL", "YPF", "PAM", "BMA")], axis=1).mean(axis=1)
    r = pd.DataFrame({
        "MELI": weekly(close("MELI")), "QQQ": weekly(close("QQQ")),
        "BRL": -weekly(series("PTAX")), "MXN": -weekly(mxn),
        "ARS_CCL": -weekly(c), "ARS_OFF": -weekly(official),
        "BVSP": weekly(series("IBOV")), "MXX": weekly(close("EWW", "Close")) + weekly(mxn),
        "ARG_EQ": arg_equity,
        "SPREAD": weekly(close("EMB")) - weekly(close("IEF")), "DBC": weekly(close("DBC")),
    })
    r["GAP"] = np.log(c.resample("W-WED").last() / official.resample("W-WED").last())
    return r


def rolling_factors(r):
    """Past-only regional factor and country shocks: Nasdaq out, then principal components."""
    x = r[SERIES + ["QQQ"]].dropna()
    out, stats = {}, {}
    for i in range(WINDOW, len(x)):
        win, now = x.iloc[i - WINDOW:i], x.iloc[i]
        q = win["QQQ"]
        b = win[SERIES].apply(lambda s: np.cov(s, q)[0, 1] / q.var())
        a = win[SERIES].mean() - b * q.mean()
        res_win = win[SERIES] - a - np.outer(q, b)
        mu, sd = res_win.mean(), res_win.std()
        z_win = (res_win - mu) / sd
        z_now = (now[SERIES] - a - b * now["QQQ"] - mu) / sd
        vals, vecs = np.linalg.eigh(np.corrcoef(z_win.T))
        load = pd.Series(vecs[:, -1], index=SERIES)
        load *= np.sign(load["BRL"])
        f_win, f_now = z_win @ load, z_now @ load
        lam = z_win.apply(lambda s: np.cov(s, f_win)[0, 1] / f_win.var())
        resid = z_now - lam * f_now
        row = {"REGIONAL": f_now}
        row.update({c: resid[cols].mean() for c, cols in COUNTRIES.items()})
        row["EQUAL"] = (z_now * np.sign(load)).mean()
        out[x.index[i]] = row
        stats[x.index[i]] = {"pc1_share": vals[-1] / vals.sum(), **(lam**2 * f_win.var()).to_dict()}
    return pd.DataFrame(out).T, pd.DataFrame(stats).T


def standardised(d, cols):
    return (d[cols] - d[cols].mean()) / d[cols].std()


def hac(y, x):
    return sm.OLS(y, sm.add_constant(x)).fit(cov_type="HAC", cov_kwds={"maxlags": LAGS})


def contributions(y, x):
    b = np.linalg.lstsq(np.c_[np.ones(len(x)), x.values], y.values, rcond=None)[0][1:]
    return pd.Series([b[j] * np.cov(x.iloc[:, j], y)[0, 1] / y.var() for j in range(x.shape[1])], index=x.columns)


def block_indices(n, rng, mean_block=8):
    idx = np.empty(n, dtype=int)
    idx[0] = rng.integers(n)
    for i in range(1, n):
        idx[i] = rng.integers(n) if rng.random() < 1 / mean_block else (idx[i - 1] + 1) % n
    return idx


def one_sided(res, expr):
    t = res.t_test(expr)
    return float(np.squeeze(t.effect)), float(np.squeeze(t.tvalue)), float(np.squeeze(t.pvalue)) / 2


def h1(r, f):
    cols = ["REGIONAL", "Brazil", "Mexico", "Argentina", "QQQ"]
    d = f.join(r[["MELI", "QQQ"]]).dropna().loc[START:]
    x, y = standardised(d, cols), d["MELI"]
    res = hac(y, x)
    sd = y.std()
    table = pd.DataFrame({"beta_std": res.params[cols] / sd, "t": res.tvalues[cols], "p_two_sided": res.pvalues[cols]})
    table["var_share"] = contributions(y, x)

    tests = [("regional > 0", *one_sided(res, "REGIONAL = 0"))]
    tests += [(f"regional > {c}", *one_sided(res, f"REGIONAL - {c} = 0")) for c in COUNTRIES]
    tests = pd.DataFrame(tests, columns=["test", "effect", "t", "p_one_sided"])
    tests["effect"] /= sd

    rng = np.random.default_rng(SEED)
    boot = []
    for _ in range(BOOT):
        i = block_indices(len(d), rng)
        c = contributions(y.iloc[i], x.iloc[i])
        boot.append({"regional": c["REGIONAL"], "countries": c[list(COUNTRIES)].sum(),
                     "gap": c["REGIONAL"] - c[list(COUNTRIES)].sum()})
    boot = pd.DataFrame(boot).quantile([0.05, 0.95]).T

    sub = {}
    for name, (a, b) in {"2015-19": ("2015", "2019"), "2020-26": ("2020", "2026"), "last 5y": ("2021-11", "2026")}.items():
        dd = d.loc[a:b]
        xx = standardised(dd, cols)
        sub[name] = pd.concat([hac(dd["MELI"], xx).params[cols] / dd["MELI"].std(),
                               contributions(dd["MELI"], xx).rename(lambda c: c + " var")])
    alt = ["EQUAL", "Brazil", "Mexico", "Argentina", "QQQ"]
    xa = standardised(d, alt)
    sub["equal-weighted factor"] = pd.concat([hac(y, xa).params[alt] / sd, contributions(y, xa).rename(lambda c: c + " var")])

    ev = []
    fitted = res.predict(sm.add_constant(x)) - res.params["const"]
    regional_part = res.params["REGIONAL"] * x["REGIONAL"]
    for name, (a, b) in EVENTS.items():
        w = slice(pd.Timestamp(a) + pd.Timedelta(days=1), b)
        ev.append({"event": name, "weeks": len(y.loc[w]), "actual": y.loc[w].sum(), "model": fitted.loc[w].sum(),
                   "regional_part": regional_part.loc[w].sum()})
    return table, tests, boot, pd.DataFrame(sub), pd.DataFrame(ev), res


def h3(r):
    base = ["QQQ", "BRL", "MXN"]
    d = r[["MELI", "ARS_CCL", "ARS_OFF", "ARG_EQ", "GAP"] + base].dropna()
    d = d.assign(GAP_LAG=d["GAP"].shift(1)).dropna()
    control = pd.Series(False, index=d.index)
    for a, b in CONTROL_PERIODS:
        control.loc[a:b] = True
    specs = {
        "official only": ["ARS_OFF", "ARG_EQ"], "CCL only": ["ARS_CCL", "ARG_EQ"],
        "both": ["ARS_CCL", "ARS_OFF", "ARG_EQ"], "both, no equity control": ["ARS_CCL", "ARS_OFF"],
    }
    samples = {
        "both control periods": d[control], "2013-15": d.loc[slice(*CONTROL_PERIODS[0])],
        "2019-25": d.loc[slice(*CONTROL_PERIODS[1])], "no controls": d[~control], "all": d,
    }
    rows = []
    for sname, s in samples.items():
        for name, c in specs.items():
            res = hac(s["MELI"], s[base + c])
            row = {"sample": sname, "spec": name, "n": len(s), "r2": res.rsquared}
            for v in ("ARS_CCL", "ARS_OFF", "ARG_EQ"):
                if v in c:
                    row[v] = res.params[v]
                    row[v + "_t"] = res.tvalues[v]
            rows.append(row)
    s = d.assign(GAP_C=d["GAP_LAG"] - d["GAP_LAG"].mean())
    s = s.assign(CCL_X_GAP=s["ARS_CCL"] * s["GAP_C"], CCL_X_CONTROL=s["ARS_CCL"] * control.astype(float))
    inter = hac(s["MELI"], s[base + ["ARS_CCL", "CCL_X_GAP", "GAP_C", "ARG_EQ"]])
    dummy = hac(s["MELI"], s[base + ["ARS_CCL", "CCL_X_CONTROL", "ARG_EQ"]])
    gap = d["GAP"].groupby(control).describe()[["mean", "max"]]
    return pd.DataFrame(rows), inter, dummy, gap, d["GAP"]


def h1_robustness(r, f):
    """How much the small Latin American share depends on how the factor is built."""
    d = f.join(r[["MELI", "QQQ"] + SERIES]).dropna().loc[START:]
    z = standardised(d, SERIES)
    vals, vecs = np.linalg.eigh(np.corrcoef(z.T))
    load = pd.Series(vecs[:, -1], index=SERIES)
    raw = z @ (load * np.sign(load["BRL"]))
    y = d["MELI"]
    rows = {}
    for name, x in {
        "past-only factor, Nasdaq out": standardised(d, ["REGIONAL", "Brazil", "Mexico", "Argentina", "QQQ"]),
        "full-sample factor, Nasdaq kept in": standardised(d.assign(REGIONAL=raw), ["REGIONAL", "Brazil", "Mexico", "Argentina", "QQQ"]),
        "all eight series directly": standardised(d, SERIES + ["QQQ"]),
    }.items():
        res = hac(y, x)
        c = contributions(y, x)
        rows[name] = {"r2": res.rsquared, "nasdaq": c["QQQ"], "latin_american": c.drop("QQQ").sum()}
    no_nasdaq = hac(y, standardised(d, ["REGIONAL", "Brazil", "Mexico", "Argentina"]))
    rows["no Nasdaq in the regression"] = {"r2": no_nasdaq.rsquared, "nasdaq": 0.0, "latin_american": no_nasdaq.rsquared}
    q_only = hac(y, standardised(d, ["QQQ"]))
    rows["Nasdaq alone"] = {"r2": q_only.rsquared, "nasdaq": q_only.rsquared, "latin_american": 0.0}
    return pd.DataFrame(rows).T


def monthly_model(f, r):
    """Adds local rates and inflation, split into a regional part and country parts."""
    cpi = {c: pd.read_csv(PRICES / f"CPI_{c}.csv", index_col=0, parse_dates=True)["cpi"] for c in ("BR", "MX", "AR")}
    rate = {c: pd.read_csv(PRICES / f"IRSTCI01{c}M156N.csv", index_col=0, parse_dates=True).iloc[:, 0] for c in ("BR", "MX")}
    macro = pd.DataFrame({
        "RATE_BR": rate["BR"].diff(), "RATE_MX": rate["MX"].diff(),
        "INF_BR": np.log(cpi["BR"]).diff().diff(), "INF_MX": np.log(cpi["MX"]).diff().diff(),
        "INF_AR": np.log(cpi["AR"]).diff().diff(),
    }).dropna()
    macro.index = macro.index + pd.offsets.MonthEnd(0)
    z = standardised(macro, list(macro.columns))
    vals, vecs = np.linalg.eigh(np.corrcoef(z.T))
    load = pd.Series(vecs[:, -1], index=macro.columns)
    pc = z @ load
    resid = z - np.outer(pc, z.apply(lambda s: np.cov(s, pc)[0, 1] / pc.var()))
    macro_f = pd.DataFrame({"MACRO_REGIONAL": pc, "MACRO_BR": resid[["RATE_BR", "INF_BR"]].mean(axis=1),
                            "MACRO_MX": resid[["RATE_MX", "INF_MX"]].mean(axis=1), "MACRO_AR": resid["INF_AR"]})
    m = f[["REGIONAL", "Brazil", "Mexico", "Argentina"]].resample("ME").sum()
    m = m.join(r[["MELI", "QQQ"]].resample("ME").sum()).join(macro_f).dropna()
    base = ["REGIONAL", "Brazil", "Mexico", "Argentina", "QQQ"]
    x = standardised(m, base + list(macro_f.columns))
    small = sm.OLS(m["MELI"], sm.add_constant(x[base])).fit()
    full = sm.OLS(m["MELI"], sm.add_constant(x)).fit(cov_type="HAC", cov_kwds={"maxlags": 3})
    wald = full.wald_test(" = ".join(macro_f.columns) + " = 0", use_f=True, scalar=True)
    return {"months": len(m), "start": m.index[0].date(), "end": m.index[-1].date(), "r2_base": small.rsquared,
            "r2_macro": full.rsquared, "wald_p": float(wald.pvalue),
            "macro_t": full.tvalues[list(macro_f.columns)].round(2).to_dict(), "pc1_share": vals[-1] / vals.sum()}


def h3_diagnostics(r):
    """Does one devaluation week drive the official-rate beta, and does a daily test change the answer?"""
    base = ["QQQ", "BRL", "MXN"]
    d = r[["MELI", "ARS_CCL", "ARS_OFF", "ARG_EQ"] + base].dropna()
    control = pd.Series(False, index=d.index)
    for a, b in CONTROL_PERIODS:
        control.loc[a:b] = True
    s = d[control]
    big = s["ARS_OFF"].abs().sort_values(ascending=False)
    rows = []
    for k in (0, 1, 3, 5):
        t = s.drop(big.index[:k])
        res = hac(t["MELI"], t[base + ["ARS_CCL", "ARS_OFF", "ARG_EQ"]])
        rows.append({"dropped_weeks": k, "official": res.params["ARS_OFF"], "official_t": res.tvalues["ARS_OFF"],
                     "ccl": res.params["ARS_CCL"], "ccl_t": res.tvalues["ARS_CCL"]})
    top = pd.DataFrame({"official": s.loc[big.index[:5], "ARS_OFF"], "ccl": s.loc[big.index[:5], "ARS_CCL"],
                        "meli": s.loc[big.index[:5], "MELI"], "qqq": s.loc[big.index[:5], "QQQ"]})

    c = series("CCL")
    off = series("BCRA_USD")
    daily = pd.DataFrame({
        "MELI": np.log(close("MELI")).diff(), "QQQ": np.log(close("QQQ")).diff(),
        "BRL": -np.log(series("PTAX")).diff(), "MXN": -np.log(series("DEXMXUS")).diff(),
        "ARS_CCL": -np.log(c).diff(), "ARS_OFF": -np.log(off).diff(),
    }).dropna()
    mask = pd.Series(False, index=daily.index)
    for a, b in CONTROL_PERIODS:
        mask.loc[a:b] = True
    out = []
    for name, t in {"daily, control periods": daily[mask], "daily, no controls": daily[~mask]}.items():
        res = sm.OLS(t["MELI"], sm.add_constant(t[base + ["ARS_CCL", "ARS_OFF"]])).fit(cov_type="HAC", cov_kwds={"maxlags": 5})
        out.append({"sample": name, "n": len(t), "ccl": res.params["ARS_CCL"], "ccl_t": res.tvalues["ARS_CCL"],
                    "official": res.params["ARS_OFF"], "official_t": res.tvalues["ARS_OFF"]})
    return pd.DataFrame(rows), top, pd.DataFrame(out)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    r = weekly_returns()
    f, stats = rolling_factors(r)
    table, tests, boot, sub, ev, _ = h1(r, f)
    h3_table, inter, dummy, gap, gap_series = h3(r)
    table.to_csv(OUT / "h1_main.csv")
    tests.to_csv(OUT / "h1_tests.csv", index=False)
    boot.to_csv(OUT / "h1_bootstrap.csv")
    sub.to_csv(OUT / "h1_subsamples.csv")
    ev.to_csv(OUT / "h1_events.csv", index=False)
    stats.to_csv(OUT / "h1_regional_share.csv", index_label="date")
    f.to_csv(OUT / "h1_factors.csv", index_label="date")
    h3_table.to_csv(OUT / "h3_regressions.csv", index=False)
    gap_series.to_csv(OUT / "h3_gap.csv")

    pd.set_option("display.width", 220, "display.max_columns", 30)
    print(f"weeks {len(f.loc[START:])}, {f.loc[START:].index[0].date()} to {f.index[-1].date()}")
    print(table.round(3), tests.round(3), boot.round(3), sub.round(3), ev.round(3), sep="\n\n")
    print("\nregional share by year\n", stats.loc[START:].groupby(lambda t: t.year).mean().round(2).to_string())
    print("\n", h3_table.round(3).to_string())
    print("\ninteraction\n", pd.DataFrame({"b": inter.params, "t": inter.tvalues}).round(3).to_string())
    print("\ncontrol dummy\n", pd.DataFrame({"b": dummy.params, "t": dummy.tvalues}).round(3).to_string())
    print("\ngap\n", gap.round(3).to_string())

    rob = h1_robustness(r, f)
    rob.to_csv(OUT / "h1_robustness.csv")
    print("\nH1 robustness\n", rob.round(3).to_string())
    print("\nmonthly model\n", monthly_model(f, r))
    drop, top, daily = h3_diagnostics(r)
    drop.to_csv(OUT / "h3_leverage.csv", index=False)
    daily.to_csv(OUT / "h3_daily.csv", index=False)
    print("\nH3 leverage\n", drop.round(3).to_string(), "\n", top.round(3).to_string(), "\n", daily.round(3).to_string())


if __name__ == "__main__":
    main()
