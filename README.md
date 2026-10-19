# MercadoLibre: currency risk and option pricing

**Question.** How exposed is MercadoLibre (MELI) to Latin American currency and macro shocks, and do its options price that risk fairly?

MELI reports in US dollars, but in 2025 52.6% of its revenue was in Brazilian reais, 22.4% in Mexican pesos and 20.6% in Argentine pesos (FY2025 10-K). The gap between the reporting currency and the operating currencies is the core of the analysis.

**Finding.** _To be written once the analysis is complete._

## Hypotheses

- **H1. Regional shocks matter more than single-country shocks.** MELI's stock reacts strongly to shocks that hit Latin America as a whole, but much less to shocks confined to one country, because operating in several countries diversifies them away. Tested by splitting the Latin American factors (currencies, sovereign spread, local equity, commodities) into a common regional component and country-specific shocks, with the Nasdaq as a global control.
- **H2. Currency exposure in proportion to value.** MELI's stock moves with the Brazilian real and the Mexican peso in line with each country's share of MELI's value, within the range the country DCF gives once price pass-through and the currency mix of costs and debt are allowed for.
- **H3. Argentina is priced at the market rate.** MELI's exposure to Argentina shows up against the CCL (market) exchange rate rather than the official rate, survives a control for the Argentine stock market, and is largest when capital controls bind.
- **H4. Options price MELI's extra risk.** After removing earnings effects, MELI's options charge at least as much per unit of risk (implied over GARCH-forecast variance) as those of comparable US companies: commerce (Amazon, eBay, Etsy, Shopify) and fintech (PayPal), weighted by MELI's revenue split. A lower price of risk means the extra risk MELI carries, mostly Latin American, is under-priced.

Currency returns are measured as the change in the US-dollar value of the local currency, so a positive beta means MELI gains when the local currency strengthens.

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
| EM sovereign spread proxy (EMB, IEF), commodities (DBC), Bovespa, IPC, Merval | Yahoo Finance via yfinance |
| US yields, SOFR, VIX, VXN, VXAZN, Brazil and Mexico interbank rates | FRED, Federal Reserve Bank of St. Louis |
| Revenue by country | MercadoLibre FY2025 10-K, SEC EDGAR |
| Option chains | Yahoo Finance via yfinance, daily snapshots from Oct 16, 2026 |
