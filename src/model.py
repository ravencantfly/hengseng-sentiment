"""Expanding-window walk-forward validation (never shuffles time) vs a naive baseline."""
import numpy as np, pandas as pd
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from .features import FEATURES

def walk_forward(df, min_train=40):
    d = df.dropna(subset=FEATURES + ["target"]).sort_values("bar")
    preds = []
    for bar in sorted(d.bar.unique()):
        train, test = d[d.bar < bar], d[d.bar == bar]
        if len(train) < min_train:
            continue
        m = make_pipeline(StandardScaler(), Ridge(alpha=10.0)).fit(train[FEATURES], train.target)
        t = test.copy(); t["pred_ret"] = m.predict(test[FEATURES]); preds.append(t)
    if not preds:
        raise RuntimeError("Not enough data for walk-forward; lower min_train or add data")
    p = pd.concat(preds)
    p["pred_close"] = p.close * (1 + p.pred_ret)
    p["naive_close"] = p.close                                   # baseline: next = current
    return p

def metrics(p):
    mae = lambda a, b: float(np.mean(np.abs(a - b)))
    return {
        "n_test": len(p),
        "MAE_model": mae(p.pred_close, p.next_close),
        "MAE_naive": mae(p.naive_close, p.next_close),
        "directional_acc": float((np.sign(p.pred_ret) == np.sign(p.target)).mean()),
    }
