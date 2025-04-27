import streamlit as st
import pandas as pd
import requests

# إعدادات الصفحة
st.set_page_config(page_title="Crypto Analyzer", layout="wide")

# اختيار اللغة
language = st.radio("Select Language / اختر اللغة:", ("English", "العربية"))

# ترجمة النصوص بناءً على اللغة
TXT = {
    "symbol": "Enter Symbol (e.g., BTCUSDT):" if language == "English" else "ادخل رمز العملة (مثلا BTCUSDT):",
    "mode": "Select Mode:" if language == "English" else "اختر نوع التداول:",
    "interval": "Select Interval:" if language == "English" else "اختر الفاصل الزمني:",
    "lookback": "Number of Candles:" if language == "English" else "عدد الشموع:",
    "capital": "Enter Capital ($):" if language == "English" else "ادخل رأس المال ($):",
    "leverage": "Select Leverage:" if language == "English" else "اختر الرافعة المالية:",
    "analyze": "Analyze" if language == "English" else "تحليل",
    "multi": "Analyze All Timeframes" if language == "English" else "تحليل جميع الفريمات",
    "signal": "Signal" if language == "English" else "الإشارة",
    "price": "Price" if language == "English" else "السعر",
    "sl": "Stop Loss" if language == "English" else "وقف الخسارة",
    "tp": "Take Profit Targets" if language == "English" else "أهداف الأرباح",
    "rsi": "RSI" if language == "English" else "مؤشر القوة النسبية",
    "risk": "Smart Risk %" if language == "English" else "نسبة المخاطرة الذكية",
    "score": "Trade Score" if language == "English" else "درجة جودة الصفقة",
    "summary": "Summary Table" if language == "English" else "جدول الملخص"
}

# خيارات التداول
mode = st.radio(TXT["mode"], ["Spot", "Futures"])
symbols = st.text_input(TXT["symbol"], "BTCUSDT").upper().split(",")
interval = st.selectbox(TXT["interval"], [
    "1m", "3m", "5m", "15m", "30m", "1h", "2h", "4h", "6h", "12h", "1d", "3d", "1w"
])
lookback = st.slider(TXT["lookback"], 50, 500, 100)
capital = st.number_input(TXT["capital"], min_value=10.0, value=100.0, step=10.0)
leverage = st.selectbox(TXT["leverage"], [1, 2, 5, 10, 20, 50], index=2 if mode == "Futures" else 0)

# دالة تحميل البيانات من Binance
def fetch_data(symbol, interval, limit):
    try:
        api_key = st.secrets["BINANCE_API_KEY"]
        headers = {
            "X-MBX-APIKEY": api_key,
            "Accept": "application/json"
        }
        url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()

        if not data or len(data) < max(10, limit * 0.5):
            raise Exception("Not enough candles returned from Binance API.")

        df = pd.DataFrame(data, columns=[
            "time", "open", "high", "low", "close", "volume",
            "close_time", "qav", "trades", "tbbav", "tbqav", "ignore"
        ])
        df["time"] = pd.to_datetime(df["time"], unit="ms")
        df[["open", "high", "low", "close", "volume"]] = df[["open", "high", "low", "close", "volume"]].astype(float)
        return df
    except Exception as e:
        st.error(f"Error fetching data for {symbol}: {e}")
        return pd.DataFrame()

# مؤشرات فنية
def compute_indicators(df):
    df["EMA20"] = df["close"].ewm(span=20, adjust=False).mean()
    df["EMA50"] = df["close"].ewm(span=50, adjust=False).mean()
    df["RSI"] = compute_rsi(df["close"], 14)
    df["ATR"] = compute_atr(df, 14)
    df["MACD"], df["MACD_Signal"], df["MACD_Hist"] = compute_macd(df["close"])
    return df

def compute_rsi(series, period):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def compute_atr(df, period):
    high_low = df['high'] - df['low']
    high_close = abs(df['high'] - df['close'].shift())
    low_close = abs(df['low'] - df['close'].shift())
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = ranges.max(axis=1)
    atr = true_range.rolling(window=period).mean()
    return atr

def compute_macd(series, fast=12, slow=26, signal=9):
    exp1 = series.ewm(span=fast, adjust=False).mean()
    exp2 = series.ewm(span=slow, adjust=False).mean()
    macd = exp1 - exp2
    signal_line = macd.ewm(span=signal, adjust=False).mean()
    hist = macd - signal_line
    return macd, signal_line, hist

# كشف الشموع المهمة
def detect_price_action(df):
    last = df.iloc[-1]
    previous = df.iloc[-2]
    if (last["close"] > last["open"] and previous["close"] < previous["open"]
        and last["close"] > previous["open"] and last["open"] < previous["close"]
        and last["volume"] > previous["volume"]):
        return "Bullish Engulfing"
    elif (last["close"] < last["open"] and previous["close"] > previous["open"]
        and last["open"] > previous["close"] and last["close"] < previous["open"]
        and last["volume"] > previous["volume"]):
        return "Bearish Engulfing"
    elif (last["high"] - last["low"]) > 3 * abs(last["close"] - last["open"]) and \
         (last["close"] - last["low"]) / (last["high"] - last["low"]) > 0.6:
        return "Hammer"
    elif abs(last["close"] - last["open"]) <= (last["high"] - last["low"]) * 0.1:
        return "Doji"
    return "None"
    
    # دالة تحليل صفقة واحدة
def analyze(symbol):
    df = fetch_data(symbol, interval, lookback)
    if df.empty or len(df) < 20:
        raise Exception("Not enough data to analyze")

    df = compute_indicators(df)
    last = df.iloc[-1]

    signal = "Hold"
    if last["EMA20"] > last["EMA50"] and last["RSI"] > 40 and last["MACD_Hist"] > 0:
        signal = "Buy ✅"
    elif last["EMA20"] < last["EMA50"] and last["RSI"] < 60 and last["MACD_Hist"] < 0:
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
    if (signal == "Buy ✅" and last["close"] > last["EMA20"]) or (signal == "Sell ❌" and last["close"] < last["EMA20"]):
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

# دالة تحليل جميع الفريمات الزمنية
def analyze_all_timeframes(symbol):
    timeframes = [
        "1m", "3m", "5m", "15m", "30m",
        "1h", "2h", "4h", "6h", "12h",
        "1d", "3d", "1w"
    ]

    buy_frames = []
    sell_frames = []
    hold_frames = []

    for tf in timeframes:
        try:
            df = fetch_data(symbol, tf, 100)
            if df.empty or len(df) < 20:
                hold_frames.append(tf)
                continue

            df = compute_indicators(df)
            last = df.iloc[-1]

            signal = "Hold"
            if last["EMA20"] > last["EMA50"] and last["RSI"] > 40 and last["MACD_Hist"] > 0:
                signal = "Buy ✅"
            elif last["EMA20"] < last["EMA50"] and last["RSI"] < 60 and last["MACD_Hist"] < 0:
                signal = "Sell ❌"

            if signal == "Buy ✅":
                buy_frames.append(tf)
            elif signal == "Sell ❌":
                sell_frames.append(tf)
            else:
                hold_frames.append(tf)

        except Exception as e:
            hold_frames.append(tf)

    total = len(timeframes)
    buy_percent = len(buy_frames) / total * 100
    sell_percent = len(sell_frames) / total * 100

    st.subheader(f"Multi-Timeframe Analysis for {symbol}")
    st.write(f"✅ Buy: {round(buy_percent, 2)}% ({len(buy_frames)} timeframes)")
    st.write(", ".join(buy_frames))

    st.write(f"❌ Sell: {round(sell_percent, 2)}% ({len(sell_frames)} timeframes)")
    st.write(", ".join(sell_frames))

    if buy_percent > 70:
        st.success("Strong Buy Signal across multiple timeframes!")
    elif sell_percent > 70:
        st.error("Strong Sell Signal across multiple timeframes!")
    else:
        st.warning("No clear trend: Signals are mixed.")
        
        # ---------------------------------
# واجهة المستخدم
# ---------------------------------

st.title("Crypto Analyzer" if language == "English" else "محلل العملات الرقمية")

results = []

# زر التحليل العادي
if st.button(TXT["analyze"]):
    for sym in symbols:
        try:
            result, df = analyze(sym)
            results.append(result)

            st.subheader(f"{sym} - {TXT['signal']}: {result['signal']}")
            st.write(f"{TXT['price']}: {round(result['price'], 4)}")
            st.write(f"{TXT['sl']}: {round(result['sl'], 4)}")
            st.write(f"{TXT['tp']}:")
            st.write(f"• TP1: {round(result['tp1'], 4)}")
            st.write(f"• TP2: {round(result['tp2'], 4)}")
            st.write(f"• TP3: {round(result['tp3'], 4)}")
            st.write(f"{TXT['rsi']}: {round(result['rsi'], 2)}")
            st.write(f"{TXT['risk']}: {round(result['risk_pct'], 2)}%")
            st.write(f"Price Action: {result['pa']}")
            st.write(f"{TXT['score']}: {result['score']}%")
            st.markdown("---")

        except Exception as e:
            st.error(f"Error analyzing {sym}: {e}")

# زر تحليل جميع الفريمات الزمنية
if st.button(TXT["multi"]):
    for sym in symbols:
        analyze_all_timeframes(sym)

# عرض جدول ملخص لكل العملات التي تم تحليلها
if results:
    df_results = pd.DataFrame(results)
    st.subheader(TXT["summary"])
    st.dataframe(df_results)