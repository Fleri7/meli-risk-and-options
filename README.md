# MercadoLibre: currency risk and option pricing

**Question.** How exposed is MercadoLibre (MELI) to Latin American currency and macro shocks, and do its options price that risk fairly?

MELI reports in US dollars, but in 2025 52.6% of its revenue was in Brazilian reais, 22.4% in Mexican pesos and 20.6% in Argentine pesos (FY2025 10-K). The gap between the reporting currency and the operating currencies is the core of the analysis.

**Finding.** _To be written once the analysis is complete._

## Hypotheses

- **H1. Exposure in proportion to value.** MELI's stock moves with the Brazilian real and the Mexican peso roughly in proportion to each country's share of MELI's value, as measured by the country DCF.
- **H2. Argentina is priced at the market rate.** MELI's exposure to Argentina shows up against the CCL (market) exchange rate, not the official rate.
- **H3. Options price the currency risk.** MELI's options charge at least as much per unit of risk as those of comparable US companies. The price of risk is implied variance divided by GARCH-forecast variance, compared with a peer group that mirrors MELI's two businesses: commerce (Amazon, eBay, Etsy, Shopify) and fintech (PayPal), weighted by MELI's commerce and fintech revenue split. A lower ratio for MELI means its options under-price the extra risk it carries, which is mainly Latin American currency risk.

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
