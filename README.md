# Hang Seng Sentiment Price Prediction Agent

Pipeline: Apify (social posts) + Exa (news) + yfinance (prices) -> LLM (NVIDIA NIM) sentiment/extraction -> features -> walk-forward Ridge model -> Plotly HTML report.

## Setup
```
pip install -r requirements.txt
cp .env.example .env   # fill in keys and Apify actor IDs
python main.py --refresh   # scrape + score + model + report
python main.py             # reuse cached data/scored.csv
```
Open `reports/report.html`.

## API keys
- Apify: https://console.apify.com/settings/integrations
- Exa: https://dashboard.exa.ai/api-keys
- NVIDIA NIM: https://build.nvidia.com (open any model, click Get API Key)

## Sources
- Exchange: HKEX (Tencent, Alibaba, HSBC, Meituan, Xiaomi)
- Social: Telegram + LIHKG via Apify. Actor IDs: (fill in)
- News: Exa.com
- Actor IDs: tri_angle/telegram-scraper and claude_code_reviewer/lihkg-scraper-en
- Telegram Channels used: SmallCapAsiaChannel,investkaki

## Method
- Posts aligned to hourly price bars in UTC (latest bar at/before post time).
- Sentiment per post by LLM in [-1,1], weighted by engagement and author followers.
- Features: social sentiment, mentions, sentiment change, news sentiment, previous return. Target: next-bar return (n+1).
- Validation: expanding-window walk-forward, compared with the naive "next = current" baseline.

## Limitations
10 days of data is a tiny sample; results are noisy and not evidence of tradable edge.
