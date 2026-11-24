import pandas as pd, yfinance as yf
from .config import ALL_TICKERS, DAYS, INTERVAL

def get_prices():
    frames = []
    for t in ALL_TICKERS:
        d = yf.Ticker(t).history(period=f"{max(DAYS, 5) + 20}d", interval=INTERVAL)
        d = d.rename(columns=str.lower)[["open", "high", "low", "close", "volume"]]
        d.index = d.index.tz_convert("UTC"); d.index.name = "bar"
        d["ticker"] = t
        frames.append(d.reset_index())
    df = pd.concat(frames)
    df.to_csv("data/prices.csv", index=False)
    return df
