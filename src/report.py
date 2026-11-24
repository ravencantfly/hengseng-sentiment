import numpy as np, pandas as pd, plotly.graph_objects as go
from plotly.subplots import make_subplots
from .config import EXCHANGES, ALL_TICKERS

def direction(s):
    return "Bullish" if s > 0.15 else "Bearish" if s < -0.15 else "Neutral"

def ticker_summary(feat, scored):
    rows = []
    for t, meta in ALL_TICKERS.items():
        f = feat[feat.ticker == t]; s = scored[(scored.ticker == t) & (scored.source != "news")]
        if f.empty: continue
        recent = f.tail(40)
        sent = float(s.score.mean()) if len(s) else 0.0
        pos = s.position.dropna()
        rows.append({"ticker": t, "name": meta["name"], "price": round(f.close.iloc[-1], 2),
                     "mentions": len(s), "sentiment": round(sent, 3), "direction": direction(sent),
                     "top_position": pos.mode().iloc[0] if len(pos) else "-",
                     "support (posts)": round(s.support.dropna().median(), 2) if s.support.notna().any() else None,
                     "resistance (posts)": round(s.resistance.dropna().median(), 2) if s.resistance.notna().any() else None,
                     "support (calc)": round(recent.low.min(), 2), "resistance (calc)": round(recent.high.max(), 2)})
    return pd.DataFrame(rows)

def build_report(feat, scored, preds, metrics, path="reports/report.html"):
    summ = ticker_summary(feat, scored)
    parts = ["<h1>Hang Seng Sentiment Report</h1>"]
    for ex, tks in EXCHANGES.items():
        s = summ[summ.ticker.isin(tks)].sort_values(["mentions", "sentiment"], ascending=False)
        fig = go.Figure(go.Table(header=dict(values=list(s.columns), fill_color="#222", font_color="white"),
                                 cells=dict(values=[s[c] for c in s.columns])))
        fig.update_layout(title=f"{ex}: ranked by mentions / sentiment", height=330)
        parts.append(fig.to_html(full_html=False, include_plotlyjs="cdn"))
        bar = go.Figure(go.Bar(x=s.name, y=s.sentiment, marker_color=["green" if v > 0 else "red" for v in s.sentiment]))
        bar.update_layout(title=f"{ex}: sentiment score", height=300)
        parts.append(bar.to_html(full_html=False, include_plotlyjs=False))
    for t in ALL_TICKERS:
        f = feat[feat.ticker == t]; p = preds[preds.ticker == t]
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        fig.add_trace(go.Scatter(x=f.bar, y=f.close, name="close"), secondary_y=False)
        fig.add_trace(go.Bar(x=f.bar, y=f.social_sent, name="social sentiment", opacity=.4), secondary_y=True)
        if len(p):
            fig.add_trace(go.Scatter(x=p.bar, y=p.pred_close, name="predicted n+1 close", mode="markers"), secondary_y=False)
            fig.add_trace(go.Scatter(x=p.bar, y=p.next_close, name="actual n+1 close", mode="markers"), secondary_y=False)
        fig.update_layout(title=f"{t} price vs sentiment & prediction", height=400)
        parts.append(fig.to_html(full_html=False, include_plotlyjs=False))
    parts.append("<h2>Out-of-sample results (walk-forward)</h2><pre>" + "\n".join(f"{k}: {v}" for k, v in metrics.items()) +
                 "</pre><p>Caveat: ~10 days of data is a very small sample; compare model MAE against the naive baseline.</p>")
    open(path, "w", encoding="utf-8").write("<html><body>" + "\n".join(parts) + "</body></html>")
    summ.to_csv("reports/summary.csv", index=False)
