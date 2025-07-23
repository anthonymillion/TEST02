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
st.set_page_config(layout="wide", initial_sidebar_state="collapsed")
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

# === Combined Score & Driver ===
def get_combined_score(symbol):
    score = 0
    driver = "—"
    try:
        news = requests.get(f"https://finnhub.io/api/v1/news-sentiment?symbol={symbol}&token={FINNHUB_API_KEY}").json()
        comp_score = news.get("companyNewsScore", 0)
        sector_bull = news.get("sectorAverageBullishPercent", 0)
        if comp_score > 0.2:
            score += 1
            driver = "News"
        elif comp_score < -0.2:
            score -= 1
            driver = "News"
        if sector_bull > 0.5:
            score += 1
            if driver == "—":
                driver = "News"
    except: pass

    try:
        earnings = requests.get(f"https://finnhub.io/api/v1/calendar/earnings?symbol={symbol}&token={FINNHUB_API_KEY}").json()
        for e in earnings.get("earningsCalendar", []):
            eps_act = float(e.get("epsActual", 0))
            eps_est = float(e.get("epsEstimate", 0))
            if eps_act > eps_est:
                score += 1
                driver = "Earnings"
            elif eps_act < eps_est:
                score -= 1
                driver = "Earnings"
    except: pass

    try:
        start = (datetime.today() - timedelta(days=14)).strftime("%Y-%m-%d")
        end = datetime.today().strftime("%Y-%m-%d")
        ipo = requests.get(f"https://finnhub.io/api/v1/calendar/ipo?from={start}&to={end}&token={FINNHUB_API_KEY}").json()
        for i in ipo.get("ipoCalendar", []):
            if i.get("symbol") == symbol:
                score += 1
                if driver == "—":
                    driver = "IPO"
    except: pass

    if get_macro_risk_score() > 6:
        score -= 1
        if driver == "—":
            driver = "Macro Risk"

    return score, driver

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

        score, driver = (get_combined_score(symbol) if not is_macro else (0, "—"))
        trend = "UPTREND" if score > 0 else "DOWNTREND" if score < 0 else "NEUTRAL"
        sentiment = "🟢 Bullish" if score > 0 else "🔴 Bearish" if score < 0 else "⚪ Neutral"

        return {
            "Symbol": label or symbol,
            "Price": f"${price:.2f}",
            "Volume": f"{volume/1e6:.2f}M",
            "Float": f"{float_shares/1e6:.2f}M" if float_shares else "—",
            "CAP": f"${market_cap/1e9:.2f}B" if market_cap else "N/A",
            "Score": score,
            "Score_Display": f"+{score}" if score > 0 else str(score),
            "Trend": trend,
            "Sentiment": sentiment,
            "Driver": driver
        }
    except:
        return {
            "Symbol": label or symbol,
            "Price": "N/A", "Volume": "N/A", "Float": "N/A",
            "CAP": "N/A", "Score": 0, "Score_Display": "0",
            "Trend": "NEUTRAL", "Sentiment": "⚪ Neutral", "Driver": "—"
        }

# === Build DataFrames ===
stock_data = [process_symbol(sym) for sym in stock_list]
stock_df = pd.DataFrame(stock_data)
stock_df = stock_df.sort_values("Score", ascending=False)

macro_data = [process_symbol(tick, name, is_macro=True) for name, tick in macro_symbols.items()]
macro_df = pd.DataFrame(macro_data)
macro_df = macro_df.sort_values("Score", ascending=False)

# === Cell Styling ===
def style_symbol_cell(val):
    return "background-color: #a9a9a9; color: white; font-weight: bold; text-align:center; border-radius:4px; padding:5px;"

def style_price_cell(val):
    return "background-color: #90ee90; color: black; font-weight: bold; text-align:center; border-radius:4px; padding:5px;"

def style_volume_cell(val):
    return "background-color: #add8e6; color: black; font-weight: bold; text-align:center; border-radius:4px; padding:5px;"

def style_score_cell(val):
    return "background-color: #6495ed; color: white; font-weight: bold; text-align:center; border-radius:4px; padding:5px;"

def style_trend_cell(val):
    color_map = {"UPTREND": "#28a745", "DOWNTREND": "#dc3545", "NEUTRAL": "#6c757d"}
    color = color_map.get(val, "#6c757d")
    return f"background-color: {color}; color: white; font-weight: bold; text-align:center; border-radius:4px; padding:5px;"

def style_sentiment_cell(val):
    color_map = {"🟢 Bullish": "#28a745", "🔴 Bearish": "#dc3545", "⚪ Neutral": "#6c757d"}
    color = color_map.get(val, "#6c757d")
    return f"background-color: {color}; color: white; font-weight: bold; text-align:center; border-radius:4px; padding:5px;"

def style_driver_cell(val):
    return "background-color: #f0ad4e; color: black; font-weight: bold; text-align:center; border-radius:4px; padding:5px;"

def style_df(df):
    return (df.style
            .applymap(style_symbol_cell, subset=["Symbol"])
            .applymap(style_price_cell, subset=["Price"])
            .applymap(style_volume_cell, subset=["Volume"])
            .applymap(style_score_cell, subset=["Score_Display"])
            .applymap(style_trend_cell, subset=["Trend"])
            .applymap(style_sentiment_cell, subset=["Sentiment"])
            .applymap(style_driver_cell, subset=["Driver"])
            .hide(columns=["Score"])  # Hide numeric score column, show formatted instead
            .set_properties(**{'text-align': 'center'})
            .set_table_styles([
                {'selector': 'th', 'props': [('background-color', '#222'), ('color', '#ddd'), ('border', '2px solid #555')]},
                {'selector': 'td', 'props': [('border', '1px solid #444'), ('padding', '8px'), ('font-size', '14px')]},
                {'selector': 'table', 'props': [('border-collapse', 'collapse'), ('width', '100%'), ('border', '2px solid #555')]},
            ])
           )

# === Layout Display ===

st.markdown("### NASDAQ-100 Stocks")
st.dataframe(style_df(stock_df), use_container_width=True)

st.markdown("### Global Market Symbols")
st.dataframe(style_df(macro_df), use_container_width=True)
