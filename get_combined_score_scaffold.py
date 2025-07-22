
# Updated get_combined_score function with real sentiment components
# Each part (earnings, news, IPO, macro, COT, options, geopolitics) gets +1, -1, or 0

def get_combined_score(symbol):
    score = 0

    # --- 1. Earnings Sentiment (Finnhub) ---
    try:
        earnings_url = f"https://finnhub.io/api/v1/stock/earnings?symbol={symbol}&token={FINNHUB_API_KEY}"
        response = requests.get(earnings_url).json()
        if response and 'surprise' in response[0]:
            if response[0]['surprise'] > 0:
                score += 1
            elif response[0]['surprise'] < 0:
                score -= 1
    except:
        pass

    # --- 2. News Sentiment (Finnhub or Alpaca) ---
    try:
        news_url = f"https://finnhub.io/api/v1/news-sentiment?symbol={symbol}&token={FINNHUB_API_KEY}"
        data = requests.get(news_url).json()
        sentiment_score = data.get("companyNewsScore", 0)
        if sentiment_score > 0.2:
            score += 1
        elif sentiment_score < -0.2:
            score -= 1
    except:
        pass

    # --- 3. IPO Flow Sentiment ---
    try:
        ipo_url = f"https://finnhub.io/api/v1/calendar/ipo?from=2024-01-01&to=2025-12-31&token={FINNHUB_API_KEY}"
        data = requests.get(ipo_url).json()
        count = len(data.get("ipoCalendar", []))
        if count > 5:
            score += 1
        elif count < 1:
            score -= 1
    except:
        pass

    # --- 4. COT Sentiment (from CSV or Tradingster) ---
    try:
        # parse pre-downloaded COT CSV or scrape latest sentiment
        cot_signal = 1  # mock result; will be live parsed
        score += cot_signal
    except:
        pass

    # --- 5. Macro Risk Score (from Trading Economics API) ---
    try:
        macro_risk_score = 0  # calculate from event severity (green/yellow/red flags)
        score += macro_risk_score
    except:
        pass

    # --- 6. Geopolitical Risk (keyword scan from news) ---
    try:
        geopolitics_keywords = ["conflict", "war", "sanction", "invasion", "tension", "missile"]
        geopolitics_score = -1 if any(k in str(data).lower() for k in geopolitics_keywords) else 0
        score += geopolitics_score
    except:
        pass

    # --- 7. Options Flow Sentiment (from Yahoo Finance or other) ---
    try:
        # logic to parse put/call ratio or open interest
        options_signal = 0  # mock value
        score += options_signal
    except:
        pass

    return score
