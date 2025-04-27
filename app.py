import streamlit as st
import pandas as pd
import requests
import numpy as np

# إعداد صفحة التطبيق
st.set_page_config(page_title="Crypto Analyzer", layout="wide")

# عنوان التطبيق
st.title("Crypto Analyzer - Spot and Futures")

# اختيار نوع السوق
market_type = st.radio("Select Market Type:", ["Spot", "Futures"])

# إدخال رمز العملة
symbol = st.text_input("Enter Symbol (example: BTCUSDT):", value="BTCUSDT").upper()

# اختيار فريم الزمن
timeframes = ["1m", "5m", "15m", "30m", "1h", "2h", "4h", "6h", "12h", "1d", "1w"]
selected_timeframes = st.multiselect("Select Timeframes to Analyze:", timeframes, default=["5m", "15m", "1h", "4h", "1d"])

# زر البدء
start_button = st.button("Start Analysis")

# دالة جلب بيانات السعر من Binance Public API (بدون مفتاح API)
def fetch_candles(symbol, interval, limit=100):
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
    response = requests.get(url)
    data = response.json()

    df = pd.DataFrame(data, columns=[
        "time", "open", "high", "low", "close", "volume",
        "close_time", "qav", "trades", "tbbav", "tbqav", "ignore"
    ])
    df["time"] = pd.to_datetime(df["time"], unit="ms")
    df[["open", "high", "low", "close", "volume"]] = df[["open", "high", "low", "close", "volume"]].astype(float)
    return df

# دالة حساب RSI
def compute_rsi(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

# دالة حساب MACD
def compute_macd(series, fast=12, slow=26, signal=9):
    exp1 = series.ewm(span=fast, adjust=False).mean()
    exp2 = series.ewm(span=slow, adjust=False).mean()
    macd = exp1 - exp2
    signal_line = macd.ewm(span=signal, adjust=False).mean()
    hist = macd - signal_line
    return macd, signal_line, hist

# دالة حساب EMA
def compute_ema(series, period=20):
    return series.ewm(span=period, adjust=False).mean()
    
    # دالة تحليل لكل فريم
def analyze_single_timeframe(symbol, timeframe):
    df = fetch_candles(symbol, timeframe)

    if df.empty or len(df) < 50:
        return None

    close = df["close"]

    rsi = compute_rsi(close)
    macd, macd_signal, macd_hist = compute_macd(close)
    ema20 = compute_ema(close, period=20)
    ema50 = compute_ema(close, period=50)

    last_close = close.iloc[-1]
    last_rsi = rsi.iloc[-1]
    last_macd_hist = macd_hist.iloc[-1]
    last_ema20 = ema20.iloc[-1]
    last_ema50 = ema50.iloc[-1]

    atr = (df["high"] - df["low"]).rolling(window=14).mean().iloc[-1]

    # تحديد الإشارة بناء على المؤشرات
    if last_ema20 > last_ema50 and last_macd_hist > 0 and last_rsi > 50:
        signal = "Buy"
        tp1 = last_close + atr * 1.5
        tp2 = last_close + atr * 2
        tp3 = last_close + atr * 3
        sl = last_close - atr
    elif last_ema20 < last_ema50 and last_macd_hist < 0 and last_rsi < 50:
        signal = "Sell"
        tp1 = last_close - atr * 1.5
        tp2 = last_close - atr * 2
        tp3 = last_close - atr * 3
        sl = last_close + atr
    else:
        signal = "Neutral"
        tp1 = tp2 = tp3 = sl = None

    return {
        "timeframe": timeframe,
        "signal": signal,
        "price": round(last_close, 4),
        "tp1": round(tp1, 4) if tp1 else None,
        "tp2": round(tp2, 4) if tp2 else None,
        "tp3": round(tp3, 4) if tp3 else None,
        "sl": round(sl, 4) if sl else None,
        "rsi": round(last_rsi, 2),
        "ema20": round(last_ema20, 4),
        "ema50": round(last_ema50, 4),
        "macd_hist": round(last_macd_hist, 4)
    }
    
    # عرض النتائج بعد الضغط على زر التحليل
if start_button:
    if not symbol or not selected_timeframes:
        st.error("Please enter a symbol and select at least one timeframe.")
    else:
        st.subheader(f"Analysis Results for {symbol} - {market_type}")

        analysis_results = []

        for tf in selected_timeframes:
            result = analyze_single_timeframe(symbol, tf)
            if result:
                analysis_results.append(result)

        if analysis_results:
            df_results = pd.DataFrame(analysis_results)

            # عرض النتائج بتفصيل
            st.dataframe(df_results)

            # حساب النسبة المئوية لكل إشارة
            buy_count = sum(df['signal'] == "Buy" for _, df in df_results.iterrows())
            sell_count = sum(df['signal'] == "Sell" for _, df in df_results.iterrows())
            neutral_count = sum(df['signal'] == "Neutral" for _, df in df_results.iterrows())

            total = len(df_results)
            buy_pct = (buy_count / total) * 100
            sell_pct = (sell_count / total) * 100
            neutral_pct = (neutral_count / total) * 100

            st.subheader("Multi-Timeframe Summary")
            st.write(f"✅ Buy Signals: {buy_pct:.2f}% ({buy_count}/{total})")
            st.write(f"❌ Sell Signals: {sell_pct:.2f}% ({sell_count}/{total})")
            st.write(f"⚪ Neutral Signals: {neutral_pct:.2f}% ({neutral_count}/{total})")

            # تحديد الإشارة العامة
            if buy_pct > 70:
                st.success("Overall Market Signal: STRONG BUY ✅")
            elif sell_pct > 70:
                st.error("Overall Market Signal: STRONG SELL ❌")
            else:
                st.warning("Overall Market Signal: MIXED ⚪")

        else:
            st.error("No data available to analyze!")