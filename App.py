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
st.set_page_config(page_title="VN30F Terminal PRO MAX", page_icon="📈", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700&family=Space+Grotesk:wght@400;500;600;700&display=swap');
html, body, [class*="css"] { font-family: 'Space Grotesk', sans-serif; background-color: #0a0e1a; color: #e2e8f0; }
.stApp { background: #0a0e1a; }
section[data-testid="stSidebar"] { background: #0f1526; border-right: 1px solid #1e2d4a; }
section[data-testid="stSidebar"] * { color: #c9d5e8 !important; }
.signal-card { border-radius: 10px; padding: 18px 22px; margin-bottom: 8px; font-family: 'JetBrains Mono', monospace; font-weight: 700; font-size: 15px; letter-spacing: 1px; text-align: center; }
.uptrend  { background: linear-gradient(135deg,#0d2b1e,#0f3b26); border:1.5px solid #00e676; color:#00e676; }
.downtrend{ background: linear-gradient(135deg,#2b0d0d,#3b0f0f); border:1.5px solid #ff5252; color:#ff5252; }
.sideway  { background: linear-gradient(135deg,#1a1a2b,#1e1e3b); border:1.5px solid #ffd600; color:#ffd600; }
.metric-box { background: #111827; border: 1px solid #1e2d4a; border-radius: 8px; padding: 14px 16px; text-align: center; }
.metric-label { font-size: 11px; color: #64748b; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 4px; }
.metric-value { font-family: 'JetBrains Mono', monospace; font-size: 18px; font-weight: 700; }
.green { color: #00e676; } .red { color: #ff5252; } .yellow { color: #ffd600; } .white { color: #f1f5f9; }
.section-header { font-size: 11px; font-weight: 600; letter-spacing: 2px; text-transform: uppercase; color: #475569; border-bottom: 1px solid #1e2d4a; padding-bottom: 6px; margin-bottom: 12px; }
.stButton > button { background: linear-gradient(135deg,#1e40af,#1d4ed8); color: white; border: none; border-radius: 6px; font-family: 'JetBrains Mono', monospace; font-weight: 600; }
.stTabs [data-baseweb="tab"] { font-family: 'JetBrains Mono', monospace; font-size: 12px; color: #64748b; }
.stTabs [aria-selected="true"] { color: #38bdf8 !important; border-bottom-color: #38bdf8 !important; }
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding-top: 1rem; padding-bottom: 1rem; }
.stSelectbox > div > div, .stNumberInput > div > div > input { background: #111827; border-color: #1e2d4a; color: #e2e8f0; }
div[data-testid="stDataFrame"] { font-family: 'JetBrains Mono', monospace; font-size: 13px; }
</style>
""", unsafe_allow_html=True)

if "trade_history" not in st.session_state: st.session_state.trade_history = []
if "last_refresh" not in st.session_state: st.session_state.last_refresh = datetime.now()

# ─────────────────────────────────────────────
# LẤY DỮ LIỆU THỰC TẾ (VNSTOCK)
# ─────────────────────────────────────────────
@st.cache_data(ttl=30, show_spinner=False)
def fetch_real_ohlcv(symbol: str, tf_minutes: int, days_back: int = 5) -> pd.DataFrame:
    try:
        today = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")
        df = stock_historical_data(symbol=symbol, start_date=start_date, end_date=today, resolution=str(tf_minutes), type='derivative')
        if df is not None and not df.empty:
            df = df.sort_values(by='time').reset_index(drop=True)
            df['time'] = pd.to_datetime(df['time'])
            return df.set_index("time")
        return pd.DataFrame()
    except:
        return pd.DataFrame()

# ─────────────────────────────────────────────
# TÍNH TOÁN TẤT CẢ CHỈ BÁO & TẠO ĐIỂM CẮT
# ─────────────────────────────────────────────
def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    c, h, l, n = df["close"].values, df["high"].values, df["low"].values, len(df)

    def ema(arr, period):
        res = np.full(len(arr), np.nan); k = 2 / (period + 1); res[period-1] = arr[:period].mean()
        for i in range(period, len(arr)): res[i] = arr[i] * k + res[i-1] * (1 - k)
        return res

    df["ema9"], df["ema21"], df["ema50"] = ema(c, 9), ema(c, 21), ema(c, 50)
    rmean, rstd = pd.Series(c).rolling(20).mean().values, pd.Series(c).rolling(20).std().values
    df["bb_mid"], df["bb_upper"], df["bb_lower"] = rmean, rmean + 2*rstd, rmean - 2*rstd
    df["bb_width"] = (df["bb_upper"] - df["bb_lower"]) / df["bb_mid"]

    delta = pd.Series(c).diff()
    rs = delta.clip(lower=0).rolling(14).mean() / (-delta.clip(upper=0)).rolling(14).mean().replace(0, np.nan)
    df["rsi"] = (100 - 100 / (1 + rs)).fillna(50)

    df["macd"] = ema(c, 12) - ema(c, 26)
    df["macd_signal"] = ema(np.nan_to_num(df["macd"].values), 9)
    df["macd_hist"] = df["macd"] - df["macd_signal"]

    df['prev_close'] = df['close'].shift(1)
    df['tr1'] = df['high'] - df['low']
    df['tr2'] = (df['high'] - df['prev_close']).abs()
    df['tr3'] = (df['low'] - df['prev_close']).abs()
    df['tr'] = df[['tr1', 'tr2', 'tr3']].max(axis=1)
    df['up_move'] = df['high'] - df['high'].shift(1)
    df['down_move'] = df['low'].shift(1) - df['low']
    df['+dm'] = np.where((df['up_move'] > df['down_move']) & (df['up_move'] > 0), df['up_move'], 0)
    df['-dm'] = np.where((df['down_move'] > df['up_move']) & (df['down_move'] > 0), df['down_move'], 0)
    rma = lambda s, p: s.ewm(alpha=1/p, min_periods=p, adjust=False).mean()
    
    df['atr'] = rma(df['tr'], 14)
    df['+dm14'] = rma(df['+dm'], 14)
    df['-dm14'] = rma(df['-dm'], 14)
    df['di_pos'] = 100 * (df['+dm14'] / df['atr'])
    df['di_neg'] = 100 * (df['-dm14'] / df['atr'])
    df['dx'] = 100 * (df['di_pos'] - df['di_neg']).abs() / (df['di_pos'] + df['di_neg'])
    df['adx'] = rma(df['dx'], 14)
    df.drop(['prev_close', 'tr1', 'tr2', 'tr3', 'tr', 'up_move', 'down_move', '+dm', '-dm', '+dm14', '-dm14', 'dx'], axis=1, inplace=True)

    df["ema_buy"] = (df["ema9"] > df["ema21"]) & (df["ema9"].shift(1) <= df["ema21"].shift(1))
    df["ema_sell"] = (df["ema9"] < df["ema21"]) & (df["ema9"].shift(1) >= df["ema21"].shift(1))
    df["macd_buy"] = (df["macd_hist"] > 0) & (df["macd_hist"].shift(1) <= 0)
    df["macd_sell"] = (df["macd_hist"] < 0) & (df["macd_hist"].shift(1) >= 0)
    df["bb_break_up"] = (df["close"] > df["bb_upper"]) & (df["close"].shift(1) <= df["bb_upper"].shift(1))
    df["bb_break_dn"] = (df["close"] < df["bb_lower"]) & (df["close"].shift(1) >= df["bb_lower"].shift(1))
    df["buy_signal"] = df["ema_buy"] & (df["rsi"] > 40)
    df["sell_signal"] = df["ema_sell"] & (df["rsi"] < 60)
    df["vol_ma"] = pd.Series(df["volume"].values).rolling(20).mean().values
    return df

# ─────────────────────────────────────────────
# TẠO BẢNG NHẬT KÝ TÍN HIỆU LỊCH SỬ (LOG)
# ─────────────────────────────────────────────
def get_signal_history(df: pd.DataFrame, tf_label: str) -> list:
    history = []
    recent_df = df.iloc[-150:] 
    for i in range(1, len(recent_df)):
        row = recent_df.iloc[i]
        t_obj = recent_df.index[i]
        t_str = t_obj.strftime("%d/%m %H:%M:%S")

        if row['ema_buy']: history.append({"_ts": t_obj, "Thời gian": t_str, "Khung": tf_label, "Chỉ báo": "EMA 9/21", "Tín hiệu": "🟢 CẮT LÊN (LONG)"})
        elif row['ema_sell']: history.append({"_ts": t_obj, "Thời gian": t_str, "Khung": tf_label, "Chỉ báo": "EMA 9/21", "Tín hiệu": "🔴 CẮT XUỐNG (SHORT)"})
        if row['macd_buy']: history.append({"_ts": t_obj, "Thời gian": t_str, "Khung": tf_label, "Chỉ báo": "MACD Histogram", "Tín hiệu": "🟢 ĐẢO CHIỀU TĂNG"})
        elif row['macd_sell']: history.append({"_ts": t_obj, "Thời gian": t_str, "Khung": tf_label, "Chỉ báo": "MACD Histogram", "Tín hiệu": "🔴 ĐẢO CHIỀU GIẢM"})
        if row['bb_break_up']: history.append({"_ts": t_obj, "Thời gian": t_str, "Khung": tf_label, "Chỉ báo": "Bollinger Bands", "Tín hiệu": "🚀 BREAK CẠNH TRÊN"})
        elif row['bb_break_dn']: history.append({"_ts": t_obj, "Thời gian": t_str, "Khung": tf_label, "Chỉ báo": "Bollinger Bands", "Tín hiệu": "💥 BREAK CẠNH DƯỚI"})
    return history

def detect_regime(df: pd.DataFrame) -> dict:
    last = df.iloc[-1]
    last_time = df.index[-1].strftime("%H:%M:%S")
    
    adx, di_pos, di_neg, rsi, bb_w, ema9, ema21, ema50, close, macd_h = (
        last.get("adx", 20), last.get("di_pos", 20), last.get("di_neg", 20), last.get("rsi", 50),
        last.get("bb_width", 0.03), last.get("ema9", last["close"]), last.get("ema21", last["close"]),
        last.get("ema50", last["close"]), last["close"], last.get("macd_hist", 0)
    )
    if np.isnan(adx): adx = 20

    hist_bb_w = df["bb_width"].dropna().tail(50)
    sqz_thresh = hist_bb_w.quantile(0.15) if len(hist_bb_w) > 10 else 0.0
    is_sqz = bb_w < sqz_thresh

    if adx < 22: regime, strength = "SIDEWAY", "YẾU" if adx < 18 else "VỪA"
    elif di_pos > di_neg: regime, strength = "UPTREND", "MẠNH" if adx > 35 else "VỪA"
    else: regime, strength = "DOWNTREND", "MẠNH" if adx > 35 else "VỪA"

    signals = []
    if ema9 > ema21 > ema50: signals.append(("🟢", "EMA Hướng Lên (LONG)", "TRẠNG THÁI"))
    elif ema9 < ema21 < ema50: signals.append(("🔴", "EMA Hướng Xuống (SHORT)", "TRẠNG THÁI"))
    if rsi < 30: signals.append(("🟢", f"RSI Oversold ({rsi:.1f})", "CẢNH BÁO"))
    elif rsi > 70: signals.append(("🔴", f"RSI Overbought ({rsi:.1f})", "CẢNH BÁO"))
    if is_sqz: signals.append(("⚡", "BB Squeeze (Nén giá)", "WATCH"))

    return {"regime": regime, "strength": strength, "adx": adx, "di_pos": di_pos, "di_neg": di_neg, "rsi": rsi, "ema9": ema9, "ema21": ema21, "bb_w": bb_w, "sqz_thresh": sqz_thresh, "is_sqz": is_sqz, "signals": signals, "last_time": last_time}

# ─────────────────────────────────────────────
# BIỂU ĐỒ NẾN + TOGGLE BẬT TẮT CHỈ BÁO
# ─────────────────────────────────────────────
COLORS = {"bg": "#0a0e1a", "grid": "#1e2d4a", "candle_up":"#00e676", "candle_dn":"#ff5252", "bb": "#475569", "bb_fill": "rgba(71,85,105,0.08)"}

def build_chart(df: pd.DataFrame, title: str, show_ema: bool, show_bb: bool, show_signals: bool, show_trades: bool) -> go.Figure:
    df = df.copy().dropna(subset=["ema21"]).iloc[-300:] 
    fig = make_subplots(rows=4, cols=1, shared_xaxes=True, row_heights=[0.52, 0.15, 0.17, 0.16], vertical_spacing=0.01)

    fig.add_trace(go.Candlestick(x=df.index, open=df["open"], high=df["high"], low=df["low"], close=df["close"],
        increasing_line_color=COLORS["candle_up"], decreasing_line_color=COLORS["candle_dn"],
        increasing_fillcolor=COLORS["candle_up"], decreasing_fillcolor=COLORS["candle_dn"], name="OHLC"), row=1, col=1)

    if show_bb:
        fig.add_trace(go.Scatter(x=df.index, y=df["bb_upper"], line=dict(color=COLORS["bb"], width=1, dash="dot"), showlegend=False), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df["bb_lower"], line=dict(color=COLORS["bb"], width=1, dash="dot"), fill="tonexty", fillcolor=COLORS["bb_fill"], showlegend=False), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df["bb_mid"], line=dict(color=COLORS["bb"], width=0.8), showlegend=False), row=1, col=1)
    if show_ema:
        for col, color, lbl in [("ema9","#f59e0b","EMA9"), ("ema21","#38bdf8","EMA21"), ("ema50","#a78bfa","EMA50")]:
            fig.add_trace(go.Scatter(x=df.index, y=df[col], line=dict(color=color, width=1.5), name=lbl), row=1, col=1)

    if show_signals:
        buys_ema, sells_ema = df[df["ema_buy"]], df[df["ema_sell"]]
        if not buys_ema.empty: fig.add_trace(go.Scatter(x=buys_ema.index, y=buys_ema["low"] - 1.5, mode="markers", marker=dict(symbol="triangle-up", size=13, color="#00e676"), name="EMA MUA"), row=1, col=1)
        if not sells_ema.empty: fig.add_trace(go.Scatter(x=sells_ema.index, y=sells_ema["high"] + 1.5, mode="markers", marker=dict(symbol="triangle-down", size=13, color="#ff5252"), name="EMA BÁN"), row=1, col=1)
        buys_macd, sells_macd = df[df["macd_buy"]], df[df["macd_sell"]]
        if not buys_macd.empty: fig.add_trace(go.Scatter(x=buys_macd.index, y=buys_macd["low"] - 3.5, mode="markers", marker=dict(symbol="triangle-up", size=10, color="#38bdf8"), name="MACD MUA"), row=1, col=1)
        if not sells_macd.empty: fig.add_trace(go.Scatter(x=sells_macd.index, y=sells_macd["high"] + 3.5, mode="markers", marker=dict(symbol="triangle-down", size=10, color="#f59e0b"), name="MACD BÁN"), row=1, col=1)
    
    if show_trades and "trade_history" in st.session_state:
        for t in st.session_state.trade_history:
            if t["status"] == "OPEN":
                c = "#00e676" if t["direction"] == "LONG" else "#ff5252"
                fig.add_hline(y=t["entry"], line_color=c, line_width=1.5, row=1, col=1, annotation_text=f"ENTRY", annotation_font_color=c)
                fig.add_hline(y=t["tp1"], line_color="#00e676", line_width=1, line_dash="dash", row=1, col=1, annotation_text=f"TP1", annotation_font_color="#00e676")
                fig.add_hline(y=t["tp2"], line_color="#00e676", line_width=1, line_dash="dash", row=1, col=1, annotation_text=f"TP2", annotation_font_color="#00e676")
                fig.add_hline(y=t["tp3"], line_color="#00e676", line_width=1, line_dash="dash", row=1, col=1, annotation_text=f"TP3", annotation_font_color="#00e676")
                fig.add_hline(y=t["sl"], line_color="#ff5252", line_width=1, line_dash="dash", row=1, col=1, annotation_text=f"SL", annotation_font_color="#ff5252")

    v_col = ["rgba(0,230,118,0.55)" if c >= o else "rgba(255,82,82,0.55)" for c, o in zip(df["close"], df["open"])]
    fig.add_trace(go.Bar(x=df.index, y=df["volume"], marker_color=v_col, showlegend=False), row=2, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df["vol_ma"], line=dict(color="#ffd600", width=1.2), showlegend=False), row=2, col=1)
    
    m_col = ["#00e676" if v >= 0 else "#ff5252" for v in df["macd_hist"]]
    fig.add_trace(go.Bar(x=df.index, y=df["macd_hist"], marker_color=m_col, showlegend=False), row=3, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df["macd"], line=dict(color="#38bdf8", width=1.2), name="MACD"), row=3, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df["macd_signal"], line=dict(color="#ffd600", width=1.2), name="Signal"), row=3, col=1)

    fig.add_trace(go.Scatter(x=df.index, y=df["rsi"], line=dict(color="#38bdf8", width=1.5), name="RSI"), row=4, col=1)
    fig.add_hline(y=70, line_color="#ff5252", line_dash="dot", row=4, col=1); fig.add_hline(y=30, line_color="#00e676", line_dash="dot", row=4, col=1)

    fig.update_layout(template="plotly_dark", paper_bgcolor=COLORS["bg"], plot_bgcolor=COLORS["bg"], margin=dict(l=0, r=0, t=36, b=0), height=580, title=dict(text=title, font=dict(family="JetBrains Mono", size=13, color="#64748b"), x=0.01), xaxis_rangeslider_visible=False, hovermode="x unified", legend=dict(orientation="h", yanchor="bottom", y=1.01))
    for i in range(1, 5): fig.update_xaxes(row=i, col=1, gridcolor=COLORS["grid"]); fig.update_yaxes(row=i, col=1, gridcolor=COLORS["grid"], tickfont=dict(size=9, color="#475569"))
    return fig

# ─────────────────────────────────────────────
# LOGIC QUẢN LÝ LỆNH TỰ ĐỘNG & BẢNG THỐNG KÊ
# ─────────────────────────────────────────────
def add_trade(direction, entry, tp1, tp2, tp3, sl, size):
    st.session_state.trade_history.insert(0, {
        "id": len(st.session_state.trade_history)+1, "date": datetime.now().strftime("%d/%m/%Y"),
        "time": datetime.now().strftime("%H:%M:%S"), "exit_time": "-", 
        "direction": direction, "entry": entry, 
        "tp1": tp1, "tp2": tp2, "tp3": tp3, "sl": sl, "size": size, 
        "status": "OPEN", "exit_price": 0.0, "pnl_points": 0.0, "reason": "-"
    })

def close_trade(idx, exit_price, reason="Đóng thủ công"):
    t = st.session_state.trade_history[idx]
    if t["status"] == "OPEN":
        t["status"] = "CLOSED"
        t["exit_price"] = exit_price
        t["exit_time"] = datetime.now().strftime("%H:%M:%S")
        t["reason"] = reason
        pts = (exit_price - t["entry"]) * (1 if t["direction"] == "LONG" else -1)
        t["pnl_points"] = pts
        t["pnl"] = pts * t["size"] * 100_000

def auto_check_trades(current_price, target_tp_key):
    for i, t in enumerate(st.session_state.trade_history):
        if t["status"] == "OPEN":
            active_tp = t[target_tp_key]
            if t["direction"] == "LONG":
                if current_price >= active_tp: close_trade(i, active_tp, f"🎯 Chạm {target_tp_key.upper()}")
                elif current_price <= t["sl"]: close_trade(i, t["sl"], "🛡️ Cắt Lỗ (SL)")
            elif t["direction"] == "SHORT":
                if current_price <= active_tp: close_trade(i, active_tp, f"🎯 Chạm {target_tp_key.upper()}")
                elif current_price >= t["sl"]: close_trade(i, t["sl"], "🛡️ Cắt Lỗ (SL)")

# ─────────────────────────────────────────────
# THANH ĐIỀU KHIỂN (SIDEBAR)
# ─────────────────────────────────────────────
with st.sidebar:
    st.markdown('<div style="font-family:JetBrains Mono;font-size:18px;font-weight:700;color:#38bdf8;padding:8px 0 16px">⚡ VN30F TERMINAL MAX</div>', unsafe_allow_html=True)
    symbol = st.selectbox("Hợp đồng", ["VN30F1M", "VN30F1Q", "VN30F2Q"], index=0)
    auto_refresh = st.toggle("🔄 Cập nhật tự động (Auto-refresh)", value=True)
    refresh_sec  = st.slider("Chu kỳ cập nhật (giây)", 10, 120, 30) if auto_refresh else 30
    
    st.markdown('<div class="section-header">📊 CÔNG CỤ BIỂU ĐỒ</div>', unsafe_allow_html=True)
    show_ema = st.toggle("📉 Hiển thị EMA 9/21/50", value=False)
    show_bb  = st.toggle("🌊 Hiển thị Bollinger Bands", value=False)
    show_signals = st.toggle("🎯 Hiển thị Mũi tên Buy/Sell", value=True)
    show_trades = st.toggle("🛒 Vẽ đường Entry/TP/SL", value=True)

    st.markdown('<div class="section-header">🤖 BOT TỰ TÍNH RỦI RO</div>', unsafe_allow_html=True)
    lot_size  = st.number_input("Số hợp đồng (Size)", min_value=1, max_value=50, value=1)
    
    auto_sltp = st.toggle("🤖 Bot tự động tính SL/TP (Theo ATR)", value=True)
    
    if auto_sltp:
        st.info("💡 Bot đang đo lường biến động thị trường (ATR) để thiết lập Biên độ Cắt lỗ & 3 mốc Chốt lời tự động.")
        sl_pts = 0.0 
    else:
        col_tp1, col_tp2 = st.columns(2)
        tp1_points = col_tp1.number_input("TP 1 (Điểm)", min_value=1.0, max_value=50.0, value=4.0, step=0.5)
        tp2_points = col_tp2.number_input("TP 2 (Điểm)", min_value=1.0, max_value=50.0, value=8.0, step=0.5)
        tp3_points = st.number_input("TP 3 (Điểm)", min_value=1.0, max_value=50.0, value=12.0, step=0.5)
        sl_points = st.number_input("Cắt lỗ (SL) - Điểm", min_value=1.0, max_value=30.0, value=4.0, step=0.5)
        st.markdown(f'<div style="color:#ffd600;font-family:JetBrains Mono;font-size:12px;margin-top:-5px">Tỉ lệ R:R (TP1) = 1 : {tp1_points/sl_points:.1f}</div>', unsafe_allow_html=True)

    auto_tp_target = st.selectbox("Bot tự động chốt lệnh tại:", ["TP1", "TP2", "TP3"], index=2)

# ─────────────────────────────────────────────
# GIAO DIỆN CHÍNH (MAIN APP)
# ─────────────────────────────────────────────
df1, df5 = fetch_real_ohlcv(symbol, 1, 3), fetch_real_ohlcv(symbol, 5, 7)
if df1.empty or df5.empty: st.error("❌ Không lấy được dữ liệu API."); st.stop()

df1, df5 = add_indicators(df1), add_indicators(df5)
current_price, prev_close = df1["close"].iloc[-1], df1["close"].iloc[-2]
regime1, regime5 = detect_regime(df1), detect_regime(df5)

auto_check_trades(current_price, auto_tp_target.lower())

# --- 1. DẢI BĂNG THÔNG SỐ (METRICS) ---
h1, h2, h3, h4, h5, h6 = st.columns([2.2, 1.5, 1.4, 1.4, 1.4, 1.4])
price_chg = current_price - prev_close
h1.markdown(f'<div class="metric-box"><div class="metric-label">{symbol}</div><div class="metric-value white" style="font-size:26px">{current_price:.2f}</div><div style="font-size:12px;color:{"#00e676" if price_chg>=0 else "#ff5252"}">{"▲" if price_chg>=0 else "▼"} {price_chg:+.2f}</div></div>', unsafe_allow_html=True)
h2.markdown(f'<div class="metric-box"><div class="metric-label">Xu hướng 5P</div><div class="metric-value" style="color:{"#00e676" if regime5["regime"]=="UPTREND" else "#ff5252" if regime5["regime"]=="DOWNTREND" else "#ffd600"}">{regime5["regime"]}</div></div>', unsafe_allow_html=True)
h3.markdown(f'<div class="metric-box"><div class="metric-label">RSI (1P)</div><div class="metric-value {"green" if regime1["rsi"]<40 else "red" if regime1["rsi"]>60 else "yellow"}">{regime1["rsi"]:.1f}</div></div>', unsafe_allow_html=True)
h4.markdown(f'<div class="metric-box"><div class="metric-label">EMA 9/21</div><div class="metric-value {"green" if regime1["ema9"]>regime1["ema21"] else "red"}">{"BULL ▲" if regime1["ema9"]>regime1["ema21"] else "BEAR ▼"}</div></div>', unsafe_allow_html=True)
h5.markdown(f'<div class="metric-box"><div class="metric-label">DI+ / DI-</div><div class="metric-value"><span class="green">{regime1["di_pos"]:.1f}</span> / <span class="red">{regime1["di_neg"]:.1f}</span></div></div>', unsafe_allow_html=True)
h6.markdown(f'<div class="metric-box"><div class="metric-label">Volume</div><div class="metric-value yellow">{int(df1["volume"].iloc[-1]):,}</div></div>', unsafe_allow_html=True)
st.markdown("<br>", unsafe_allow_html=True)

# --- 2. BẢNG PHÁT HIỆN XU HƯỚNG ---
def regime_banner(r: dict, label: str):
    css = {"UPTREND":"uptrend","DOWNTREND":"downtrend","SIDEWAY":"sideway"}.get(r["regime"],"sideway")
    icon = {"UPTREND":"🚀","DOWNTREND":"💥","SIDEWAY":"🔄"}.get(r["regime"],"")
    arrow = {"UPTREND":"▲","DOWNTREND":"▼","SIDEWAY":"◈"}.get(r["regime"],"")
    desc = {"UPTREND": "TĂNG – Ưu tiên BUY/LONG", "DOWNTREND":"GIẢM – Ưu tiên SELL/SHORT", "SIDEWAY": "ĐI NGANG – Đánh biên, chờ Breakout"}.get(r["regime"],"")
    return f'<div class="signal-card {css}">{icon} [{label}] {arrow} {r["regime"]} – {r["strength"]}<br><span style="font-size:11px;font-weight:400">{desc} (ADX: {r["adx"]:.1f})</span></div>'

c_r1, c_r5 = st.columns(2)
with c_r1: st.markdown(regime_banner(regime1, "KHUNG 1 PHÚT"), unsafe_allow_html=True)
with c_r5: st.markdown(regime_banner(regime5, "KHUNG 5 PHÚT"), unsafe_allow_html=True)

# --- 3. BẢNG LOGIC & PHÂN TÍCH THỊ TRƯỜNG HIỆN TẠI ---
st.markdown('<div class="section-header" style="margin-top:20px">🧠 BẢNG TIÊU CHÍ & PHÂN TÍCH THỊ TRƯỜNG TRỰC TIẾP</div>', unsafe_allow_html=True)

col_logic, col_calc = st.columns([1.2, 1.8])
with col_logic:
    st.markdown("""
    <div style='background:#0f1526; border:1px solid #1e2d4a; border-radius:8px; padding:12px; font-family:JetBrains Mono; font-size:12px;'>
        <div style='color:#38bdf8; font-weight:bold; margin-bottom:8px;'>📌 BẢNG TIÊU CHÍ XU HƯỚNG</div>
        <span style='color:#ffd600'>ADX < 22</span> ➔ SIDEWAY<br>
        <span style='color:#00e676'>ADX ≥ 22 + DI+ > DI-</span> ➔ UPTREND<br>
        <span style='color:#ff5252'>ADX ≥ 22 + DI- > DI+</span> ➔ DOWNTREND<br><br>
        <span style='color:#a78bfa'>BB Width < Percentile 15%</span> ➔ BB Squeeze<br>
        <span style='color:#64748b; font-size:10px;'>(Chuẩn bị breakout)</span>
    </div>
    """, unsafe_allow_html=True)

with col_calc:
    r5 = regime5
    adx_val, dip, din, bbw, sqz = r5['adx'], r5['di_pos'], r5['di_neg'], r5['bb_w'], r5['sqz_thresh']
    
    adx_text = f"<span style='color:#ffd600'>ADX = {adx_val:.1f} (< 22) ➔ SIDEWAY</span>" if adx_val < 22 else (f"<span style='color:#00e676'>ADX = {adx_val:.1f} (≥ 22) & DI+ > DI- ➔ UPTREND</span>" if dip > din else f"<span style='color:#ff5252'>ADX = {adx_val:.1f} (≥ 22) & DI- > DI+ ➔ DOWNTREND</span>")
    bb_text = f"<span style='color:#a78bfa'>BB Width ({bbw:.4f}) < Mốc 15% ({sqz:.4f}) ➔ ĐANG NÉN GIÁ (SQUEEZE)</span>" if r5['is_sqz'] else f"<span style='color:#64748b'>BB Width ({bbw:.4f}) > Mốc 15% ({sqz:.4f}) ➔ Biên độ mở</span>"
    
    st.markdown(f"""
    <div style='background:#111827; border:1px solid #1e2d4a; border-radius:8px; padding:12px; font-family:JetBrains Mono; font-size:12px;'>
        <div style='color:#38bdf8; font-weight:bold; margin-bottom:8px;'>⚙️ TÍNH TOÁN HIỆN TẠI (KHUNG 5 PHÚT)</div>
        • {adx_text}<br>
        • DI+ = {dip:.1f} | DI- = {din:.1f}<br>
        • {bb_text}<br>
        <hr style="border-color:#1e2d4a; margin:8px 0;">
        <div style='color:#e2e8f0;'><b>Kết luận Bot:</b> Đang ở trạng thái <b style="color:#ffd600">{r5['regime']}</b>. Tín hiệu Squeeze: <b>{"CÓ (Chờ Breakout)" if r5['is_sqz'] else "KHÔNG"}</b>.</div>
    </div>
    """, unsafe_allow_html=True)

# --- 4. BẢNG TRẠNG THÁI CẢNH BÁO HIỆN TẠI ---
all_sigs = [(*s, "1P", regime1["last_time"]) for s in regime1["signals"]] + [(*s, "5P", regime5["last_time"]) for s in regime5["signals"]]
if all_sigs:
    st.markdown('<div class="section-header" style="margin-top:20px">🎯 TRẠNG THÁI CẢNH BÁO HIỆN TẠI (TRÊN NẾN CUỐI CÙNG)</div>', unsafe_allow_html=True)
    sig_cols = st.columns(min(len(all_sigs), 4))
    for idx, (icon, desc, action, tf, sig_time) in enumerate(all_sigs[:4]):
        color = "#00e676" if "LONG" in desc or "Oversold" in desc or "Up" in desc else ("#ff5252" if "SHORT" in desc or "Overbought" in desc or "Down" in desc else "#ffd600")
        sig_cols[idx % 4].markdown(f"""
        <div style='background:#111827;border-left:3px solid {color};border-radius:6px;padding:10px;font-family:JetBrains Mono;font-size:11px;'>
            <div style='display:flex;justify-content:space-between;align-items:center;'>
                <span style='color:{color};font-weight:700'>{icon} {action} [{tf}]</span>
                <span style='color:#64748b;font-size:10px;'>🕒 Cập nhật: {sig_time}</span>
            </div>
            <div style='color:#94a3b8;margin-top:3px'>{desc}</div>
        </div>
        """, unsafe_allow_html=True)
st.markdown("<br>", unsafe_allow_html=True)

# --- 5. BIỂU ĐỒ & NHẬT KÝ (FULL WIDTH MỚI) ---
tab1, tab5, tab_signals = st.tabs(["📊 Biểu đồ 1 Phút", "📊 Biểu đồ 5 Phút", "🔔 Nhật Ký Tín Hiệu Bot"])
with tab1: st.plotly_chart(build_chart(df1, f"{symbol} · 1P", show_ema, show_bb, show_signals, show_trades), use_container_width=True, config={"displayModeBar": False})
with tab5: st.plotly_chart(build_chart(df5, f"{symbol} · 5P", show_ema, show_bb, show_signals, show_trades), use_container_width=True, config={"displayModeBar": False})

with tab_signals:
    st.markdown('<div class="section-header">LỊCH SỬ GIAO CẮT TÍN HIỆU (150 NẾN GẦN NHẤT)</div>', unsafe_allow_html=True)
    h_1m = get_signal_history(df1, "1 Phút")
    h_5m = get_signal_history(df5, "5 Phút")
    all_hist = h_1m + h_5m
    if all_hist:
        all_hist.sort(key=lambda x: x["_ts"], reverse=True)
        for item in all_hist: del item["_ts"]
        st.dataframe(pd.DataFrame(all_hist), use_container_width=True, hide_index=True)
    else:
        st.info("Chưa có sự kiện giao cắt tín hiệu (EMA/MACD/Breakout) nào diễn ra gần đây.")

# ─────────────────────────────────────────────
# 6. KHU VỰC ĐẶT LỆNH & QUẢN LÝ TÀI KHOẢN (ĐƯA XUỐNG DƯỚI)
# ─────────────────────────────────────────────
st.markdown("<hr>", unsafe_allow_html=True)
st.markdown('<div class="section-header">💼 KHU VỰC GIAO DỊCH & QUẢN LÝ LỆNH</div>', unsafe_allow_html=True)

col_order, col_open = st.columns([1.5, 2.5])

with col_order:
    current_atr = df5["atr"].iloc[-1] if not np.isnan(df5["atr"].iloc[-1]) else 2.0
    if auto_sltp:
        calc_sl = current_atr * 1.0  
        calc_tp1 = current_atr * 1.0  
        calc_tp2 = current_atr * 2.0  
        calc_tp3 = current_atr * 3.0  
        
        st.markdown(f"""
        <div style='background:#0f1526; border:1px dashed #38bdf8; border-radius:6px; padding:10px; margin-bottom:12px;'>
            <div style='font-size:11px; color:#94a3b8; font-family:JetBrains Mono;'>📊 BIÊN ĐỘ THỊ TRƯỜNG: <b style="color:#ffd600">{current_atr:.1f} điểm</b></div>
            <div style='font-size:11px; color:#00e676; font-family:JetBrains Mono; margin-top:4px;'>🎯 TP1: <b>+{calc_tp1:.1f}đ</b> | TP2: <b>+{calc_tp2:.1f}đ</b> | TP3: <b>+{calc_tp3:.1f}đ</b></div>
            <div style='font-size:11px; color:#ff5252; font-family:JetBrains Mono; margin-top:4px;'>🛡️ SL: <b>-{calc_sl:.1f}đ</b> (R:R = 1:1 tới 1:3)</div>
        </div>
        """, unsafe_allow_html=True)

    entry_price = st.number_input("Giá vào lệnh", value=float(f"{current_price:.2f}"), step=0.1)
    
    c1, c2 = st.columns(2)
    with c1:
        if st.button("🟢 BUY (LONG)", use_container_width=True): 
            if auto_sltp:
                add_trade("LONG", entry_price, entry_price+calc_tp1, entry_price+calc_tp2, entry_price+calc_tp3, entry_price-calc_sl, lot_size)
            else:
                add_trade("LONG", entry_price, entry_price+tp1_points, entry_price+tp2_points, entry_price+tp3_points, entry_price-sl_points, lot_size)
            st.rerun()
    with c2:
        if st.button("🔴 SELL (SHORT)", use_container_width=True): 
            if auto_sltp:
                add_trade("SHORT", entry_price, entry_price-calc_tp1, entry_price-calc_tp2, entry_price-calc_tp3, entry_price+calc_sl, lot_size)
            else:
                add_trade("SHORT", entry_price, entry_price-tp1_points, entry_price-tp2_points, entry_price-tp3_points, entry_price+sl_points, lot_size)
            st.rerun()

with col_open:
    st.markdown('<div style="font-size:12px; color:#94a3b8; font-family:JetBrains Mono; margin-bottom:10px; font-weight:bold;">📋 LỆNH ĐANG MỞ (OPEN)</div>', unsafe_allow_html=True)
    open_trades_exist = False
    for i, t in enumerate(st.session_state.trade_history):
        if t["status"] == "OPEN":
            open_trades_exist = True
            live_pnl = (current_price - t['entry']) * (1 if t['direction']=='LONG' else -1)
            st.markdown(f"""
            <div style='background:#111827;border:1px solid #1e2d4a;padding:10px;margin-bottom:6px;font-size:11px;font-family:JetBrains Mono;'>
                <span style='color:{'#00e676' if t['direction']=='LONG' else '#ff5252'}'><b>#{t['id']} {t['direction']}</b></span> 
                <span style='float:right;color:#ffd600'>ĐANG MỞ</span><br>
                <span style='color:#94a3b8'>Entry: {t['entry']:.2f} | <span style='color:{'#00e676' if live_pnl >= 0 else '#ff5252'}'>Lãi/Lỗ: {live_pnl:+.1f}</span></span><br>
                <span style='color:#64748b'>TP1: {t['tp1']:.1f} | TP2: {t['tp2']:.1f} | TP3: {t['tp3']:.1f}</span><br>
                <span style='color:#ff5252'>SL: {t['sl']:.1f}</span>
            </div>
            """, unsafe_allow_html=True)
            if st.button(f"Đóng lệnh #{t['id']} thủ công", key=f"close_{i}"): close_trade(i, current_price, "Đóng thủ công"); st.rerun()
    if not open_trades_exist:
        st.markdown("<div style='color:#475569;font-size:12px;font-family:JetBrains Mono'>Chưa có lệnh nào đang mở.</div>", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# 7. NHẬT KÝ ĐÓNG LỆNH (FULL TABLE)
# ─────────────────────────────────────────────
st.markdown('<div class="section-header" style="margin-top:20px">📔 NHẬT KÝ LỆNH ĐÃ ĐÓNG</div>', unsafe_allow_html=True)
closed_trades = [t for t in st.session_state.trade_history if t["status"] == "CLOSED"]

if closed_trades:
    history_data = []
    for t in closed_trades:
        history_data.append({
            "Mã Lệnh": f"#{t['id']}",
            "Lệnh": "🟢 LONG" if t["direction"] == "LONG" else "🔴 SHORT",
            "Giờ VÀO": f"{t['date']} {t['time']}",
            "Giờ RA": f"{t['date']} {t['exit_time']}",
            "Giá VÀO": f"{t['entry']:.1f}",
            "Giá RA": f"{t['exit_price']:.1f}",
            "Kết quả": t["reason"],
            "Điểm Lãi/Lỗ": f"{t['pnl_points']:+.1f} đ",
            "Tổng Tiền (VNĐ)": f"{t.get('pnl', 0):+,.0f} ₫"
        })
    st.dataframe(pd.DataFrame(history_data), use_container_width=True, hide_index=True)
    if st.button("🗑️ Xóa toàn bộ Lịch sử", type="primary"): 
        st.session_state.trade_history = []
        st.rerun()
else:
    st.info("⚪ Chưa có lệnh nào được đóng. Hãy vào lệnh phía trên và chờ hệ thống Chốt lời / Cắt lỗ.")

# --- 8. AUTO REFRESH LOOP ---
if auto_refresh:
    if (datetime.now() - st.session_state.last_refresh).seconds >= refresh_sec:
        st.session_state.last_refresh = datetime.now(); st.rerun()
    time.sleep(1); st.rerun()
