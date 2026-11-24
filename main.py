import os, sys
import pandas as pd
from src.config import ALL_TICKERS
from src import scrape_social, fetch_news, prices, sentiment, features, model, report

def main(refresh=False):
    px = prices.get_prices()
    if refresh or not os.path.exists("data/scored.csv"):
        social = scrape_social.scrape(force=refresh)
        news = fetch_news.fetch_news()
        allp = pd.concat([social, news], ignore_index=True)
        scored = sentiment.score_df(allp, {t: m["name"] for t, m in ALL_TICKERS.items()})
        scored.to_csv("data/scored.csv", index=False)
    scored = pd.read_csv("data/scored.csv", parse_dates=["ts"])
    scored["ts"] = pd.to_datetime(scored.ts, utc=True)
    px["bar"] = pd.to_datetime(px.bar, utc=True)
    feat = features.build(px, scored)
    preds = model.walk_forward(feat)
    m = model.metrics(preds); print(m)
    report.build_report(feat, scored, preds, m)
    print("Report -> reports/report.html")

if __name__ == "__main__":
    main(refresh="--refresh" in sys.argv)
