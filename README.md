# MercadoLibre: currency risk and option pricing

**Question.** How exposed is MercadoLibre (MELI) to Latin American currency and macro shocks, and do its options price that risk fairly?

MELI reports in US dollars, but in 2025 52.6% of its revenue was in Brazilian reais, 22.4% in Mexican pesos and 20.6% in Argentine pesos (FY2025 10-K). The gap between the reporting currency and the operating currencies is the core of the analysis.

**Finding.** _To be written once the analysis is complete._

## Hypotheses

- **H1.** Brazilian real moves explain more of MELI's returns than Argentine peso moves, after controlling for the Nasdaq.
- **H2.** Options overprice earnings-day moves on average (panel of 20 stocks reporting Oct to Nov 2026, MELI as the case study).
- **H3.** MELI's implied volatility sits above its GARCH volatility, most of all on downside strikes.

## Repository layout

```
data/
  prices/        cached daily prices and FRED series (src/data.py)
  options/       <TICKER>_YYYY-MM-DD.csv, one option-chain snapshot per ticker per trading day
excel/
  meli_dcf.xlsx  country DCF, FX scenarios, options cross-check
src/
  data.py               download and cache prices and FRED series
  snapshot_options.py   daily option-chain snapshot (run by launchd, weekdays 3:30pm ET)
notebooks/              one notebook per step (added as the analysis is built)
figures/
```

## How to run

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python src/data.py
```

`src/data.py` caches every series to `data/prices/` so the notebooks run offline. Option chains cannot be downloaded after the fact, so `data/options/` only grows through the daily snapshot job.

## Data

| Data | Source |
|---|---|
| Stock, ETF and FX prices | Yahoo Finance via yfinance |
| US yields, SOFR, VIX, VXN, VXAZN | FRED, Federal Reserve Bank of St. Louis |
| Revenue by country | MercadoLibre FY2025 10-K, SEC EDGAR |
| Option chains | Yahoo Finance via yfinance, daily snapshots from Oct 16, 2026 |
