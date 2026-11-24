"""Scrape social posts with Apify. One run per source (cached in data/raw/), then tag each
post with the stock(s) it mentions by keyword matching.
Edit build_input() / normalize() per actor."""
import json, os
import pandas as pd
from apify_client import ApifyClient
from .config import ALL_TICKERS, SOURCES, DAYS

RAW = "data/raw"


def build_input(source):
    if source == "telegram":
        channels = [c.strip().lstrip("@") for c in os.getenv("TELEGRAM_CHANNELS", "").split(",") if c.strip()]
        # 'profiles' is required by tri_angle/telegram-scraper; check its Input tab
        # for the field that limits the number of posts and add it here.
        return {"profiles": channels}
    # TODO: input for your second source (check its Input tab)
    kws = [k for m in ALL_TICKERS.values() for k in m["keywords"]]
    return {"searchTerms": kws, "maxItems": 300}


def pick(d, *keys, default=None):
    for k in keys:
        if k in d and d[k] is not None and d[k] != "":
            return d[k]
    return default


def to_ts(v):
    if v is None:
        return pd.NaT
    if isinstance(v, (int, float)):
        return pd.to_datetime(v, unit="s" if v < 1e11 else "ms", utc=True, errors="coerce")
    ts = pd.to_datetime(v, utc=True, errors="coerce")
    if pd.notna(ts) and ts.year < 2000:
        # Telegram shows dates like "Nov 23" (no year) for the current year -> pandas gives year 0001
        now = pd.Timestamp.now(tz="UTC")
        try:
            ts = ts.replace(year=now.year)
            if ts > now + pd.Timedelta(days=1):
                ts = ts.replace(year=now.year - 1)
        except ValueError:
            return pd.NaT
    return ts


def count(v):
    """likes/reactions can be a number, a list of {count: n} or a dict of numbers."""
    if isinstance(v, (int, float)):
        return v
    if isinstance(v, str):                      # "1.2K", "3M", "845"
        t = v.strip().upper().replace(",", "")
        try:
            mult = {"K": 1e3, "M": 1e6}.get(t[-1:], 1)
            return float(t[:-1] if mult != 1 else t) * mult
        except ValueError:
            return 0
    if isinstance(v, list):
        return sum(x.get("count", 0) if isinstance(x, dict) else 0 for x in v)
    if isinstance(v, dict):
        return sum(x for x in v.values() if isinstance(x, (int, float)))
    return 0


def normalize(item, source):
    m = item.get("message")
    flat = {**item, **m} if isinstance(m, dict) else {**item, "text": m}
    prev = flat.get("preview") if isinstance(flat.get("preview"), dict) else {}
    parts = [pick(flat, "text", "content", default=""), pick(flat, "description", default=""),
             prev.get("title", "") or "", prev.get("description", "") or ""]
    text = " ".join(dict.fromkeys(str(p).strip() for p in parts if p and str(p).strip()))
    return {
        "ts": to_ts(pick(flat, "fulldate", "datetime", "dateTime", "timestamp", "createdAt", "publishedAt", "date", "time")),
        "text": text,
        "likes": count(pick(flat, "likes", "likeCount", "reactions", default=0)),
        "reposts": count(pick(flat, "reposts", "shares", "forwards", "retweetCount", default=0)),
        "views": count(pick(flat, "views", "viewCount", default=0)),
        "followers": count(pick(flat, "followers", "authorFollowers", "subscribers", default=0)),
        "source": source,
    }


def tag_tickers(df):
    """A post can mention several stocks -> one row per (post, ticker)."""
    rows = []
    for _, r in df.iterrows():
        text = r["text"].lower()
        for ticker, meta in ALL_TICKERS.items():
            if any(k.lower() in text for k in meta["keywords"]):
                rows.append({**r.to_dict(), "ticker": ticker})
    if not rows:
        print("[warning] No social posts mention your stocks in the last 10 days. "
              "Continuing with news only. Add more active channels or keywords.")
        return pd.DataFrame(columns=list(df.columns) + ["ticker"])
    out = pd.DataFrame(rows)
    print(f"[tagged] {len(out)} post-stock matches")
    return out


def scrape(force=False):
    os.makedirs(RAW, exist_ok=True)
    client = ApifyClient(os.environ["APIFY_TOKEN"])
    all_rows = []
    for source, actor in SOURCES.items():
        if not actor:
            print(f"[skip] no actor id for {source}")
            continue
        path = f"{RAW}/{source}.json"
        if os.path.exists(path) and not force:      # cache = save free-tier credits
            items = json.load(open(path, encoding="utf-8"))
        else:
            try:
                run = client.actor(actor).call(run_input=build_input(source))
            except Exception as e:
                print(f"[error] {source}: {e}")
                continue
            dataset_id = getattr(run, "default_dataset_id", None) or run["defaultDatasetId"]
            items = list(client.dataset(dataset_id).iterate_items())
            json.dump(items, open(path, "w", encoding="utf-8"), ensure_ascii=False)
        print(f"[{source}] {len(items)} items; first item keys: {list(items[0].keys()) if items else None}")
        all_rows += [normalize(i, source) for i in items]
    if not all_rows:
        raise RuntimeError("No social posts scraped. Check actor IDs / inputs above.")
    df = pd.DataFrame(all_rows)
    df["ts"] = pd.to_datetime(df["ts"], utc=True, errors="coerce")
    df = df.dropna(subset=["ts"])
    print(f"{len(df)} posts with a valid date")
    df = df[df.ts >= pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=DAYS)]
    print(f"{len(df)} posts in the last {DAYS} days")
    df = df[df.text.str.len() > 0]
    df = tag_tickers(df).drop_duplicates(["source", "ticker", "text"])
    print(df.groupby(["source", "ticker"]).size())
    df.to_csv("data/posts.csv", index=False)
    return df
