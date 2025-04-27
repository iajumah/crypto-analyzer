import streamlit as st
import pandas as pd
from binance.client import Client
import requests

# إعداد Binance Client باستخدام Secrets بدون Ping
api_key = st.secrets["BINANCE_API_KEY"]
api_secret = st.secrets["BINANCE_API_SECRET"]
binance_client = Client(api_key, api_secret)
binance_client.API_URL = 'https://api.binance.com/api'  # نحدد عنوان API رسمي بدون اختبار Ping

# دالة جلب البيانات
def fetch_data(symbol, interval, limit):
    try:
        klines = binance_client.get_klines(symbol=symbol, interval=interval, limit=limit)
        if not klines:
            raise Exception("No data returned from Binance API.")

        df = pd.DataFrame(klines, columns=[
            "time", "open", "high", "low", "close", "volume",
            "close_time", "qav", "trades", "tbbav", "tbqav", "ignore"
        ])
        df["time"] = pd.to_datetime(df["time"], unit="ms")
        df[["open", "high", "low", "close", "volume"]] = df[["open", "high", "low", "close", "volume"]].astype(float)
        return df
    except Exception as e:
        st.error(f"Error fetching data for {symbol}: {e}")
        return pd.DataFrame()

# واجهة التطبيق
st.set_page_config(page_title="Crypto Analyzer", page_icon=":chart_with_upwards_trend:", layout="wide")

st.title("تحليل العملات الرقمية - Binance")

# اختيار العملة وزمن الفريم
symbol = st.text_input("ادخل رمز العملة (مثل BTCUSDT):", "BTCUSDT").upper()
interval = st.selectbox("اختر الإطار الزمني:", ["1m", "5m", "15m", "30m", "1h", "2h", "4h", "6h", "12h", "1d", "1w"])
limit = st.slider("عدد الشموع لتحليلها:", min_value=10, max_value=500, value=100)

# زر بدء التحليل
if st.button("ابدأ التحليل"):
    df = fetch_data(symbol, interval, limit)
    if not df.empty:
        st.success(f"تم جلب بيانات {symbol} بنجاح!")
        st.dataframe(df)

        # مثال: تحليل بسيط اتجاه السعر بناءً على آخر شمعتين
        if df["close"].iloc[-1] > df["open"].iloc[-1]:
            st.success("الإشارة: شراء Buy ✅")
        elif df["close"].iloc[-1] < df["open"].iloc[-1]:
            st.error("الإشارة: بيع Sell ❌")
        else:
            st.warning("الإشارة: تردد Hold ⚪️")