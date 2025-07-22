import streamlit as st
import pandas as pd
import yfinance as yf
import requests

# === API Keys ===
FINNHUB_API_KEY = "d1uv2rhr01qujmdeohv0d1uv2rhr01qujmdeohvg"
TRADING_ECON_USER = "c88d1d122399451"
TRADING_ECON_KEY = "rdog9czpshn7zb9"

# === Stock List (NASDAQ-100) ===
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

# === Global Market Symbols (shown below stock rows) ===
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
st.title("🧠 Multi-Sentiment Market Scanner (Live)")
st.sidebar.title("Scanner Settings")
timeframe = st.sidebar.selectbox("Select Timeframe", ["1m", "5m", "15m", "1h", "1d"])

# === Macro Risk Scoring ===
def get_macro_risk_score():
    try:
        url = f"https://api.tradingeconomics.com/calendar/country/united states?c={TRADING_ECON_USER}:{TRADING_ECON_KEY}"
        res = requests.get(url).json()
        red = sum(1 for e in res if e.get("importance") == 3)
        yellow = sum(1 for e in res if e.get("importance") == 2)
        return red + 0.5 * yellow
    except:
        return 0

# === Combined Sentiment Score ===
def get_combined_score(symbol):
    score = 0
    try:
        # News sentiment
        news = requests.get(f"https://finnhub.io/api/v1/news-sentiment?symbol={symbol}&token={FINNHUB_API_KEY}").json()
        if news.get("companyNewsScore", 0) > 0.2: score += 1
        if news.get("companyNewsScore", 0) < -0.2: score -= 1
        if news.get("sectorAverageBullishPercent", 0) > 0.5: score += 1
    except: pass

    try:
        # Earnings sentiment
        earnings = requests.get(f"https://finnhub.io/api/v1/calendar/earnings?symbol={symbol}&token={FINNHUB_API_KEY}").json()
        for e in earnings.get("earningsCalendar", []):
            if float(e.get("epsActual", 0)) > float(e.get("epsEstimate", 0)): score += 1
            elif float(e.get("epsActual", 0)) < float(e.get("epsEstimate", 0)): score -= 1
    except: pass

    try:
        # IPO detection
        ipo = requests.get(f"https://finnhub.io/api/v1/calendar/ipo?from=2024-01-01&to=2025-12-31&token={FINNHUB_API_KEY}").json()
        for i in ipo.get("ipoCalendar", []):
            if i.get("symbol") == symbol:
                score += 1
    except: pass

    # Macro risk (high-impact economic events)
    macro_risk = get_macro_risk_score()
    if macro_risk > 6:
        score -= 1

    return score

# === Symbol Processing ===
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
    except:
        return {
            "Symbol": label or symbol, "Price": "Err", "Volume": "Err",
            "Float": "Err", "Score": "0", "Sentiment": "⚪"
        }

# === Build Final Table ===
rows = []

# First: Stocks
for sym in stock_list:
    rows.append(process_symbol(sym))

# Then: Macro symbols
for label, ticker in macro_symbols.items():
    rows.append(process_symbol(ticker, label))

# === Display Table ===
df = pd.DataFrame(rows)
df = df.sort_values("Score", ascending=False)
st.dataframe(df, use_container_width=True)
