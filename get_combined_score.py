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

# === Macro Risk Score ===
def get_macro_risk_score():
    try:
        url = f"https://api.tradingeconomics.com/calendar/country/united states?c={TRADING_ECON_USER}:{TRADING_ECON_KEY}"
        res = requests.get(url).json()
        red = sum(1 for e in res if e.get("importance") == 3)
        yellow = sum(1 for e in res if e.get("importance") == 2)
        return red + 0.5 * yellow
    except:
        return 0

# === Combined Score ===
def get_combined_score(symbol):
    score = 0
    source = []
    try:
        news = requests.get(f"https://finnhub.io/api/v1/news-sentiment?symbol={symbol}&token={FINNHUB_API_KEY}").json()
        if news.get("companyNewsScore", 0) > 0.2:
            score += 1
            source.append("News")
        elif news.get("companyNewsScore", 0) < -0.2:
            score -= 1
            source.append("News")
        if news.get("sectorAverageBullishPercent", 0) > 0.5:
            score += 1
            source.append("News")
    except: pass

    try:
        earnings = requests.get(f"https://finnhub.io/api/v1/calendar/earnings?symbol={symbol}&token={FINNHUB_API_KEY}").json()
        for e in earnings.get("earningsCalendar", []):
            if float(e.get("epsActual", 0)) > float(e.get("epsEstimate", 0)):
                score += 1
                source.append("Earnings")
            elif float(e.get("epsActual", 0)) < float(e.get("epsEstimate", 0)):
                score -= 1
                source.append("Earnings")
    except: pass

    try:
        start = (datetime.today() - timedelta(days=14)).strftime("%Y-%m-%d")
        end = datetime.today().strftime("%Y-%m-%d")
        ipo = requests.get(f"https://finnhub.io/api/v1/calendar/ipo?from={start}&to={end}&token={FINNHUB_API_KEY}").json()
        for i in ipo.get("ipoCalendar", []):
            if i.get("symbol") == symbol:
                score += 1
                source.append("IPO")
    except: pass

    try:
        ticker = yf.Ticker(symbol)
        opt = ticker.option_chain()
        calls = opt.calls["openInterest"].sum()
        puts = opt.puts["openInterest"].sum()
        if calls > puts * 1.2:
            score += 1
            source.append("Options")
        elif puts > calls * 1.2:
            score -= 1
            source.append("Options")
    except: pass

    if get_macro_risk_score() > 6:
        score -= 1
        source.append("Macro")

    return score, ", ".join(sorted(set(source)))

# === Symbol Data Processor ===
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

        score, drivers = get_combined_score(symbol) if not is_macro else (0, "")
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
            "Sentiment": sentiment,
            "Driver": drivers if drivers else "—"
        }
    except:
        return {
            "Symbol": label or symbol,
            "Price": "N/A", "Volume": "N/A", "Float": "N/A",
            "CAP": "N/A", "Score": "0", "Trend": "NEUTRAL", "Sentiment": "⚪ Neutral", "Driver": "—"
        }

# === Cell Styling ===
def style_trend_cell(val):
    color_map = {"UPTREND": "#28a745", "DOWNTREND": "#dc3545", "NEUTRAL": "#6c757d"}
    color = color_map.get(val, "#6c757d")
    return f"background-color: {color}; color: white; font-weight: bold; text-align:center; border-radius: 4px; padding: 3px;"

def style_sentiment_cell(val):
    color_map = {
        "🟢 Bullish": "#28a745",
        "🔴 Bearish": "#dc3545",
        "⚪ Neutral": "#6c757d"
    }
    color = color_map.get(val, "#6c757d")
    return f"background-color: {color}; color: white; font-weight: bold; text-align:center; border-radius: 4px; padding: 3px;"

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
stock_data = [process_symbol(sym) for sym in stock_list]
macro_data = [process_symbol(tick, name, is_macro=True) for name, tick in macro_symbols.items()]

stock_df = pd.DataFrame(stock_data).sort_values("Score", ascending=False)
macro_df = pd.DataFrame(macro_data).sort_values("Score", ascending=False)

col1, col2 = st.columns([1, 1], gap="small")

with col1:
    st.markdown("### NASDAQ-100 Stocks")
    st.dataframe(style_df(stock_df), use_container_width=True)

with col2:
    st.markdown("### Global Market Symbols")
    st.dataframe(style_df(macro_df), use_container_width=True)
