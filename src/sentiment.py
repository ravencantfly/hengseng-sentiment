"""LLM sentiment + structured extraction (NVIDIA NIM, OpenAI-compatible API).
NVIDIA retires hosted models often, so if the configured model returns 404/410 we list the
available models and switch automatically (the chosen model is printed)."""
import json, os, re, time
import pandas as pd
from openai import OpenAI, APIStatusError

BASE_URL = "https://integrate.api.nvidia.com/v1"
MODEL = os.getenv("NVIDIA_MODEL", "").strip()          # optional; leave empty to auto-pick
PREFER = ["qwen/qwen3", "qwen/qwen2.5", "meta/llama-4", "meta/llama-3.3", "nvidia/nemotron-3-nano",
          "nvidia/nemotron-3-super", "mistralai/mistral", "meta/llama-3.1", "deepseek"]
SKIP = ["vision", "embed", "rerank", "guard", "safety", "coder", "reward", "parse", "-vl", "clip",
        "whisper", "tts", "image", "retriev", "nemoretriever", "code"]

PROMPT = """You analyse posts about the stock {name} ({ticker}). Posts may be in English, Traditional/Simplified Chinese or Cantonese.
For each post return JSON: {{"id": int, "score": float in [-1,1] (bearish..bullish, 0 neutral/irrelevant),
"position": string or null (e.g. "long @320", "short"), "support": number or null, "resistance": number or null}}.
Return ONLY a JSON list, no other text.

Posts:
{posts}"""

_state = {"model": MODEL, "bad": set()}


def choose_model(client):
    ids = [m.id for m in client.models.list().data]
    ok = [i for i in ids if i not in _state["bad"] and not any(s in i.lower() for s in SKIP)]
    for pref in PREFER:
        for i in ok:
            if pref in i.lower():
                return i
    if ok:
        return ok[0]
    raise RuntimeError("No usable chat model found on NVIDIA NIM. Pick one at build.nvidia.com and set NVIDIA_MODEL in .env")


def ask(client, prompt):
    for attempt in range(6):
        if not _state["model"]:
            _state["model"] = choose_model(client)
            print(f"[sentiment] using model: {_state['model']}")
        try:
            r = client.chat.completions.create(model=_state["model"], max_tokens=3000, temperature=0,
                                               messages=[{"role": "user", "content": prompt}])
            return r.choices[0].message.content or ""
        except APIStatusError as e:
            if e.status_code in (404, 410):               # model retired / not found -> switch
                print(f"[sentiment] model {_state['model']} unavailable ({e.status_code}); switching")
                _state["bad"].add(_state["model"]); _state["model"] = ""
            elif e.status_code == 429:                    # rate limit -> wait and retry
                time.sleep(10 * (attempt + 1))
            else:
                raise
    raise RuntimeError("LLM call failed after retries")


def parse(text):
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.S)      # reasoning models
    m = re.search(r"\[.*\]", text, re.S)
    try:
        return {r["id"]: r for r in json.loads(m.group(0))} if m else {}
    except (json.JSONDecodeError, KeyError, TypeError):
        return {}


def score_df(df, ticker_names, batch=20):
    client = OpenAI(base_url=BASE_URL, api_key=os.environ["NVIDIA_API_KEY"])
    out = []
    for ticker, g in df.groupby("ticker"):
        g = g.reset_index(drop=True)
        for i in range(0, len(g), batch):
            chunk = g.iloc[i:i + batch]
            posts = "\n".join(f"[{j}] {t[:500]!r}" for j, t in zip(chunk.index, chunk.text))
            res = parse(ask(client, PROMPT.format(name=ticker_names[ticker], ticker=ticker, posts=posts)))
            for j in chunk.index:
                r = res.get(j, {})
                try:
                    score = float(r.get("score", 0.0) or 0.0)
                except (TypeError, ValueError):
                    score = 0.0
                out.append({**g.loc[j].to_dict(), "score": max(-1.0, min(1.0, score)),
                            "position": r.get("position"), "support": r.get("support"),
                            "resistance": r.get("resistance")})
    return pd.DataFrame(out)
