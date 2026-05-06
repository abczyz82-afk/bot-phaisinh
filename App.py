import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
from vnstock import stock_historical_data
import time

# ─────────────────────────────────────────────
# PAGE CONFIG & CSS
# ─────────────────────────────────────────────
st.set_page_config(page_title="VN30F Terminal PRO", page_icon="📈", layout="wide")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&display=swap');
    html, body, [class*="css"] { font-family: 'JetBrains Mono', monospace; background-color: #0a0e1a; color: #e2e8f0; }
    .stApp { background: #0a0e1a; }
    .metric-box { background: #111827; border: 1px solid #1e2d4a; border-radius: 8px; padding: 15px; text-align: center; }
    .recommendation-box { padding: 15px; border-radius: 8px; font-weight: bold; text-align: center; margin-bottom: 20px; border: 2px solid; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# DATA ENGINE (Sử dụng vnstock 0.2.8.2 cũ)
# ─────────────────────────────────────────────
@st.cache_data(ttl=30)
def fetch_data_legacy(symbol, tf, days=7):
    try:
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        df = stock_historical_data(symbol=symbol, start_date=start_date, end_date=end_date, resolution=str(tf), type='derivative')
        if df is not None and not df.empty:
            df['time'] = pd.to_datetime(df['time'])
            return df.sort_values('time').reset_index(drop=True)
    except:
        pass
    return pd.DataFrame()

# ─────────────────────────────────────────────
# LOGIC CHỈ BÁO THỦ CÔNG (Không dùng thư viện ngoài)
# ─────────────────────────────────────────────
def add_indicators_manual(df):
    close = df['close']
    # EMA
    df['ema9'] = close.ewm(span=9, adjust=False).mean()
    df['ema21'] = close.ewm(span=21, adjust=False).mean()
    
    # VWAP Thủ công (Nâng cấp 4)
    df['tp'] = (df['high'] + df['low'] + df['close']) / 3
    df['vwap'] = (df['tp'] * df['volume']).cumsum() / df['volume'].cumsum()
    
    # RSI
    delta = close.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))
    
    # Mẫu nến (Nâng cấp 3)
    body = abs(df['close'] - df['open'])
    df['is_engulfing_bull'] = (df['close'] > df['open'].shift(1)) & (df['open'] < df['close'].shift(1))
    
    return df

# ─────────────────────────────────────────────
# HỆ THỐNG ĐIỂM HỘI TỤ (Nâng cấp 1 & 2)
# ─────────────────────────────────────────────
def get_confluence_score(df1, df5):
    score = 0
    reasons = []
    l1, l5 = df1.iloc[-1], df5.iloc[-1]
    
    # 1. VWAP (Trọng số 20)
    if l1['close'] > l1['vwap']:
        score += 20; reasons.append("Giá nằm trên VWAP (Bullish)")
    else:
        score -= 20; reasons.append("Giá nằm dưới VWAP (Bearish)")
        
    # 2. Đa khung EMA (Trọng số 25)
    ema_1p = l1['ema9'] > l1['ema21']
    ema_5p = l5['ema9'] > l5['ema21']
    if ema_1p == ema_5p:
        score += 25 if ema_1p else -25
        reasons.append("Đồng thuận xu hướng 1P & 5P")
        
    # 3. Phân kỳ RSI (Dự báo - Trọng số 20)
    if df1['close'].tail(5).is_monotonic_decreasing and df1['rsi'].tail(5).is_monotonic_increasing:
        score += 20; reasons.append("Phân kỳ RSI Dương (Dự báo Tăng)")
        
    return score, reasons

# ─────────────────────────────────────────────
# GAUGE CHART
# ─────────────────────────────────────────────
def draw_gauge(score):
    fig = go.Figure(go.Indicator(
        mode = "gauge+number", value = score,
        gauge = {'axis': {'range': [-100, 100]},
                 'bar': {'color': "#38bdf8"},
                 'steps': [
                     {'range': [-100, -70], 'color': "#ef4444"},
                     {'range': [-70, -30], 'color': "#7f1d1d"},
                     {'range': [30, 70], 'color': "#064e3b"},
                     {'range': [70, 100], 'color': "#22c55e"}]},
        title = {'text': "Điểm Hội Tụ (Confluence)", 'font': {'size': 16}}
    ))
    fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', font={'color': "white"}, height=280, margin=dict(t=50, b=0))
    return fig

# ─────────────────────────────────────────────
# GIAO DIỆN CHÍNH
# ─────────────────────────────────────────────
st.title("⚡ VN30F TERMINAL PRO")
symbol = st.sidebar.selectbox("Hợp đồng", ["VN30F1M", "VN30F2M"])
auto_refresh = st.sidebar.checkbox("Tự động cập nhật", value=True)

df1 = fetch_data_legacy(symbol, 1)
df5 = fetch_data_legacy(symbol, 5)

if not df1.empty and not df5.empty:
    df1 = add_indicators_manual(df1)
    df5 = add_indicators_manual(df5)
    score, reasons = get_confluence_score(df1, df5)
    
    c1, c2 = st.columns([1, 1.5])
    with c1:
        st.plotly_chart(draw_gauge(score), use_container_width=True)
    with c2:
        st.subheader("🤖 Khuyến nghị AI")
        if score >= 70:
            st.markdown('<div class="recommendation-box" style="color:#00e676; border-color:#00e676; background:rgba(0,230,118,0.1)">🚀 KHUYẾN NGHỊ LONG MẠNH</div>', unsafe_allow_html=True)
        elif score <= -70:
            st.markdown('<div class="recommendation-box" style="color:#ff5252; border-color:#ff5252; background:rgba(255,82,82,0.1)">💥 KHUYẾN NGHỊ SHORT MẠNH</div>', unsafe_allow_html=True)
        else:
            st.info("Chờ tín hiệu hội tụ rõ ràng hơn...")
            
        for r in reasons:
            st.write(f"• {r}")

    # Biểu đồ nến chính
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.7, 0.3], vertical_spacing=0.05)
    fig.add_trace(go.Candlestick(x=df1['time'], open=df1['open'], high=df1['high'], low=df1['low'], close=df1['close'], name="VN30F"), row=1, col=1)
    fig.add_trace(go.Scatter(x=df1['time'], y=df1['vwap'], line=dict(color='#ffd600'), name="VWAP"), row=1, col=1)
    fig.add_trace(go.Scatter(x=df1['time'], y=df1['rsi'], line=dict(color='#38bdf8'), name="RSI"), row=2, col=1)
    fig.update_layout(template="plotly_dark", height=600, xaxis_rangeslider_visible=False)
    st.plotly_chart(fig, use_container_width=True)

else:
    st.error("Không thể lấy dữ liệu từ API vnstock.")

if auto_refresh:
    time.sleep(15)
    st.rerun()
