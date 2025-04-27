import streamlit as st
import pandas as pd
import requests
from datetime import datetime

# إعداد الصفحة
st.set_page_config(page_title="Crypto Analyzer Pro X")

# اختيار اللغة
lang = st.selectbox("Language / اللغة", ["English", "العربية"])

# الترجمة حسب اللغة المختارة
TXT = {
    "English": {
        "title": "Crypto Analyzer Pro X",
        "mode": "Trading Mode",
        "symbol": "Symbol (e.g., BTCUSDT)",
        "interval": "Timeframe",
        "lookback": "Candles to Analyze",
        "capital": "Available Capital (USD)",
        "leverage": "Leverage (Futures only)",
        "analyze": "Start Analysis",
        "results": "Analysis Results",
        "signal": "Signal",
        "price": "Current Price",
        "sl": "Stop Loss",
        "tp": "Take Profit Targets",
        "rsi": "RSI",
        "risk": "Auto Risk Level",
        "score": "Trade Score",
        "chart": "Price Chart",
    },
    "العربية": {
        "title": "أداة التحليل الاحترافية للعملات الرقمية",
        "mode": "نوع التداول",
        "symbol": "رمز العملة (مثلاً BTCUSDT)",
        "interval": "الإطار الزمني",
        "lookback": "عدد الشموع للتحليل",
        "capital": "رأس المال المتاح (دولار)",
        "leverage": "الرافعة المالية (للفيوتشر فقط)",
        "analyze": "ابدأ التحليل",
        "results": "نتائج التحليل",
        "signal": "الإشارة",
        "price": "السعر الحالي",
        "sl": "وقف الخسارة",
        "tp": "أهداف الربح",
        "rsi": "RSI",
        "risk": "نسبة المخاطرة الذكية",
        "score": "تقييم الصفقة",
        "chart": "الرسم البياني",
    }
}[lang]

# عنوان الصفحة
st.title(TXT["title"])
# اختيار نوع التداول، العملات، الإطار الزمني، عدد الشموع، رأس المال، الرافعة
mode = st.radio(TXT["mode"], ["Spot", "Futures"])
symbols = st.text_input(TXT["symbol"], "BTCUSDT,ETHUSDT,BNBUSDT").upper().split(",")
interval = st.selectbox(TXT["interval"], [
    "1m", "3m", "5m", "15m", "30m",
    "1h", "2h", "4h", "6h", "12h",
    "1d", "3d", "1w"
])
lookback = st.slider(TXT["lookback"], 50, 500, 100)
capital = st.number_input(TXT["capital"], min_value=10.0, value=100.0, step=10.0)
leverage = st.selectbox(TXT["leverage"], [1, 2, 5, 10, 20, 50], index=2 if mode == "Futures" else 0)
# تحميل بيانات العملة
def fetch_data(symbol, interval, limit):
    try:
        url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
        response = requests.get(url, timeout=10)  # مهلة الانتظار 10 ثواني
        response.raise_for_status()  # لو في خطأ HTTP يعطي خطأ واضح
        data = response.json()

        # تحقق إذا البيانات قليلة أو فاضية
        if not data or len(data) < max(10, limit * 0.5):
            raise Exception("Not enough candles returned from Binance API.")

        # تجهيز الداتا فريم
        df = pd.DataFrame(data, columns=["time", "open", "high", "low", "close", "volume",
                                         "close_time", "qav", "trades", "tbbav", "tbqav", "ignore"])
        df["time"] = pd.to_datetime(df["time"], unit="ms")
        df[["open", "high", "low", "close", "volume"]] = df[["open", "high", "low", "close", "volume"]].astype(float)
        return df

    except Exception as e:
        st.error(f"Error fetching data for {symbol}: {e}")
        return pd.DataFrame()
# حساب المؤشرات الفنية
def compute_rsi(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0).rolling(window=period).mean()
    loss = (-delta.clip(upper=0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def compute_indicators(df):
    df["EMA20"] = df["close"].ewm(span=20).mean()
    df["EMA50"] = df["close"].ewm(span=50).mean()
    df["EMA200"] = df["close"].ewm(span=200).mean()
    df["RSI"] = compute_rsi(df["close"])
    df["ATR"] = (df["high"] - df["low"]).rolling(window=14).mean()
    macd_line = df["close"].ewm(span=12).mean() - df["close"].ewm(span=26).mean()
    signal_line = macd_line.ewm(span=9).mean()
    df["MACD_Hist"] = macd_line - signal_line
    bb_std = df["close"].rolling(window=20).std()
    df["BB_upper"] = df["EMA20"] + 2 * bb_std
    df["BB_lower"] = df["EMA20"] - 2 * bb_std
    return df
# كشف Price Action
def detect_price_action(df):
    last = df.iloc[-1]
    previous = df.iloc[-2]
    if last["close"] > last["open"] and previous["close"] < previous["open"] and last["close"] > previous["open"] and last["open"] < previous["close"]:
        return "Bullish Engulfing"
    elif last["close"] < last["open"] and previous["close"] > previous["open"] and last["open"] > previous["close"] and last["close"] < previous["open"]:
        return "Bearish Engulfing"
    elif (last["high"] - last["low"]) > 3 * abs(last["close"] - last["open"]) and (last["close"] - last["low"]) / (last["high"] - last["low"]) > 0.6:
        return "Hammer"
    elif abs(last["close"] - last["open"]) < (last["high"] - last["low"]) * 0.1:
        return "Doji"
    return "None"
# تحليل العملة وتوليد الإشارة
def analyze(symbol):
    df = fetch_data(symbol, interval, lookback)
    if df.empty or len(df) < 20:  
        raise Exception("Not enough data to analyze")
    
    df = compute_indicators(df)
    last = df.iloc[-1]

    signal = "Hold"
    if last["EMA20"] > last["EMA50"] and last["RSI"] < 70:
        signal = "Buy ✅"
    elif last["EMA20"] < last["EMA50"] and last["RSI"] > 30:
        signal = "Sell ❌"

    pa = detect_price_action(df)

    sl = last["close"] - last["ATR"] if signal == "Buy ✅" else last["close"] + last["ATR"]

    if signal == "Sell ❌":
        tp1 = last["close"] - last["ATR"] * 1.5
        tp2 = last["close"] - last["ATR"] * 2
        tp3 = last["close"] - last["ATR"] * 3
    else:
        tp1 = last["close"] + last["ATR"] * 1.5
        tp2 = last["close"] + last["ATR"] * 2
        tp3 = last["close"] + last["ATR"] * 3

    rr_ratio = abs((tp1 - last["close"]) / (last["close"] - sl))
    auto_risk = min(max(rr_ratio / 4, 0.01), 0.05) * 100

    trade_score = 50
    if pa != "None":
        trade_score += 20
    if last["MACD_Hist"] > 0:
        trade_score += 15
    if (signal == "Buy ✅" and last["close"] > last["BB_upper"]) or (signal == "Sell ❌" and last["close"] < last["BB_lower"]):
        trade_score += 15

    return {
        "symbol": symbol,
        "signal": signal,
        "price": last["close"],
        "sl": sl,
        "tp1": tp1,
        "tp2": tp2,
        "tp3": tp3,
        "rsi": last["RSI"],
        "pa": pa,
        "risk_pct": auto_risk,
        "score": min(trade_score, 100)
    }, df
# زر التحليل وعرض النتائج
if st.button(TXT["analyze"]):
    results = []
    for sym in symbols:
        try:
            result, df = analyze(sym)
            results.append(result)

            if result["signal"] != "Hold":
                st.subheader(result["symbol"])
                st.success(f"{TXT['signal']}: {result['signal']} - {TXT['score']}: {result['score']}%")
                st.write(f"{TXT['price']}: {round(result['price'], 4)}")
                st.write(f"{TXT['sl']}: {round(result['sl'], 4)}")
                st.write(f"{TXT['tp']}:")
                st.write(f"• TP1: {round(result['tp1'], 4)}")
                st.write(f"• TP2: {round(result['tp2'], 4)}")
                st.write(f"• TP3: {round(result['tp3'], 4)}")
                st.write(f"{TXT['rsi']}: {round(result['rsi'], 2)}")
                st.write(f"{TXT['risk']}: {round(result['risk_pct'], 2)}%")
                st.write(f"Price Action: {result['pa']}")
                st.line_chart(df.set_index("time")[["close", "EMA20", "EMA50"]])

        except Exception as e:
            st.error(f"Error analyzing {sym}: {e}")

    # عرض جدول تلخيصي لكل العملات
    if results:
        df_results = pd.DataFrame(results)
        st.subheader("Summary Table")
        st.dataframe(df_results)
