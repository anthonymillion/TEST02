import streamlit as st
import pandas as pd
import yfinance as yf
import requests
from datetime import datetime, timedelta

# === API Keys ===
FINNHUB_API_KEY = "d1uv2rhr01qujmdeohv0d1uv2rhr01qujmdeohvg"
TRADING_ECON_USER = "c88d1d122399451"
TRADING_ECON_KEY = "rdog9czpshn7zb9"

# === Stock List ===
stock_list = [ "NVDA", "MSFT", "AAPL", "AMZN", "GOOGL", "GOOG", "META", "TSLA", "AVGO", "COST", "AMD", "NFLX" ]

# === Global Market Symbols ===
macro_symbols = {
    "DXY": "DXY", "USDJPY": "USDJPY=X", "XAUUSD": "XAUUSD=X", "EURUSD": "EURUSD=X",
    "BTCUSD": "BTC-USD", "ETHUSD": "ETH-USD", "S&P500": "^GSPC", "VIX": "^VIX"
}

# === Streamlit Setup ===
st.set_page_config(layout="wide")
st.title("Sentiment Scanner")
st.sidebar.title("Settings")
timeframe = st.sidebar.selectbox("Timeframe", ["1m", "5m", "15m", "1h", "1d"])

# === Logging Flag ===
DEBUG = True

# === Macro Risk Score ===
@st.cache_data(ttl=300)
def get_macro_risk_score():
    try:
        url = f"https://api.tradingeconomics.com/calendar/country/united states?c={TRADING_ECON_USER}:{TRADING_ECON_KEY}"
        res = requests.get(url).json()
        red = sum(1 for e in res if e.get("importance") == 3)
        yellow = sum(1 for e in res if e.get("importance") == 2)
        return red + 0.5 * yellow
    except Exception as e:
        if DEBUG: st.warning(f"Macro risk error: {e}")
        return 0

# === Combined Score ===
def get_combined_score(symbol):
    score = 0

    try:
        news = requests.get(f"https://finnhub.io/api/v1/news-sentiment?symbol={symbol}&token={FINNHUB_API_KEY}").json()
        if DEBUG: st.text(f"[{symbol}] News: {news.get('companyNewsScore')}")

        if news.get("companyNewsScore", 0) > 0.2: score += 1
        elif news.get("companyNewsScore", 0) < -0.2: score -= 1

        if news.get("sectorAverageBullishPercent", 0) > 0.5: score += 1
    except Exception as e:
        if DEBUG: st.warning(f"[{symbol}] News API error: {e}")

    try:
        earnings = requests.get(f"https://finnhub.io/api/v1/calendar/earnings?symbol={symbol}&token={FINNHUB_API_KEY}").json()
        for e in earnings.get("earningsCalendar", []):
            actual = float(e.get("epsActual", 0))
            estimate = float(e.get("epsEstimate", 0))
            if actual > estimate: score += 1
            elif actual < estimate: score -= 1
    except Exception as e:
        if DEBUG: st.warning(f"[{symbol}] Earnings API error: {e}")

    try:
        start = (datetime.today() - timedelta(days=14)).strftime("%Y-%m-%d")
        end = datetime.today().strftime("%Y-%m-%d")
        ipo = requests.get(f"https://finnhub.io/api/v1/calendar/ipo?from={start}&to={end}&token={FINNHUB_API_KEY}").json()
        for i in ipo.get("ipoCalendar", []):
            if i.get("symbol") == symbol: score += 1
    except Exception as e:
        if DEBUG: st.warning(f"[{symbol}] IPO API error: {e}")

    if get_macro_risk_score() > 6: score -= 1

    return score

# === Symbol Processor ===
@st.cache_data(ttl=300)
def process_symbol(symbol, label=None, is_macro=False, timeframe="1d"):
    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period="5d", interval=timeframe)

        if hist.empty:
            raise ValueError("No price history")

        price = hist["Close"][-1]
        volume = hist["Volume"][-1]

        info = ticker.fast_info
        float_shares = info.get("sharesOutstanding")

        if not float_shares:
            try:
                float_shares = ticker.info.get("floatShares")
            except:
                float_shares = None

        market_cap = info.get("marketCap")

        # Score only stocks, not global macros
        score = get_combined_score(symbol) if not is_macro else 0

        # Trend fallback: if no signal, infer from recent price move
        if score == 0:
            price_change = (hist["Close"][-1] - hist["Close"][-2]) / hist["Close"][-2]
            if price_change > 0.01: score += 1
            elif price_change < -0.01: score -= 1

        trend = "UPTREND" if score > 0 else "DOWNTREND" if score < 0 else "NEUTRAL"
        sentiment = "🟢 Bullish" if score > 0 else "🔴 Bearish" if score < 0 else "⚪ Neutral"

        return {
            "Symbol": label or symbol,
            "Price": f"${price:.2f}",
            "Volume": f"{volume/1e6:.2f}M",
            "Float": f"{float_shares/1e6:.2f}M" if float_shares else "—",
            "CAP": f"${market_cap/1e9:.2f}B" if market_cap else "N/A",
            "Score": f"+{score}" if score > 0 else str(score),
            "Trend": trend,
            "Sentiment": sentiment
        }

    except Exception as e:
        if DEBUG: st.error(f"[{symbol}] Error: {e}")
        return {
            "Symbol": label or symbol,
            "Price": "N/A", "Volume": "N/A", "Float": "N/A",
            "CAP": "N/A", "Score": "0", "Trend": "NEUTRAL", "Sentiment": "⚪ Neutral"
        }

# === Build DataFrames ===
stock_data = [process_symbol(sym, timeframe=timeframe) for sym in stock_list]
macro_data = [process_symbol(tick, label, True, timeframe) for label, tick in macro_symbols.items()]

stock_df = pd.DataFrame(stock_data).sort_values("Score", ascending=False)
macro_df = pd.DataFrame(macro_data).sort_values("Score", ascending=False)

# === Styling ===
def style_trend_cell(val):
    color_map = {"UPTREND": "#28a745", "DOWNTREND": "#dc3545", "NEUTRAL": "#6c757d"}
    return f"background-color: {color_map.get(val)}; color: white; font-weight: bold; text-align:center; border-radius: 4px; padding: 3px;"

def style_sentiment_cell(val):
    color_map = {
        "🟢 Bullish": "#28a745", "🔴 Bearish": "#dc3545", "⚪ Neutral": "#6c757d"
    }
    return f"background-color: {color_map.get(val)}; color: white; font-weight: bold; text-align:center; border-radius: 4px; padding: 3px;"

def style_df(df):
    return (df.style
            .applymap(style_trend_cell, subset=["Trend"])
            .applymap(style_sentiment_cell, subset=["Sentiment"])
            .set_properties(**{'text-align': 'center'})
            .set_table_styles([
                {'selector': 'th', 'props': [('text-align', 'center'), ('background-color', '#222'), ('color', '#ddd')]},
                {'selector': 'td', 'props': [('border', '1px solid #333'), ('padding', '6px 10px'), ('font-size', '14px')]}
            ])
    )

# === Layout Display ===
col1, col2 = st.columns([1, 1], gap="small")

with col1:
    st.markdown("### NASDAQ-100 Stocks")
    st.dataframe(style_df(stock_df), use_container_width=True)

with col2:
    st.markdown("### Global Market Symbols")
    st.dataframe(style_df(macro_df), use_container_width=True)
