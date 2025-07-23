import streamlit as st
import pandas as pd
import yfinance as yf
import requests
import io
from datetime import datetime, timedelta

# === API KEYS ===
FINNHUB_API_KEY = "d1uv2rhr01qujmdeohv0d1uv2rhr01qujmdeohvg"
TRADING_ECON_USER = "c88d1d122399451"
TRADING_ECON_KEY = "rdog9czpshn7zb9"

# === STOCKS & GLOBAL SYMBOLS ===
stock_list = ["NVDA", "MSFT", "AAPL", "AMZN", "GOOGL", "META", "TSLA", "NFLX"]
macro_symbols = {
    "DXY": "DXY", "USDJPY": "USDJPY=X", "XAUUSD": "XAUUSD=X", "EURUSD": "EURUSD=X",
    "USOIL": "CL=F", "S&P500": "^GSPC", "BTCUSD": "BTC-USD", "ETHUSD": "ETH-USD",
    "NATGAS": "NG=F", "SILVER": "SI=F", "COPPER": "HG=F", "BRENT": "BZ=F"
}

# === COT LABEL MAP ===
cot_name_map = {
    "DXY": "U.S. Dollar Index", "USDJPY=X": "Japanese Yen", "XAUUSD=X": "Gold",
    "EURUSD=X": "Euro FX", "CL=F": "Crude Oil", "NG=F": "Natural Gas",
    "SI=F": "Silver", "HG=F": "Copper", "BZ=F": "Brent Crude Oil"
}

# === STREAMLIT SETUP ===
st.set_page_config(layout="wide")
st.title("📊 Sentiment Scanner with COT Integration")
st.sidebar.title("⚙️ Settings")
timeframe = st.sidebar.selectbox("⏱ Timeframe", ["1m", "5m", "15m", "1h", "1d"])

# === FETCH COT DATA ===
@st.cache_data(ttl=7 * 24 * 3600)
def fetch_cot_data():
    url = https://www.cftc.gov/files/dea/futures/deacotdisagg.csv

    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        res = requests.get(url, headers=headers)
        res.raise_for_status()
        df = pd.read_csv(io.StringIO(res.text), skiprows=7)
        df["Report_Date_as_MM_DD_YYYY"] = pd.to_datetime(df["Report_Date_as_MM_DD_YYYY"])
        return df
    except Exception as e:
        st.error(f"Error fetching COT data: {e}")
        return pd.DataFrame()

cot_df = fetch_cot_data()

def get_latest_cot(symbol_name):
    if cot_df.empty: return None
    subset = cot_df[cot_df["Market_and_Exchange_Names"].str.contains(symbol_name, case=False, na=False)]
    if subset.empty: return None
    latest = subset[subset["Report_Date_as_MM_DD_YYYY"] == subset["Report_Date_as_MM_DD_YYYY"].max()]
    return latest.iloc[0] if not latest.empty else None

# === RISK SCORE ===
def get_macro_risk_score():
    try:
        url = f"https://api.tradingeconomics.com/calendar/country/united states?c={TRADING_ECON_USER}:{TRADING_ECON_KEY}"
        res = requests.get(url).json()
        red = sum(1 for e in res if e.get("importance") == 3)
        yellow = sum(1 for e in res if e.get("importance") == 2)
        return red + 0.5 * yellow
    except:
        return 0

# === COMBINED SCORE ===
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

    cot_key = cot_name_map.get(symbol)
    if cot_key:
        cot = get_latest_cot(cot_key)
        if cot is not None:
            try:
                net = cot["Noncommercial_Long_All"] - cot["Noncommercial_Short_All"]
                open_interest = cot["Open_Interest"]
                ratio = net / open_interest if open_interest else 0
                if ratio > 0.1: score += 1
                elif ratio < -0.1: score -= 1
            except: pass

    return score

# === SYMBOL PROCESSING ===
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

# === STYLES ===
def style_trend_cell(val):
    color_map = {"UPTREND": "#28a745", "DOWNTREND": "#dc3545", "NEUTRAL": "#6c757d"}
    return f"background-color:{color_map.get(val, '#6c757d')};color:white;font-weight:bold;text-align:center;"

def style_sentiment_cell(val):
    color_map = {"🟢 Bullish": "#28a745", "🔴 Bearish": "#dc3545", "⚪ Neutral": "#6c757d"}
    return f"background-color:{color_map.get(val, '#6c757d')};color:white;font-weight:bold;text-align:center;"

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

# === BUILD TABLES ===
stock_data = [process_symbol(s) for s in stock_list]
macro_data = [process_symbol(t, label, is_macro=True) for label, t in macro_symbols.items()]

stock_df = pd.DataFrame(stock_data).sort_values("Score", ascending=False)
macro_df = pd.DataFrame(macro_data).sort_values("Score", ascending=False)

# === LAYOUT ===
col1, col2 = st.columns([1, 1], gap="small")
with col1:
    st.markdown("### 📈 NASDAQ Stocks")
    st.dataframe(style_df(stock_df), use_container_width=True)
with col2:
    st.markdown("### 🌍 Global Market Symbols")
    st.dataframe(style_df(macro_df), use_container_width=True)
