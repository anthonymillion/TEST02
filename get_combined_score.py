import requests
import datetime

FINNHUB_API_KEY = "d1uv2rhr01qujmdeohv0d1uv2rhr01qujmdeohvg"
TE_USERNAME = "c88d1d122399451"
TE_API_KEY = "rdog9czpshn7zb9"

def get_combined_score(symbol: str) -> float:
    news_sentiment = 0
    earnings_sentiment = 0
    ipo_sentiment = 0
    macro_risk_score = 0
    options_sentiment = 0
    cot_sentiment = 0
    geo_risk = 0

    try:
        # 1. News Sentiment
        news_url = f"https://finnhub.io/api/v1/news-sentiment?symbol={symbol}&token={FINNHUB_API_KEY}"
        news_res = requests.get(news_url).json()
        news_sentiment = news_res.get("sentiment", {}).get("score", 0)

        # 2. Earnings Sentiment
        earnings_url = f"https://finnhub.io/api/v1/stock/earnings?symbol={symbol}&token={FINNHUB_API_KEY}"
        earnings_res = requests.get(earnings_url).json()
        if earnings_res:
            latest = earnings_res[0]
            surprise = latest["actual"] - latest["estimate"]
            earnings_sentiment = 0.7 if surprise > 0 else -0.7 if surprise < 0 else 0

        # 3. IPO Sentiment
        today = datetime.date.today()
        month_start = today.replace(day=1).strftime('%Y-%m-%d')
        month_end = (today.replace(day=28) + datetime.timedelta(days=4)).replace(day=1) - datetime.timedelta(days=1)
        ipo_url = f"https://finnhub.io/api/v1/calendar/ipo?from={month_start}&to={month_end}&token={FINNHUB_API_KEY}"
        ipo_res = requests.get(ipo_url).json()
        ipo_count = len(ipo_res.get("ipoCalendar", []))
        ipo_sentiment = 0.5 if ipo_count > 5 else -0.5

        # 4. Macro Risk Score
        calendar_url = f"https://api.tradingeconomics.com/calendar/country/all?c={TE_USERNAME}:{TE_API_KEY}"
        cal_res = requests.get(calendar_url).json()
        upcoming_events = [e for e in cal_res if e.get("Importance", 0) >= 2 and e.get("Date")]
        macro_risk_score = -1 if len(upcoming_events) > 10 else 1

        # 5. Options Sentiment (calls vs puts)
        yahoo_url = f"https://query2.finance.yahoo.com/v7/finance/options/{symbol}"
        opt_res = requests.get(yahoo_url).json()
        options_data = opt_res["optionChain"]["result"][0]["options"][0]
        calls = len(options_data.get("calls", []))
        puts = len(options_data.get("puts", []))
        options_sentiment = 0.6 if calls > puts else -0.6 if puts > calls else 0

        # 6. COT Sentiment (placeholder logic)
        cot_url = f"https://api.tradingeconomics.com/cot?symbol={symbol}&c={TE_USERNAME}:{TE_API_KEY}"
        cot_res = requests.get(cot_url).json()
        net = cot_res[0]["netPosition"] if cot_res and "netPosition" in cot_res[0] else 0
        cot_sentiment = 0.4 if net > 0 else -0.4 if net < 0 else 0

        # 7. Geopolitical Risk
        geo_url = f"https://finnhub.io/api/v1/news?category=general&token={FINNHUB_API_KEY}"
        geo_res = requests.get(geo_url).json()
        war_words = ["war", "conflict", "strike", "missile", "tensions", "nuclear"]
        war_count = sum(any(word in news["headline"].lower() for word in war_words) for news in geo_res)
        geo_risk = -0.5 if war_count > 3 else 0.2

    except Exception as e:
        print(f"Error getting sentiment for {symbol}: {str(e)}")

    # Weighted scoring
    score = (
        0.25 * news_sentiment +
        0.20 * earnings_sentiment +
        0.10 * ipo_sentiment +
        0.20 * macro_risk_score +
        0.10 * options_sentiment +
        0.10 * cot_sentiment +
        0.05 * geo_risk
    )

    print(f"[SCORE] {symbol}: {round(score, 2)} | Breakdown:", {
        "news": news_sentiment,
        "earnings": earnings_sentiment,
        "ipo": ipo_sentiment,
        "macro": macro_risk_score,
        "options": options_sentiment,
        "cot": cot_sentiment,
        "geo": geo_risk,
    })

    return round(score, 2)
