# Mercado Libre: currency risk and option pricing

**Question.** How exposed is Mercado Libre (MELI) to Latin American currency and macro shocks, and do its options price that risk fairly?

MELI reports in US dollars, but in 2025 52.6% of its revenue was in Brazilian reais, 22.4% in Mexican pesos and 20.6% in Argentine pesos (FY2025 10-K). The gap between the reporting currency and the operating currencies is the core of the analysis.

**Finding.** _To be written once the analysis is complete._

## Hypotheses

- **H1. Regional shocks matter more than single-country shocks.** MELI's stock reacts strongly to shocks that hit Latin America as a whole, but much less to shocks confined to one country, because operating in several countries diversifies them away. Tested by splitting the Latin American factors (currencies, sovereign spread, local equity, commodities) into a common regional component and country-specific shocks, with the Nasdaq as a global control.
- **H2. Currency exposure in proportion to value.** MELI's stock moves with the Brazilian real and the Mexican peso in line with each country's share of MELI's value, within the range the country DCF gives once price pass-through and the currency mix of costs and debt are allowed for.
- **H3. Argentina is priced at the market rate.** MELI's exposure to Argentina shows up against the CCL (market) exchange rate rather than the official rate, survives a control for the Argentine stock market, and is largest when capital controls bind.
- **H4. Options price MELI's extra risk.** After removing earnings effects, MELI's options charge at least as much per unit of risk (implied over GARCH-forecast variance) as those of comparable US companies: commerce (Amazon, eBay, Etsy, Shopify) and fintech (PayPal), weighted by MELI's revenue split. A lower price of risk means the extra risk MELI carries, mostly Latin American, is under-priced. A second benchmark of US-listed Latin American fintechs (Nubank, PagSeguro, StoneCo, XP, Inter&Co, dLocal) shows whether MELI is priced like a Latin American company.

Currency returns are measured as the change in the US-dollar value of the local currency, so a positive beta means MELI gains when the local currency strengthens.

## Repository layout

```
data/
  prices/        cached daily prices and FRED series (src/data.py)
  options/       <TICKER>_YYYY-MM-DD.csv, one option-chain snapshot per ticker per trading day
  options_recovered/  Nov 3 peer chains from DoltHub, kept apart from the snapshots
  earnings_dates.csv  8-K Item 2.02 dates for MELI and peers (src/data.py)
  results/       H2 betas and rolling betas (src/exposure.py)
docs/
  MELI Risk and Options - Paper Plan.docx   paper plan: hypotheses, methods, data, timeline
excel/
  meli_dcf.xlsx  country DCF, FX scenarios, options cross-check
src/
  data.py               download and cache prices, FRED and BCRA series, and EDGAR earnings dates
  exposure.py           H2 currency betas for MELI and peers
  snapshot_options.py   daily option-chain snapshot (run by launchd, weekdays 3:30pm ET, retries at 3:45 and 3:55 fill any failed tickers)
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
| Local peers (Magazine Luiza, Casas Bahia, Falabella) | Yahoo Finance via yfinance, converted to US$ |
| EM sovereign spread proxy (EMB, IEF), commodities (DBC), Bovespa, IPC, Merval | Yahoo Finance via yfinance |
| US yields, SOFR, VIX, VXN, VXAZN, Brazil and Mexico interbank rates | FRED, Federal Reserve Bank of St. Louis |
| Revenue by country, debt, FX sensitivity | Mercado Libre FY2025 10-K, 10-Qs and 8-Ks, SEC EDGAR |
| Earnings dates, MELI and peers | 8-K Item 2.02 filings, SEC EDGAR |
| Official peso rate | BCRA API (Com. A 3500), from 2010 |
| Option chains | Yahoo Finance via yfinance, daily snapshots from Oct 16, 2026 |
| Recovered option chains | DoltHub post-no-preference/options (Nov 3, 2026: AMZN, EBAY, ETSY, PYPL) |
