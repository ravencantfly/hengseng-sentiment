import numpy as np, pandas as pd

def weight(df):
    eng = df.likes.fillna(0) + 2 * df.reposts.fillna(0) + df.views.fillna(0) / 100
    return (1 + np.log1p(eng)) * (1 + np.log1p(df.followers.fillna(0)) / 5)

def assign_bar(posts, prices):
    """Each post belongs to the latest price bar that started at/before it (UTC)."""
    bars = prices[["ticker", "bar"]].drop_duplicates().sort_values("bar")
    p = posts.sort_values("ts")
    return pd.merge_asof(p, bars, left_on="ts", right_on="bar", by="ticker", direction="backward").dropna(subset=["bar"])

def agg(df, prefix):
    df = df.assign(w=weight(df))
    df["ws"] = df.score * df.w
    g = df.groupby(["ticker", "bar"]).agg(ws=("ws", "sum"), w=("w", "sum"), n=("score", "size")).reset_index()
    g[f"{prefix}_sent"] = g.ws / g.w
    g[f"{prefix}_n"] = g.n
    return g[["ticker", "bar", f"{prefix}_sent", f"{prefix}_n"]]

def to_ns_utc(s):
    """Newer pandas keeps different time resolutions (s / us / ns); merges need identical ones."""
    return pd.to_datetime(s, utc=True).astype("datetime64[ns, UTC]")

def build(prices, scored):
    prices = prices.copy(); scored = scored.copy()
    prices["bar"] = to_ns_utc(prices["bar"])
    scored["ts"] = to_ns_utc(scored["ts"])
    scored = assign_bar(scored, prices)
    social = agg(scored[scored.source != "news"], "social")
    news = agg(scored[scored.source == "news"], "news")
    df = prices.merge(social, on=["ticker", "bar"], how="left").merge(news, on=["ticker", "bar"], how="left")
    df = df.sort_values(["ticker", "bar"])
    for c in ["social_sent", "social_n", "news_sent", "news_n"]:
        df[c] = df[c].fillna(0)
    df["news_sent"] = df.groupby("ticker").news_sent.transform(lambda s: s.replace(0, np.nan).ffill().fillna(0))
    df["ret"] = df.groupby("ticker").close.pct_change()
    df["d_sent"] = df.groupby("ticker").social_sent.diff().fillna(0)
    df["target"] = df.groupby("ticker").ret.shift(-1)          # next-bar return (n+1)
    df["next_close"] = df.groupby("ticker").close.shift(-1)
    return df

FEATURES = ["social_sent", "social_n", "d_sent", "news_sent", "ret"]
