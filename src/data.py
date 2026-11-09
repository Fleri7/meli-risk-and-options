"""Download and cache daily prices and FRED series to data/prices/.

Every series is saved as one CSV so the notebooks run offline and a broken
API call never changes a result after the fact.
"""

import base64
import io
import json
import sys
import time
import zipfile
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import requests

START = "2010-01-01"
OUT_DIR = Path(__file__).resolve().parents[1] / "data" / "prices"

TICKERS = [
    "MELI", "QQQ", "SPY", "EEM", "EWW",
    "NU", "STNE", "PAGS", "SE", "AMZN",
    "GGAL", "YPF", "PAM", "BMA",
    "EMB", "IEF", "DBC",
    "EBAY", "ETSY", "SHOP", "PYPL", "INTR", "DLO",
]
ETFS = {"QQQ", "SPY", "EEM", "EWW", "EMB", "IEF", "DBC"}
B3_STOCKS = {"MGLU3": "MGLU3", "VIIA3": "BHIA3", "BHIA3": "BHIA3"}  # Via became Casas Bahia in Sep 2023
B3_FIRST_YEAR = 2021
B3_SPLITS = {"MGLU3": {"2024-05-27": 10}, "BHIA3": {"2023-12-15": 25}}  # reverse splits, unadjusted in COTAHIST
BROWSER = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}

EARNINGS_CIKS = {
    "MELI": 1099590, "AMZN": 1018724, "EBAY": 1065088, "ETSY": 1370637, "SHOP": 1594805, "PYPL": 1633917,
}

FRED_SERIES = [
    "DGS10", "DGS1MO", "SOFR", "VIXCLS", "VXNCLS", "VXAZNCLS", "DEXBZUS", "DEXMXUS",
    "IRSTCI01BRM156N", "IRSTCI01MXM156N",
]


def get(url, **kwargs):
    for i in range(4):
        try:
            r = requests.get(url, headers=BROWSER, timeout=120, **kwargs)
            r.raise_for_status()
            return r
        except requests.RequestException as e:
            if i == 3:
                raise
            print(f"retry {i + 1}: {e}", file=sys.stderr)
            time.sleep(5 * (i + 1))


def dividends(ticker):
    kind = "etf" if ticker in ETFS else "stocks"
    rows = get(f"https://api.nasdaq.com/api/quote/{ticker}/dividends", params={"assetclass": kind}).json()["data"]["dividends"]["rows"] or []
    cash = [(pd.Timestamp(d["exOrEffDate"]), float(d["amount"].replace("$", "").replace(",", ""))) for d in rows
            if d["type"] == "Cash" and d["exOrEffDate"] != "N/A"]
    return pd.Series(dict(cash), dtype=float).sort_index()


def adjusted(close, cash):
    """Dividend-adjusted close: every price before an ex-date is scaled by 1 - dividend / prior close."""
    factor = pd.Series(1.0, index=close.index)
    for ex, amount in cash.items():
        before = close.index[close.index < ex]
        if ex <= close.index[-1] and len(before):
            factor[before] *= 1 - amount / close[before[-1]]
    return close * factor


def download_prices():
    """Exchange closes from Cboe, dividends from Nasdaq; the latest row is always a finished session."""
    today = pd.Timestamp(datetime.now(ZoneInfo("America/New_York")).date())
    for t in TICKERS:
        df = pd.DataFrame(get(f"https://cdn.cboe.com/api/global/delayed_quotes/charts/historical/{t}.json").json()["data"])
        df["date"] = pd.to_datetime(df["date"])
        df = df[(df["date"] >= START) & (df["date"] < today) & (df["close"] > 0)].drop_duplicates("date", keep="last").set_index("date")
        df = df.rename(columns=str.title)
        df["Adj Close"] = adjusted(df["Close"], dividends(t))
        df[["Open", "High", "Low", "Close", "Adj Close", "Volume"]].to_csv(OUT_DIR / f"{t}.csv")
        print(f"{t}: {len(df)} rows")


def download_fred():
    for s in FRED_SERIES:
        r = requests.get(f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={s}", timeout=60)
        r.raise_for_status()
        df = pd.read_csv(io.StringIO(r.text))
        df.columns = ["date", s]
        df = df[df["date"] >= START]
        df.to_csv(OUT_DIR / f"{s}.csv", index=False)
        print(f"{s}: {len(df)} rows")


def download_bcra():
    """Official wholesale peso rate (Com. A 3500) from the BCRA API, one year per call."""
    rows = []
    today = datetime.now(ZoneInfo("America/Argentina/Buenos_Aires")).date().isoformat()
    for year in range(int(START[:4]), int(today[:4]) + 1):
        r = requests.get(
            "https://api.bcra.gob.ar/estadisticascambiarias/v1.0/Cotizaciones/USD",
            params={"fechadesde": f"{year}-01-01", "fechahasta": min(f"{year}-12-31", today)},
            timeout=60,
        )
        r.raise_for_status()
        rows += [(d["fecha"], d["detalle"][0]["tipoCotizacion"]) for d in r.json()["results"] if d["detalle"]]
    df = pd.DataFrame(rows, columns=["date", "ars_per_usd"]).sort_values("date")
    df.to_csv(OUT_DIR / "BCRA_USD.csv", index=False)
    print(f"BCRA_USD: {len(df)} rows")


def download_ptax():
    """Brazilian central bank PTAX selling rate, reais per US$."""
    end = datetime.now(ZoneInfo("America/Sao_Paulo")).strftime("%m-%d-%Y")
    url = ("https://olinda.bcb.gov.br/olinda/servico/PTAX/versao/v1/odata/CotacaoDolarPeriodo(dataInicial=@a,dataFinalCotacao=@b)"
           f"?@a='01-01-{START[:4]}'&@b='{end}'&$format=json&$select=cotacaoVenda,dataHoraCotacao")
    df = pd.DataFrame(get(url).json()["value"])
    df["date"] = pd.to_datetime(df["dataHoraCotacao"]).dt.date
    df = df.groupby("date")["cotacaoVenda"].last().rename("brl_per_usd")
    df.to_csv(OUT_DIR / "PTAX.csv")
    print(f"PTAX: {len(df)} rows")


def download_ccl():
    """Contado con liquidacion from Ambito: no official body publishes this rate, and its series starts in 2013."""
    rows = []
    today = datetime.now(ZoneInfo("America/Argentina/Buenos_Aires")).date()
    for m in pd.date_range("2013-01-01", today, freq="MS"):
        end = min((m + pd.offsets.MonthEnd(0)).date(), today)
        r = requests.get(f"https://mercados.ambito.com/dolarrava/cl/historico-general/{m.date()}/{end}", headers=BROWSER, timeout=60)
        if r.status_code == 200:
            rows += r.json()[1:]
        else:
            days = pd.date_range(m, end, freq="B")
            for d in days:
                x = requests.get(f"https://mercados.ambito.com/dolarrava/cl/historico-general/{d.date()}/{d.date()}", headers=BROWSER, timeout=60)
                if x.status_code == 200:
                    rows += x.json()[1:]
    df = pd.DataFrame(rows, columns=["date", "ars_per_usd"])
    df["date"] = pd.to_datetime(df["date"], dayfirst=True).dt.date
    df["ars_per_usd"] = df["ars_per_usd"].str.replace(".", "").str.replace(",", ".").astype(float)
    df = df.drop_duplicates("date").sort_values("date")
    df.to_csv(OUT_DIR / "CCL.csv", index=False)
    print(f"CCL: {len(df)} rows")


def download_ibovespa():
    """Bovespa closes from B3, which serves one table per year (days by months)."""
    rows = []
    for year in range(int(START[:4]), datetime.now().year + 1):
        key = base64.b64encode(json.dumps({"language": "en-us", "index": "IBOV", "year": str(year)}).encode()).decode()
        table = get(f"https://sistemaswebb3-listados.b3.com.br/indexStatisticsProxy/IndexCall/GetPortfolioDay/{key}").json()["results"]
        for x in table:
            rows += [(f"{year}-{m:02d}-{x['day']:02d}", float(x[f"rateValue{m}"].replace(",", ""))) for m in range(1, 13) if x[f"rateValue{m}"]]
    df = pd.DataFrame(rows, columns=["date", "ibovespa"]).sort_values("date")
    df.to_csv(OUT_DIR / "IBOV.csv", index=False)
    print(f"IBOV: {len(df)} rows")


def parse_cotahist(data):
    """Cash-market rows of a B3 COTAHIST file: date, ticker, close in reais."""
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        text = z.read(z.namelist()[0]).decode("latin-1")
    return [(l[2:10], B3_STOCKS[l[12:24].strip()], int(l[108:121]) / 100) for l in text.splitlines()
            if l[:2] == "01" and l[24:27] == "010" and l[12:24].strip() in B3_STOCKS]


def download_b3_stocks():
    rows = []
    for year in range(B3_FIRST_YEAR, datetime.now().year + 1):
        rows += parse_cotahist(get(f"https://bvmf.bmfbovespa.com.br/InstDados/SerHist/COTAHIST_A{year}.ZIP").content)
    save_b3_stocks(rows)


def save_b3_stocks(rows):
    df = pd.DataFrame(rows, columns=["date", "ticker", "close"])
    df["date"] = pd.to_datetime(df["date"])
    for t, g in df.groupby("ticker"):
        c = g.set_index("date")["close"].sort_index()
        for day, ratio in B3_SPLITS.get(t, {}).items():
            c[c.index < day] *= ratio
        c.rename("brl").to_csv(OUT_DIR / f"{t}.csv")
        print(f"{t}: {len(c)} rows")


def download_inflation():
    """Monthly CPI levels: IBGE for Brazil, INDEC for Argentina, FRED (OECD) for Mexico, which ends in 2024."""
    r = requests.get("https://apisidra.ibge.gov.br/values/t/1737/n1/all/v/2266/p/all", timeout=120)
    r.raise_for_status()
    rows = [(f"{x['D3C'][:4]}-{x['D3C'][4:]}-01", float(x["V"])) for x in r.json()[1:] if x["V"] not in ("...", "-")]
    pd.DataFrame(rows, columns=["date", "cpi"]).to_csv(OUT_DIR / "CPI_BR.csv", index=False)
    r = requests.get(
        "https://apis.datos.gob.ar/series/api/series/",
        params={"ids": "148.3_INIVELNAL_DICI_M_26", "limit": 5000, "format": "csv"},
        timeout=60,
    )
    r.raise_for_status()
    df = pd.read_csv(io.StringIO(r.text))
    df.columns = ["date", "cpi"]
    df.to_csv(OUT_DIR / "CPI_AR.csv", index=False)
    r = requests.get("https://fred.stlouisfed.org/graph/fredgraph.csv?id=MEXCPIALLMINMEI", timeout=60)
    r.raise_for_status()
    df = pd.read_csv(io.StringIO(r.text))
    df.columns = ["date", "cpi"]
    df.to_csv(OUT_DIR / "CPI_MX.csv", index=False)
    print("CPI: Brazil, Argentina, Mexico saved")


def download_earnings_dates():
    """Earnings release dates from 8-K Item 2.02 filings on EDGAR (times are UTC)."""
    headers = {"User-Agent": "meli-risk-and-options research project"}
    rows = []
    for ticker, cik in EARNINGS_CIKS.items():
        r = requests.get(f"https://data.sec.gov/submissions/CIK{cik:010d}.json", headers=headers, timeout=60)
        r.raise_for_status()
        f = r.json()["filings"]["recent"]
        rows += [
            (ticker, f["filingDate"][i], f["acceptanceDateTime"][i], f["accessionNumber"][i])
            for i in range(len(f["form"]))
            if f["form"][i] == "8-K" and "2.02" in f["items"][i]
        ]
    df = pd.DataFrame(rows, columns=["ticker", "filing_date", "accepted_utc", "accession"])
    df["accepted_et"] = (
        pd.to_datetime(df["accepted_utc"], utc=True).dt.tz_convert("America/New_York").dt.strftime("%Y-%m-%d %H:%M")
    )
    df = df.sort_values(["ticker", "filing_date"])
    df.to_csv(OUT_DIR.parent / "earnings_dates.csv", index=False)
    print(f"earnings_dates: {len(df)} rows")


if __name__ == "__main__":
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    download_prices()
    download_fred()
    download_bcra()
    download_ptax()
    download_ccl()
    download_ibovespa()
    download_b3_stocks()
    download_inflation()
    download_earnings_dates()
