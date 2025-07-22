import streamlit as st
import pandas as pd
import yfinance as yf
import requests

# === API Keys ===
FINNHUB_API_KEY = "d1uv2rhr01qujmdeohv0d1uv2rhr01qujmdeohvg"

# === Full NASDAQ-100 Stock List ===
stock_list = [
    "NVDA", "MSFT", "AAPL", "AMZN", "GOOGL", "GOOG", "META", "TSLA", "AVGO", "COST", "AMD", "NFLX",
    "ABNB", "ADBE", "ADI", "ADP", "ADSK", "AEP", "AMAT", "AMGN", "APP", "ANSS", "ARM", "ASML", "AXON",
    "AZN", "BIIB", "BKNG", "BKR", "CCEP", "CDNS", "CDW", "CEG", "CHTR", "CMCSA", "CPRT", "CSGP", "CSCO",
    "CSX", "CTAS", "CTSH", "CRWD", "DASH", "DDOG", "DXCM", "EA", "EXC", "FAST", "FANG", "FTNT", "GEHC",
    "GILD", "GFS", "HON", "IDXX", "INTC", "INTU", "ISRG", "KDP", "KHC", "KLAC", "LIN", "LRCX", "LULU",
    "MAR", "MCHP", "MDLZ", "MELI", "MNST", "MRVL", "MSTR", "MU", "NXPI", "ODFL", "ON", "ORLY", "PANW",
    "PAYX", "PYPL", "PDD", "PEP", "PLTR", "QCOM", "REGN", "ROP", "ROST", "SHOP", "SBUX", "SNPS", "TTWO",
    "TMUS", "TXN", "TTD", "VRSK", "VRTX", "WBD", "WDAY", "XEL", "ZS"
]

# === Global Macro Symbols ===
macro_symbols = {
    "DXY": "DXY",
    "USDJPY": "USDJPY=X",
    "XAUUSD": "XAUUSD=X",
    "EURUSD": "EURUSD=X",
    "USOIL": "CL=F",
    "USTECH100": "^NDX",
    "S&P500": "^GSPC",
    "BTCUSD": "BTC-USD",
    "ETHUSD": "ETH-USD",
    "RUSSEL2000": "^RUT",
    "NIKKEI": "^N225",
    "SILVER": "SI=F",
    "QQQ": "QQQ",
    "NATGAS": "NG=F",
    "COPPER": "HG=F",
    "BRENT": "BZ=F",
    "VIX": "^VIX",
    "BONDYIELD": "^TNX"
}

# === Streamlit Setup ===
st.set_page_config(layout="wide")
st.sidebar.title("📊 Scanner Settings")
timeframe = st.sidebar.selectbox("Select Timeframe", ["1m", "5m", "15m", "1h", "1d"])
st.title("🧠 Multi-Sentiment Market Scanner (Live)")

# === Sentiment Function ===
def get_combined_score(symbol):
    score = 0
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
    return score

# === Build Table Rows ===
def process_symbol(symbol, label=None):
    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period="5d", interval=timeframe)
        info = ticker.info

        price = hist["Close"][-1] if not hist.empty else None
        volume = hist["Volume"][-1] if not hist.empty else None
        float_shares = info.get("floatShares", None)

        score = get_combined_score(symbol)
        sentiment = "🟢 Bullish" if score > 0 else "🔴 Bearish" if score < 0 else "⚪ Neutral"

        return {
            "Symbol": label or symbol,
            "Price": f"${price:.2f}" if price else "N/A",
            "Volume": f"{volume / 1e6:.2f}M" if volume else "N/A",
            "Float": f"{float_shares / 1e6:.2f}M" if float_shares else "N/A",
            "Score": f"+{score}" if score > 0 else str(score),
            "Sentiment": sentiment
        }
    except Exception as e:
        return {
            "Symbol": label or symbol,
            "Price": "Error",
            "Volume": "Error",
            "Float": "Error",
            "Score": "Error",
            "Sentiment": "❌"
        }

# === Main Table ===
rows = []

# Stocks
for sym in stock_list:
    st.write(f"Processing {sym}...")
    rows.append(process_symbol(sym))

# Macro symbols
for label, ticker in macro_symbols.items():
    st.write(f"Processing {label}...")
    rows.append(process_symbol(ticker, label))

# === Display Table ===
df = pd.DataFrame(rows)
df = df.sort_values("Score", ascending=False)
st.dataframe(df, use_container_width=True)
