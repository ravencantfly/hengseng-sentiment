import os
from dotenv import load_dotenv
load_dotenv()

DAYS = 10
INTERVAL = "1h"   # price bar size; "n+1" = next bar

EXCHANGES = {
    "HKEX (Hang Seng)": {
        "0700.HK": {"name": "Tencent",  "keywords": ["Tencent", "騰訊", "腾讯", "0700"]},
        "9988.HK": {"name": "Alibaba",  "keywords": ["Alibaba", "阿里巴巴", "阿里", "9988"]},
        "0005.HK": {"name": "HSBC",     "keywords": ["HSBC", "匯豐", "汇丰", "0005"]},
        "3690.HK": {"name": "Meituan",  "keywords": ["Meituan", "美團", "美团", "3690"]},
        "1810.HK": {"name": "Xiaomi",   "keywords": ["Xiaomi", "小米", "1810"]},
    },
    # Extra group: US tech names are discussed far more often in Asia-focused channels.
    # Delete this block if you want Hang Seng only.
    "NASDAQ (US tech)": {
        "NVDA":  {"name": "NVIDIA",    "keywords": ["NVIDIA", "NVDA", "英偉達", "英伟达", "輝達", "辉达"]},
        "TSLA":  {"name": "Tesla",     "keywords": ["Tesla", "TSLA", "特斯拉"]},
        "AAPL":  {"name": "Apple",     "keywords": ["Apple", "AAPL", "蘋果", "苹果"]},
        "MSFT":  {"name": "Microsoft", "keywords": ["Microsoft", "MSFT", "微軟", "微软"]},
        "GOOGL": {"name": "Alphabet",  "keywords": ["Alphabet", "GOOGL", "Google", "谷歌"]},
    },
}
ALL_TICKERS = {t: v for ex in EXCHANGES.values() for t, v in ex.items()}
def exchange_of(ticker):
    return next(e for e, ts in EXCHANGES.items() if ticker in ts)

# Two different social sources per exchange. Put the real Apify actor IDs in .env
SOURCES = {
    "telegram": os.getenv("APIFY_ACTOR_TELEGRAM", ""),
    "lihkg": os.getenv("APIFY_ACTOR_LIHKG", ""),
}
