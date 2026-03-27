import yfinance as yf
import pandas as pd
import numpy as np
import requests
import time
from datetime import datetime


# ---------- Fetch NIFTY 200 ----------
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


# ---------- Decision Engine ----------
def decide(rsi_val, macd_val, signal_val, price, ma20):

    score = 0

    # RSI
    if rsi_val < 35:
        score += 3
    elif rsi_val < 45:
        score += 2
    elif rsi_val < 60:
        score += 1
    elif rsi_val > 75:
        score -= 2

    # MACD
    if macd_val > signal_val:
        score += 2
    else:
        score -= 1

    # Trend
    if price > ma20:
        score += 2
    else:
        score -= 1

    # signal strength
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

    # timeframe
    if rsi_val < 50 and macd_val > signal_val:
        trade = "⚡ Intraday"
    elif 45 < rsi_val < 65:
        trade = "🔵 Swing"
    else:
        trade = "🟣 Long Term"

    return signal_txt, trade, score


# ---------- Safe Download ----------
def safe_download(stock):

    try:
        df = yf.download(
            stock,
            period="5d",
            interval="5m",
            progress=False,
            threads=False
        )

        if df is None or df.empty:
            return None

        return df

    except:
        return None


# ---------- Analyze ----------
def analyze(stock):

    df = safe_download(stock)

    if df is None or len(df) < 50:
        return None

    df['RSI'] = rsi(df)
    macd_val, signal = macd(df)

    # safe scalar extraction
    r = df['RSI'].iloc[-1].item()
    m = macd_val.iloc[-1].item()
    s = signal.iloc[-1].item()

    price = df['Close'].iloc[-1].item()
    ma20 = df['Close'].rolling(20).mean().iloc[-1].item()

    signal_txt, trade, score = decide(r, m, s, price, ma20)

    return stock, r, score, signal_txt, trade


# ---------- MAIN ----------
print("\nFetching NIFTY 200...")
stocks = get_nifty200()

print("Total stocks:", len(stocks))
print("Scan time:", datetime.now())
print()

results = []

for i, s in enumerate(stocks, 1):

    print(f"Scanning {i}/{len(stocks)} : {s}")

    try:
        res = analyze(s)

        if res:
            results.append(res)

    except Exception as e:
        print("Error:", s)

    time.sleep(0.25)


# sort best
results = sorted(results, key=lambda x: x[2], reverse=True)

print("\n==============================")
print("TRADE SUGGESTIONS")
print("==============================\n")

for r in results[:25]:
    print(
        f"{r[0]:15} | RSI:{r[1]:.1f} | Score:{r[2]} | {r[3]} | {r[4]}"
    )
