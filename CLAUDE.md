# Project rules

## Data sources
- Never use Yahoo Finance or yfinance. Use official sources: SEC EDGAR for filings, exchanges for prices (Cboe, Nasdaq, B3), central banks for exchange rates (BCRA, Banco Central do Brasil, Federal Reserve), statistical agencies for inflation.
- The only exception is the archived option snapshots from Oct 16 to Nov 4, 2026 in `data/options/`. Keep them, but collect nothing new from Yahoo.
- Where no official series exists, say so in the plan and README. The CCL comes from Ámbito for that reason.
