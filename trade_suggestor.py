import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import requests
import time

st.set_page_config(layout="wide")

st.title("NIFTY 200 Smart Trade Scanner")
st.write("Based on RSI + MACD based Intraday / Swing / Long-term signals")


# ---------- Fetch NIFTY 200 ----------
@st.cache_data
def get_nifty200():

    url = "https://www.nseindia.com/api/equity-stockIndices?index=NIFTY%20200"

    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json"
    }

    session = requests.Session()
    session.get("https://www.nseindia.com", headers=headers)

    data = session.get(url, headers=headers).json()

    stocks = []

    for item in data['data']:
        symbol = item['symbol']
        if symbol and "NIFTY" not in symbol:
            stocks.append(symbol + ".NS")

    return stocks


# ---------- RSI ----------
def rsi(data, period=14):

    delta = data['Close'].diff()

    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.rolling(period).mean()
    avg_loss = loss.rolling(period).mean()

    rs = avg_gain / avg_loss

    return 100 - (100 / (1 + rs))


# ---------- MACD ----------
def macd(data):

    e1 = data['Close'].ewm(span=12, adjust=False).mean()
    e2 = data['Close'].ewm(span=26, adjust=False).mean()

    macd = e1 - e2
    signal = macd.ewm(span=9, adjust=False).mean()

    return macd, signal


# ---------- Decision ----------
def decide(rsi_val, macd_val, signal_val, price, ma20):

    score = 0

    if rsi_val < 35:
        score += 3
    elif rsi_val < 45:
        score += 2
    elif rsi_val < 60:
        score += 1
    elif rsi_val > 75:
        score -= 2

    if macd_val > signal_val:
        score += 2
    else:
        score -= 1

    if price > ma20:
        score += 2
    else:
        score -= 1

    if score >= 6:
        signal_txt = "🟢 STRONG BUY"
    elif score >= 4:
        signal_txt = "🟢 MODERATE BUY"
    elif score >= 2:
        signal_txt = "🟡 SLIGHT BUY"
    elif score <= -1:
        signal_txt = "🔴 SELL"
    else:
        signal_txt = "⚪ HOLD"

    if rsi_val < 50 and macd_val > signal_val:
        trade = "⚡ Intraday"
    elif 45 < rsi_val < 65:
        trade = "🔵 Swing"
    else:
        trade = "🟣 Long Term"

    return signal_txt, trade, score


# ---------- Analyze ----------
def analyze(stock):

    try:
        df = yf.download(
            stock,
            period="5d",
            interval="5m",
            progress=False,
            threads=False
        )

        if df is None or len(df) < 50:
            return None

        df['RSI'] = rsi(df)
        macd_val, signal = macd(df)

        r = df['RSI'].iloc[-1].item()
        m = macd_val.iloc[-1].item()
        s = signal.iloc[-1].item()

        price = df['Close'].iloc[-1].item()
        ma20 = df['Close'].rolling(20).mean().iloc[-1].item()

        signal_txt, trade, score = decide(r, m, s, price, ma20)

        return [stock, r, score, signal_txt, trade]

    except:
        return None


# ---------- UI ----------
if st.button("Run NIFTY 200 Scan"):

    stocks = get_nifty200()

    progress = st.progress(0)
    status = st.empty()

    results = []

    total = len(stocks)

    for i, s in enumerate(stocks):

        status.text(f"Scanning {i+1}/{total} : {s}")
        progress.progress((i+1)/total)

        res = analyze(s)

        if res:
            results.append(res)

        time.sleep(0.05)

    df = pd.DataFrame(
        results,
        columns=["Stock","RSI","Score","Signal","Trade Type"]
    )

    df = df.sort_values("Score", ascending=False)

    st.success("Scan complete")

    st.dataframe(df, use_container_width=True)
