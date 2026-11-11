# Mercado Libre: Pricing Latin American Risk in the Stock and Its Options

*Independent research project by Fernando Leri. In progress (November 2026).*

**Question.** How exposed is Mercado Libre (MELI) to Latin American currency and macro shocks, and do its stock price and options price that risk?

MELI reports in US dollars and trades on the Nasdaq, but in 2025 52.6% of its revenue was in Brazilian reais, 22.4% in Mexican pesos and 20.6% in Argentine pesos (FY2025 10-K). The project measures how much of that risk shows up in the stock, in its valuation and in its options.

## Approach

1. **Equity exposure.** Weekly regressions of MELI's returns on a regional Latin American factor, country-specific shocks and the Nasdaq, with Newey-West errors and a block bootstrap (H1); currency betas against the exposure the valuation implies (H2); Argentina's official vs parallel (CCL) exchange rate (H3).
2. **Valuation.** A DCF for 2026E to 2036E built from the filings, valuing commerce and the Mercado Pago loan book together; a WACC with the beta checked against peers and the cost of debt from Fitch default data; peer multiples; sensitivity grids and break-evens showing how much country risk today's price assumes.
3. **Options.** A daily snapshot of option chains on MELI and 21 peers since October 2026, testing whether MELI's options charge as much per unit of risk as those of US peers (H4).

## Status

| Part | Status |
|---|---|
| H1, regional vs country shocks | First estimate: inconclusive |
| H2, currency exposure vs value | First estimate: inconclusive; rerun with the Q3 2026 10-Q |
| H3, Argentina at the market rate | First estimate: rejected |
| Valuation | Model built; recommendation waits for H2 and H3 |
| H4, options | Collecting data; test from December 2026 |

Early valuation result, still being tested: with the full Damodaran country risk premium the DCF gives about $860 a share against a $1,740 price. The price is consistent with a WACC of about 10.3%, which leaves room for very little Latin American country premium.

## Hypotheses

- **H1. Regional shocks matter more than single-country shocks.** Operating in several countries should diversify away shocks confined to one of them, but not shocks that hit the region as a whole.
- **H2. Currency exposure in proportion to value.** MELI's stock moves with the real and the peso within the range the country DCF gives once price pass-through and the currency mix of costs and debt are allowed for.
- **H3. Argentina is priced at the market rate.** Exposure shows up against the CCL rather than the official rate, survives a control for Argentine equities, and is largest when capital controls bind.
- **H4. Options price MELI's extra risk.** After removing earnings effects, MELI's options charge at least as much per unit of risk (implied over GARCH-forecast variance) as a revenue-weighted basket of US commerce and payments peers.

Currency returns are the change in the US-dollar value of the local currency, so a positive beta means MELI gains when the local currency strengthens.

## Repository

```
data/
  prices/             cached daily prices, exchange rates and FRED series (src/data.py)
  options/            one option-chain snapshot per ticker per trading day
  options_recovered/  Nov 3, 2026 peer chains from DoltHub, kept apart from the snapshots
  earnings_dates.csv  8-K Item 2.02 dates for MELI and peers
  results/            H1, H2 and H3 estimates and equity betas
docs/
  MELI Risk and Options - Paper Plan.docx   paper plan: sections, methods, data, timeline
excel/
  meli_dcf.xlsx       historicals, WACC, DCF, multiples, sensitivity and break-evens; country DCF, FX scenarios, options cross-check
src/
  data.py               downloads and caches prices, exchange rates and EDGAR earnings dates
  factors.py            H1 regional and country factors; H3 official vs CCL
  exposure.py           H2 currency betas for MELI and peers
  betas.py              equity betas vs the S&P 500 for the WACC
  snapshot_options.py   daily option-chain snapshot, run each weekday at 3:30pm ET
```

Notebooks and figures will be added as each part is written up.

## How to run

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python src/data.py
```

`src/data.py` caches every series to `data/prices/`, so the analysis scripts run offline. Option chains cannot be downloaded after the fact, so `data/options/` only grows through the daily snapshot job.

## Data

Official and exchange sources only. Yahoo Finance is not used; the one exception is option snapshots from Oct 16 to Nov 4, 2026, archived before the switch to Nasdaq. Licensed Fitch reports used for the cost of debt are cited but not included.

| Data | Source |
|---|---|
| US-listed stocks and ETFs | Cboe daily closes; dividends from Nasdaq |
| Brazilian real | Banco Central do Brasil, PTAX |
| Mexican peso | Federal Reserve H.10 via FRED |
| Argentine peso | BCRA (official rate); Ámbito (CCL, since no official body publishes it) |
| Brazilian equities | B3 (Ibovespa, COTAHIST quotes for Magazine Luiza and Casas Bahia) |
| Mexican and Argentine equities | EWW in pesos; average of GGAL, YPF, PAM and BMA in US$ |
| Rates and volatility indices | FRED (US yields, SOFR, VIX, VXN, VXAZN, Brazil and Mexico interbank rates) |
| Inflation | IBGE, INDEC, FRED (OECD) |
| MELI and peer financials | 10-K, 10-Q and 20-F filings, SEC EDGAR |
| Earnings dates | 8-K Item 2.02 filings, SEC EDGAR |
| Cost of capital | Damodaran (ERP and country risk premiums); ICE BofA BBB EM corporate yield via FRED; Fitch rating action (Oct 8, 2026) and default study (1990-2025) |
| Option chains | Nasdaq daily snapshots from Nov 5, 2026; archived Yahoo snapshots Oct 16 to Nov 4; DoltHub for Nov 3 peer chains |
