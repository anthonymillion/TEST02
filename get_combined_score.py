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

# === Global Market Symbols ===
macro_symbols = {
    "DXY": "DXY", "USDJPY": "USDJPY=X", "XAUUSD": "XAUUSD=X", "EURUSD": "EURUSD=X",
    "USOIL": "CL=F", "USTECH100": "^NDX", "S&P500": "^GSPC", "BTCUSD": "BTC-USD",
    "ETHUSD": "ETH-USD", "RUSSEL2000": "^RUT", "NIKKEI": "^N225", "SILVER": "SI=F",
    "QQQ": "QQQ", "NATGAS": "NG=F", "COPPER": "HG=F", "BRENT": "BZ=F", "VIX": "^VIX", "BONDYIELD": "^TNX"
}

# === Streamlit Setup ===
st.set_page_config(layout="wide")
st.title("Sentiment Scanner")
st.sidebar.title("Settings")
timeframe = st.sidebar.selectbox("Timeframe", ["1m", "5m", "15m", "1h", "1d"])

# === Color-Coded Boxes ===
def styled_trend(trend):
    color = {"UPTREND": "#28a745", "DOWNTREND": "#dc3545", "NEUTRAL": "#6c757d"}.get(trend, "#6c757d")
    return f'<span style="background-color:{color};color:white;padding:3px 8px;border-radius:4px;font-weight:bold;">{trend}</span>'

def styled_sentiment(sentiment):
    color = {"🟢 Bullish": "#28a745", "🔴 Bearish": "#dc3545", "⚪ Neutral": "#6c757d"}.get(sentiment, "#6c757d")
    return f'<span style="background-color:{color};color:white;padding:3px 8px;border-radius:4px;font-weight:bold;">{sentiment}</span>'

# === Economic Risk Score ===
def get_macro_risk_score():
    try:
        url = f"https://api.tradingeconomics.com/calendar/country/united states?c={TRADING_ECON_USER}:{TRADING_ECON_KEY}"
        res = requests.get(url).json()
        red = sum(1 for e in res if e.get("importance") == 3)
        yellow = sum(1 for e in res if e.get("importance") == 2)
        return red + 0.5 * yellow
    except:
        return 0

# === Scoring Logic ===
def get_combined_score(symbol):
    score = 0
    try:
        news = requests.get(f"https://finnhub.io/api/v1/news-sentiment?symbol={symbol}&token={FINNHUB_API_KEY}").json()
        if news.get("companyNewsScore", 0) > 0.2: score += 1
        elif news.get("companyNewsScore", 0) < -0.2: score -= 1
        if news.get("sectorAverageBullishPercent", 0) > 0.5: score += 1
    except: pass

    try:
        earnings = requests.get(f"https://finnhub.io/api/v1/calendar/earnings?symbol={symbol}&token={FINNHUB_API_KEY}").json()
        for e in earnings.get("earningsCalendar", []):
            if float(e.get("epsActual", 0)) > float(e.get("epsEstimate", 0)): score += 1
            elif float(e.get("epsActual", 0)) < float(e.get("epsEstimate", 0)): score -= 1
    except: pass

    try:
        start = (datetime.today() - timedelta(days=14)).strftime("%Y-%m-%d")
        end = datetime.today().strftime("%Y-%m-%d")
        ipo = requests.get(f"https://finnhub.io/api/v1/calendar/ipo?from={start}&to={end}&token={FINNHUB_API_KEY}").json()
        for i in ipo.get("ipoCalendar", []):
            if i.get("symbol") == symbol: score += 1
    except: pass

    if get_macro_risk_score() > 6: score -= 1
    return score

# === Data Processor ===
def process_symbol(symbol, label=None, is_macro=False):
    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period="5d", interval=timeframe)
        if hist.empty: raise ValueError("No history")

        price = hist["Close"][-1]
        volume = hist["Volume"][-1]
        info = ticker.fast_info

        float_shares = info.get("sharesOutstanding")
        market_cap = info.get("marketCap")

        score = get_combined_score(symbol) if not is_macro else 0
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
    except:
        return {
            "Symbol": label or symbol,
            "Price": "N/A", "Volume": "N/A", "Float": "N/A",
            "CAP": "N/A", "Score": "0", "Trend": "NEUTRAL", "Sentiment": "⚪ Neutral"
        }

# === Build Tables ===
stock_data = [process_symbol(sym) for sym in stock_list]
stock_df = pd.DataFrame(stock_data).sort_values("Score", ascending=False)

macro_data = [process_symbol(tick, name, is_macro=True) for name, tick in macro_symbols.items()]
macro_df = pd.DataFrame(macro_data).sort_values("Score", ascending=False)

# === Format Columns ===
stock_df["Trend"] = stock_df["Trend"].apply(styled_trend)
stock_df["Sentiment"] = stock_df["Sentiment"].apply(styled_sentiment)
macro_df["Trend"] = macro_df["Trend"].apply(styled_trend)
macro_df["Sentiment"] = macro_df["Sentiment"].apply(styled_sentiment)

# === Styling ===
st.markdown("""
    <style>
    .dataframe th, .dataframe td {
        text-align: center !important;
        color: #ddd !important;
        background-color: #111 !important;
        border: 1px solid #333 !important;
        font-size: 14px !important;
    }
    .dataframe th {
        background-color: #222 !important;
        font-weight: bold;
    }
    .block-container {
        padding-top: 1rem !important;
        padding-bottom: 0rem !important;
    }
    .element-container:has(div[data-testid="column"]) {
        gap: 0px !important;
    }
    </style>
""", unsafe_allow_html=True)

# === Display Side-by-Side ===
col1, col2 = st.columns([1, 1], gap="small")

with col1:
    st.markdown("### NASDAQ-100 Stocks")
    st.write(stock_df.to_html(escape=False, index=False), unsafe_allow_html=True)

with col2:
    st.markdown("### Global Market Symbols")
    st.write(macro_df.to_html(escape=False, index=False), unsafe_allow_html=True)
