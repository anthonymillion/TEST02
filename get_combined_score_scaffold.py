import streamlit as st
import pandas as pd
import yfinance as yf
import requests

# API Keys (replace with your actual keys)
TRADING_ECON_API_USER = "c88d1d122399451"
TRADING_ECON_API_PASS = "rdog9czpshn7zb9"
FINNHUB_API_KEY = "d1uv2rhr01qujmdeohv0d1uv2rhr01qujmdeohvg"

stock_list = ["NVDA", "MSFT", "AAPL", "AMZN", "GOOGL", "GOOG", "META", "TSLA"]  # Your list can be bigger

macro_symbols = {
    "DXY": "DXY",
    "USDJPY": "USDJPY=X",
    "XAUUSD": "XAUUSD=X",
    "BTCUSD": "BTC-USD",
    "S&P500": "^GSPC"
}

st.sidebar.title("📊 Scanner Settings")
timeframe = st.sidebar.selectbox("Select Timeframe", ["1m", "5m", "15m", "1h", "1d", "1wk", "1mo"])
st.title("🧠 Live Multi-Sentiment Stock Scanner")

macro_prices = {}
for label, ticker in macro_symbols.items():
    try:
        data = yf.Ticker(ticker).history(period="1d", interval="1h")
        last_price = data["Close"][-1] if not data.empty else None
        macro_prices[label] = round(last_price, 2) if last_price else "N/A"
    except:
        macro_prices[label] = "Error"

def get_combined_score(symbol):
    score = 0

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

    try:
        cot_signal = 0
        score += cot_signal
    except:
        pass

    try:
        macro_risk_score = 0
        score += macro_risk_score
    except:
        pass

    try:
        geopolitics_keywords = ["conflict", "war", "sanction", "invasion", "tension", "missile"]
        geopolitics_score = -1 if any(k in str(data).lower() for k in geopolitics_keywords) else 0
        score += geopolitics_score
    except:
        pass

    try:
        options_signal = 0
        score += options_signal
    except:
        pass

    return score

rows = []
for symbol in stock_list:
    st.write(f"Processing {symbol}...")  # Debug log line

    try:
        ticker = yf.Ticker(symbol)
        data = ticker.history(period="5d", interval=timeframe)
        info = ticker.info

        price = data["Close"][-1] if not data.empty else None
        volume = data["Volume"][-1] if not data.empty else None
        float_shares = info.get("floatShares", 0)

        try:
            score = get_combined_score(symbol)
        except:
            score = 0

        sentiment = "🟢 Bullish" if score > 0 else "🔴 Bearish" if score < 0 else "⚪ Neutral"

        row = {
            "Symbol": symbol,
            "Price": f"${price:.2f}" if price else "N/A",
            "Volume": f"{volume / 1e6:.2f}M" if volume else "N/A",
            "Float": f"{float_shares / 1e6:.2f}M" if float_shares else "N/A",
            "Score": f"+{score}" if score > 0 else f"{score}",
            "Sentiment": sentiment
        }

        for macro_label, macro_price in macro_prices.items():
            row[macro_label] = f"${macro_price}" if isinstance(macro_price, (float, int)) else macro_price

        rows.append(row)

    except Exception as e:
        st.write(f"❌ Error with {symbol}: {e}")
        rows.append({
            "Symbol": symbol,
            "Price": "Error",
            "Volume": "Error",
            "Float": "Error",
            "Score": "Error",
            "Sentiment": "❌",
            **{label: "N/A" for label in macro_symbols.keys()}
        })

df = pd.DataFrame(rows)
df = df.sort_values(by="Score", ascending=False)
st.dataframe(df, use_container_width=True)
