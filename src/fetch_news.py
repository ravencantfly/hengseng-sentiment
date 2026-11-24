import os
import pandas as pd
from exa_py import Exa
from .config import ALL_TICKERS, DAYS

def fetch_news():
    exa = Exa(os.environ["EXA_API_KEY"])
    start = (pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=DAYS)).strftime("%Y-%m-%dT00:00:00.000Z")
    rows = []
    for ticker, meta in ALL_TICKERS.items():
        res = exa.search_and_contents(
            f"{meta['name']} stock {ticker} news", num_results=10,
            start_published_date=start, text={"max_characters": 1500})
        for r in res.results:
            rows.append({"ts": pd.to_datetime(r.published_date, utc=True, errors="coerce"),
                         "text": f"{r.title}. {r.text or ''}", "likes": 0, "reposts": 0, "views": 0,
                         "followers": 0, "ticker": ticker, "source": "news", "url": r.url})
    df = pd.DataFrame(rows).dropna(subset=["ts"])
    df.to_csv("data/news.csv", index=False)
    return df
