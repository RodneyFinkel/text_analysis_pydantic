from bs4 import BeautifulSoup
import requests
from pprint import pprint
#from rsa import key
from tensorboard import data
import yfinance as yf
import pandas as pd
import time
import redis
import json

from yfinance import data

from yfinance import ticker

def headers():
    return {
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36",
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "accept-language": "en-US,en;q=0.9",
        "accept-encoding": "gzip, deflate, br",
        "cache-control": "max-age=0",
        "connection": "keep-alive",
        "referer": "https://finance.yahoo.com/",
        "sec-ch-ua": '"Chromium";v="117", "Not;A=Brand";v="8", "Google Chrome";v="117"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"macOS"',
        "sec-fetch-dest": "document",
        "sec-fetch-mode": "navigate",
        "sec-fetch-site": "same-origin",
        "sec-fetch-user": "?1",
        "upgrade-insecure-requests": "1",
    }


# REDIS SETUP

r = redis.Redis(host="localhost", port=6379, db=0)

CACHE_TTL = 60 * 60 * 24  # 24h

BASE_URL = "https://query1.finance.yahoo.com/v10/finance/quoteSummary/{}"

def fetch_yahoo_raw(ticker):
    params = {
        "modules": ",".join([
            "defaultKeyStatistics",
            "financialData",
            "summaryDetail",
            "price"
        ])
    }

    resp = requests.get(
        BASE_URL.format(ticker),
        headers=headers(),
        params=params,
        timeout=15
    )

    resp.raise_for_status()

    data = resp.json()["quoteSummary"]["result"][0]
    return data


def get_cached_yahoo(ticker):
    key = f"yahoo:{ticker}"

    cached = r.get(key)
    if cached:
        print(f"Using cached data for {ticker}")
        return json.loads(cached)

    data = fetch_yahoo_raw(ticker)
    
    r.setex(key, CACHE_TTL, json.dumps(data))

    return data


# =========================
# UNWRAP HELPERS
# =========================

def u(x):
    if isinstance(x, dict):
        return x.get("raw", x.get("fmt"))
    return x



# FEATURE EXTRACTION (FUNDAMENTALS)


def extract_fundamentals(data):
    return {
        "market_cap": u(data.get("marketCap")),
        "beta": u(data.get("beta")),

        "shares_outstanding": u(data.get("sharesOutstanding")),
        "float": u(data.get("floatShares")),

        "held_by_insiders": u(data.get("heldPercentInsiders")),
        "held_by_institutions": u(data.get("heldPercentInstitutions")),

        "short_ratio": u(data.get("shortRatio")),

        "profit_margin": u(data.get("profitMargins")),
        "operating_margin": u(data.get("operatingMargins")),
        "roe": u(data.get("returnOnEquity")),
        "roa": u(data.get("returnOnAssets")),

        "revenue": u(data.get("totalRevenue")),
        "gross_profit": u(data.get("grossProfits")),
        "ebitda": u(data.get("ebitda")),
        "net_income": u(data.get("netIncomeToCommon")),
        "eps": u(data.get("trailingEps")),

        "total_cash": u(data.get("totalCash")),
        "total_debt": u(data.get("totalDebt")),
        "current_ratio": u(data.get("currentRatio")),
        "debt_to_equity": u(data.get("debtToEquity")),

        "operating_cash_flow": u(data.get("operatingCashflow")),
        "free_cash_flow": u(data.get("freeCashflow")),

        "payout_ratio": u(data.get("payoutRatio")),

        "52_week_high": u(data.get("fiftyTwoWeekHigh")),
        "52_week_low": u(data.get("fiftyTwoWeekLow")),

        "avg_vol_3m": u(data.get("averageVolume")),
        "avg_vol_10d": u(data.get("averageVolume10days")),
    }


# TECHNICAL FEATURES


def extract_technicals(ticker):
    df = yf.download(ticker, period="1y", progress=False)

    if df.empty:
        return {}

    close = df["Close"]
    volume = df["Volume"]
    returns = close.pct_change()

    return {
        "return_1d": returns.mean(),
        "volatility": returns.std(),

        "50_day_ma": close.rolling(50).mean().iloc[-1],
        "200_day_ma": close.rolling(200).mean().iloc[-1]

        # "avg_vol_10d": volume.rolling(10).mean().iloc[-1],
        # "avg_vol_3m": volume.rolling(63).mean().iloc[-1],
    }



# FULL FEATURE BUILDER


def build_feature_matrix(tickers):
    rows = []

    for t in tickers:
        try:
            raw = get_cached_yahoo(t)          # Redis cached API call
            fund = extract_fundamentals(raw)
            tech = extract_technicals(t)

            row = {"ticker": t, **fund, **tech}
            rows.append(row)

        except Exception as e:
            print(f"{t} failed: {e}")

    df = pd.DataFrame(rows).set_index("ticker")

    # PCA-ready numeric matrix
    df = df.apply(pd.to_numeric, errors="coerce")

    return df



if __name__ == "__main__":
    tickers = ["TSLA", "AAPL", "MSFT", "NVDA", "AMZN"]

    X = build_feature_matrix(tickers)

    print(X)

    output_file = "feature_matrix.csv"
    X.to_csv(output_file)
    print(f"Saved feature matrix to {output_file}")


#     metric_aliases = {
#             'Market Cap (intraday)': 'market_cap',
#             'Beta (5Y Monthly)': 'beta',
#             '52 Week High 3': '52_week_high',
#             '52 Week Low 3': '52_week_low',
#             '50-Day Moving Average 3': '50_day_ma',
#             '200-Day Moving Average 3': '200_day_ma',
#             'Avg Vol (3 month) 3': 'avg_vol_3m',
#             'Avg Vol (10 day) 3': 'avg_vol_10d',
#             'Shares Outstanding 5': 'shares_outstanding',
#             'Float 8': 'float',
#             '% Held by Insiders 1': 'held_by_insiders',
#             '% Held by Institutions 1': 'held_by_institutions',
#             'Short Ratio (Jan 30, 2023) 4': 'short_ratio',
#             'Payout Ratio 4': 'payout_ratio',
#             'Profit Margin': 'profit_margin',
#             'Operating Margin  (ttm)': 'operating_margin',
#             'Return on Assets  (ttm)': 'return_on_assets',
#             'Return on Equity  (ttm)': 'return_on_equity',
#             'Revenue  (ttm)': 'revenue',
#             'Revenue Per Share  (ttm)': 'revenue_per_share',
#             'Gross Profit  (ttm)': 'gross_profit',
#             'EBITDA': 'ebitda',
#             'Net Income Avi to Common  (ttm)': 'net_income',
#             'Diluted EPS  (ttm)': 'eps',
#             'Total Cash  (mrq)': 'total_cash',
#             'Total Cash Per Share  (mrq)': 'cash_per_share',
#             'Total Debt  (mrq)': 'total_debt',
#             'Total Debt/Equity  (mrq)': 'debt_to_equity',
#             'Current Ratio  (mrq)': 'current_ratio',
#             'Book Value Per Share  (mrq)': 'book_value_per_share',
#             'Operating Cash Flow  (ttm)': 'operating_cash_flow',
#             'Levered Free Cash Flow  (ttm)': 'levered_free_cash_flow'
#         }
    
    
    
    
# import scratch_pad, pprint, pandas as pd, requests
# from scratch_pad import get_cached_yahoo, extract_fundamentals, build_feature_matrix
# for t in ['TSLA', 'AAPL']:
#     print('----', t)
#     data = get_cached_yahoo(t)
#     fundamentals = extract_fundamentals(data)
#     pprint.pprint(fundamentals)
#     rows = []
#     row = {"ticker": t, **fundamentals}
#     rows.append(row)
#     df = pd.DataFrame(rows).set_index("ticker")
#     output_file = "fundamentals_test2.csv"
#     df.to_csv(output_file) 