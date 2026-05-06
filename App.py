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
# TÍNH TOÁN TẤT CẢ CHỈ BÁO
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
    # Thêm fillna(50) để bẫy lỗi NaN khi giá đi ngang
    rs = delta.clip(lower=0).rolling(14).mean() / (-delta.clip(upper=0)).rolling(14).mean().replace(0, np.nan)
    df["rsi"] = (100 - 100 / (1 + rs)).fillna(50)

    df["macd"] = ema(c, 12) - ema(c, 26)
    df["macd_signal"] = ema(np.nan_to_num(df["macd"].values), 9)
    df["macd_hist"] = df["macd"] - df["macd_signal"]

    # Tín hiệu cho biểu đồ
    df["buy_signal"] = (df["ema9"] > df["ema21"]) & (df["ema9"].shift(1) <= df["ema21"].shift(1)) & (df["rsi"] > 40)
    df["sell_signal"] = (df["ema9"] < df["ema21"]) & (df["ema9"].shift(1) >= df["ema21"].shift(1)) & (df["rsi"] < 60)

    tr, dmp, dmm = np.zeros(n), np.zeros(n), np.zeros(n)
    for i in range(1, n):
        tr[i]  = max(h[i]-l[i], abs(h[i]-c[i-1]), abs(l[i]-c[i-1]))
        dmp[i] = max(h[i]-h[i-1], 0) if (h[i]-h[i-1]) > (l[i-1]-l[i]) else 0
        dmm[i] = max(l[i-1]-l[i], 0) if (l[i-1]-l[i]) > (h[i]-h[i-1]) else 0

    def wilder(arr, p):
        out = np.full(len(arr), np.nan); out[p] = sum(arr[1:p+1])
        for i in range(p+1, len(arr)): out[i] = out[i-1] - out[i-1]/p + arr[i]
        return out

    atr14, dmp14, dmm14  = wilder(tr, 14), wilder(dmp, 14), wilder(dmm, 14)
    di_pos, di_neg = 100 * dmp14 / np.where(atr14==0, 1, atr14), 100 * dmm14 / np.where(atr14==0, 1, atr14)
    df["adx"] = wilder(100 * np.abs(di_pos - di_neg) / np.where((di_pos+di_neg)==0, 1, (di_pos+di_neg)), 14)
    df["di_pos"], df["di_neg"], df["vol_ma"] = di_pos, di_neg, pd.Series(df["volume"].values).rolling(20).mean().values
    return df

# ─────────────────────────────────────────────
# PHÁT HIỆN XU HƯỚNG & TÍN HIỆU CHI TIẾT
# ─────────────────────────────────────────────
def detect_regime(df: pd.DataFrame) -> dict:
    last = df.iloc[-1]
    adx, di_pos, di_neg, rsi, bb_w, ema9, ema21, ema50, close, macd_h = (
        last.get("adx", 20), last.get("di_pos", 20), last.get("di_neg", 20), last.get("rsi", 50),
        last.get("bb_width", 0.03), last.get("ema9", last["close"]), last.get("ema21", last["close"]),
        last.get("ema50", last["close"]), last["close"], last.get("macd_hist", 0)
    )
    if np.isnan(adx): adx = 20

    # Phân loại Xu hướng (Regime)
    if adx < 22 or bb_w < 0.015: regime, strength = "SIDEWAY", "YẾU" if adx < 18 else "VỪA"
    elif di_pos > di_neg: regime, strength = "UPTREND", "MẠNH" if adx > 35 else "VỪA"
    else: regime, strength = "DOWNTREND", "MẠNH" if adx > 35 else "VỪA"

    # Tổng hợp Tín hiệu
    signals = []
    if ema9 > ema21 > ema50: signals.append(("🟢", "EMA Cross (LONG)", "BUY"))
    elif ema9 < ema21 < ema50: signals.append(("🔴", "EMA Cross (SHORT)", "SELL"))
    if rsi < 30: signals.append(("🟢", f"RSI Oversold ({rsi:.1f})", "BUY"))
    elif rsi > 70: signals.append(("🔴", f"RSI Overbought ({rsi:.1f})", "SELL"))
    if df.iloc[-2].get("macd_hist", 0) < 0 < macd_h: signals.append(("🟢", "MACD Flip (Up)", "BUY"))
    elif df.iloc[-2].get("macd_hist", 0) > 0 > macd_h: signals.append(("🔴", "MACD Flip (Down)", "SELL"))
    if close > last.get("bb_upper", close): signals.append(("🚀", "BB Breakout (Cạnh trên)", "BUY"))
    elif close < last.get("bb_lower", close): signals.append(("💥", "BB Breakout (Cạnh dưới)", "SELL"))
    
    hist_bb_w = df["bb_width"].dropna().tail(50)
    if len(hist_bb_w) > 10 and bb_w < hist_bb_w.quantile(0.15):
        signals.append(("⚡", "BB Squeeze (Nén giá)", "WATCH"))

    # ĐÃ SỬA LỖI Ở ĐÂY: Trả về đầy đủ ema9 và ema21
    return {"regime": regime, "strength": strength, "adx": adx, "di_pos": di_pos, "di_neg": di_neg, "rsi": rsi, "ema9": ema9, "ema21": ema21, "signals": signals}

# ─────────────────────────────────────────────
# BIỂU ĐỒ NẾN + TOGGLE BẬT TẮT CHỈ BÁO
# ─────────────────────────────────────────────
COLORS = {"bg": "#0a0e1a", "grid": "#1e2d4a", "candle_up":"#00e676", "candle_dn":"#ff5252", "bb": "#475569", "bb_fill": "rgba(71,85,105,0.08)"}

def build_chart(df: pd.DataFrame, title: str, show_ema: bool, show_bb: bool, show_signals: bool, show_trades: bool) -> go.Figure:
    df = df.copy().dropna(subset=["ema21"]).iloc[-100:]
    fig = make_subplots(rows=4, cols=1, shared_xaxes=True, row_heights=[0.52, 0.15, 0.17, 0.16], vertical_spacing=0.01)

    # Nến
    fig.add_trace(go.Candlestick(x=df.index, open=df["open"], high=df["high"], low=df["low"], close=df["close"],
        increasing_line_color=COLORS["candle_up"], decreasing_line_color=COLORS["candle_dn"],
        increasing_fillcolor=COLORS["candle_up"], decreasing_fillcolor=COLORS["candle_dn"], name="OHLC"), row=1, col=1)

    # Toggle: BB & EMA
    if show_bb:
        fig.add_trace(go.Scatter(x=df.index, y=df["bb_upper"], line=dict(color=COLORS["bb"], width=1, dash="dot"), showlegend=False), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df["bb_lower"], line=dict(color=COLORS["bb"], width=1, dash="dot"), fill="tonexty", fillcolor=COLORS["bb_fill"], showlegend=False), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df["bb_mid"], line=dict(color=COLORS["bb"], width=0.8), showlegend=False), row=1, col=1)
    if show_ema:
        for col, color, lbl in [("ema9","#f59e0b","EMA9"), ("ema21","#38bdf8","EMA21"), ("ema50","#a78bfa","EMA50")]:
            fig.add_trace(go.Scatter(x=df.index, y=df[col], line=dict(color=color, width=1.5), name=lbl), row=1, col=1)

    # Toggle: Tín hiệu & Lệnh
    if show_signals:
        buys, sells = df[df["buy_signal"] == True], df[df["sell_signal"] == True]
        if not buys.empty: fig.add_trace(go.Scatter(x=buys.index, y=buys["low"] - 1.5, mode="markers", marker=dict(symbol="triangle-up", size=14, color="#00e676"), name="MUA"), row=1, col=1)
        if not sells.empty: fig.add_trace(go.Scatter(x=sells.index, y=sells["high"] + 1.5, mode="markers", marker=dict(symbol="triangle-down", size=14, color="#ff5252"), name="BÁN"), row=1, col=1)
    if show_trades and "trade_history" in st.session_state:
        for t in st.session_state.trade_history:
            if t["status"] == "OPEN":
                c = "#00e676" if t["direction"] == "LONG" else "#ff5252"
                fig.add_hline(y=t["entry"], line_color=c, line_width=1.5, row=1, col=1, annotation_text=f"ENTRY", annotation_font_color=c)
                fig.add_hline(y=t["tp"], line_color="#00e676", line_width=1, line_dash="dash", row=1, col=1, annotation_text=f"TP", annotation_font_color="#00e676")
                fig.add_hline(y=t["sl"], line_color="#ff5252", line_width=1, line_dash="dash", row=1, col=1, annotation_text=f"SL", annotation_font_color="#ff5252")

    # Vol, MACD, RSI
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
# LOGIC QUẢN LÝ LỆNH (ORDERS)
# ─────────────────────────────────────────────
def add_trade(direction, entry, tp, sl, size):
    st.session_state.trade_history.insert(0, {"id": len(st.session_state.trade_history)+1, "time": datetime.now().strftime("%H:%M:%S"), "date": datetime.now().strftime("%d/%m"), "direction": direction, "entry": entry, "tp": tp, "sl": sl, "size": size, "status": "OPEN", "pnl": 0.0})

def close_trade(idx, current_price):
    t = st.session_state.trade_history[idx]
    if t["status"] == "OPEN":
        t["status"], t["exit_price"] = "CLOSED", current_price
        t["pnl"] = (current_price - t["entry"]) * (1 if t["direction"] == "LONG" else -1) * t["size"] * 100_000

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

    st.markdown('<div class="section-header">📐 QUẢN LÝ LỆNH & RỦI RO</div>', unsafe_allow_html=True)
    lot_size  = st.number_input("Số hợp đồng (Size)", min_value=1, max_value=50, value=1)
    tp_points = st.number_input("Chốt lời (TP) - Điểm", min_value=1.0, max_value=50.0, value=8.0, step=0.5)
    sl_points = st.number_input("Cắt lỗ (SL) - Điểm", min_value=1.0, max_value=30.0, value=4.0, step=0.5)
    
    # Tính năng tỷ lệ R:R
    st.markdown(f'<div style="color:#ffd600;font-family:JetBrains Mono;font-size:12px;margin-top:-10px">Tỉ lệ R:R = 1 : {tp_points/sl_points:.1f}</div>', unsafe_allow_html=True)
    
    st.markdown("---")
    st.markdown('<div style="font-size:10px;color:#00e676;font-family:JetBrains Mono">🟢 Đang kết nối Realtime API</div>', unsafe_allow_html=True)

# ─────────────────────────────────────────────
# GIAO DIỆN CHÍNH (MAIN APP)
# ─────────────────────────────────────────────
df1, df5 = fetch_real_ohlcv(symbol, 1, 3), fetch_real_ohlcv(symbol, 5, 7)
if df1.empty or df5.empty: st.error("❌ Không lấy được dữ liệu. Có thể do ngoài giờ giao dịch, nghỉ lễ hoặc API đang bảo trì."); st.stop()

df1, df5 = add_indicators(df1), add_indicators(df5)
current_price, prev_close = df1["close"].iloc[-1], df1["close"].iloc[-2]
regime1, regime5 = detect_regime(df1), detect_regime(df5)

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

# --- 2. BẢNG PHÁT HIỆN XU HƯỚNG (REGIME BANNERS) ---
def regime_banner(r: dict, label: str):
    css = {"UPTREND":"uptrend","DOWNTREND":"downtrend","SIDEWAY":"sideway"}.get(r["regime"],"sideway")
    icon = {"UPTREND":"🚀","DOWNTREND":"💥","SIDEWAY":"🔄"}.get(r["regime"],"")
    arrow = {"UPTREND":"▲","DOWNTREND":"▼","SIDEWAY":"◈"}.get(r["regime"],"")
    desc = {"UPTREND": "TĂNG – Ưu tiên BUY/LONG", "DOWNTREND":"GIẢM – Ưu tiên SELL/SHORT", "SIDEWAY": "ĐI NGANG – Đánh biên, chờ Breakout"}.get(r["regime"],"")
    return f'<div class="signal-card {css}">{icon} [{label}] {arrow} {r["regime"]} – {r["strength"]}<br><span style="font-size:11px;font-weight:400">{desc} (ADX: {r["adx"]:.1f})</span></div>'

c_r1, c_r5 = st.columns(2)
with c_r1: st.markdown(regime_banner(regime1, "KHUNG 1 PHÚT"), unsafe_allow_html=True)
with c_r5: st.markdown(regime_banner(regime5, "KHUNG 5 PHÚT"), unsafe_allow_html=True)

# --- 3. BẢNG TÍN HIỆU CHI TIẾT (SIGNALS) ---
all_sigs = [(s, "1P") for s in regime1["signals"]] + [(s, "5P") for s in regime5["signals"]]
if all_sigs:
    st.markdown('<div class="section-header" style="margin-top:10px">🎯 TÍN HIỆU PHÁT HIỆN GẦN NHẤT</div>', unsafe_allow_html=True)
    sig_cols = st.columns(min(len(all_sigs), 4))
    for idx, ((icon, desc, action), tf) in enumerate(all_sigs[:4]):
        color = "#00e676" if action=="BUY" else "#ff5252" if action=="SELL" else "#ffd600"
        sig_cols[idx % 4].markdown(f"<div style='background:#111827;border-left:3px solid {color};border-radius:6px;padding:10px;font-family:JetBrains Mono;font-size:11px;'><div style='color:{color};font-weight:700'>{icon} {action} [{tf}]</div><div style='color:#94a3b8;margin-top:3px'>{desc}</div></div>", unsafe_allow_html=True)
st.markdown("<br>", unsafe_allow_html=True)

# --- 4. BIỂU ĐỒ & PANEL VÀO LỆNH ---
chart_col, trade_col = st.columns([3, 1.1])

with chart_col:
    tab1, tab5 = st.tabs(["📊 Biểu đồ 1 Phút", "📊 Biểu đồ 5 Phút"])
    with tab1: st.plotly_chart(build_chart(df1, f"{symbol} · 1P", show_ema, show_bb, show_signals, show_trades), use_container_width=True, config={"displayModeBar": False})
    with tab5: st.plotly_chart(build_chart(df5, f"{symbol} · 5P", show_ema, show_bb, show_signals, show_trades), use_container_width=True, config={"displayModeBar": False})

with trade_col:
    st.markdown('<div class="section-header">🔫 VÀO LỆNH NHANH</div>', unsafe_allow_html=True)
    entry_price = st.number_input("Giá vào", value=float(f"{current_price:.2f}"), step=0.1)
    
    c1, c2 = st.columns(2)
    with c1:
        if st.button("🟢 BUY (LONG)", use_container_width=True): add_trade("LONG", entry_price, entry_price+tp_points, entry_price-sl_points, lot_size); st.rerun()
    with c2:
        if st.button("🔴 SELL (SHORT)", use_container_width=True): add_trade("SHORT", entry_price, entry_price-tp_points, entry_price+sl_points, lot_size); st.rerun()

    # --- 5. LỊCH SỬ LỆNH (Realtime P&L) ---
    st.markdown('<div class="section-header" style="margin-top:14px">📋 LỊCH SỬ LỆNH (Realtime P&L)</div>', unsafe_allow_html=True)
    if st.button("🗑️ Xóa Lịch sử", use_container_width=True): st.session_state.trade_history = []; st.rerun()
    
    open_pnl = sum(((current_price - t["entry"]) * (1 if t["direction"]=="LONG" else -1) * t["size"]) for t in st.session_state.trade_history if t["status"]=="OPEN")
    st.markdown(f"<div style='font-family:JetBrains Mono; font-size:13px; margin: 10px 0;'>P&L Đang mở: <b style='color:{'#00e676' if open_pnl >= 0 else '#ff5252'}'>{open_pnl:+.1f} điểm</b></div>", unsafe_allow_html=True)

    for i, t in enumerate(st.session_state.trade_history):
        live_pnl = f"<span style='color:{'#00e676' if ((current_price - t['entry']) * (1 if t['direction']=='LONG' else -1)) >= 0 else '#ff5252'}'>Lãi/Lỗ: {((current_price - t['entry']) * (1 if t['direction']=='LONG' else -1)):+.1f}</span>" if t["status"] == "OPEN" else ""
        st.markdown(f"<div style='background:#111827;border:1px solid #1e2d4a;padding:10px;margin-top:6px;font-size:11px;font-family:JetBrains Mono;'><span style='color:{'#00e676' if t['direction']=='LONG' else '#ff5252'}'><b>#{t['id']} {t['direction']}</b></span> <span style='float:right;color:#ffd600'>{t['status']}</span><br><span style='color:#94a3b8'>Entry: {t['entry']:.2f} | {live_pnl}</span><br><span style='color:#64748b'>TP:{t['tp']:.2f} SL:{t['sl']:.2f}</span></div>", unsafe_allow_html=True)
        if t["status"] == "OPEN" and st.button(f"Đóng lệnh #{t['id']} thủ công", key=f"close_{i}"): close_trade(i, current_price); st.rerun()

# --- 6. AUTO REFRESH LOOP ---
if auto_refresh:
    if (datetime.now() - st.session_state.last_refresh).seconds >= refresh_sec:
        st.session_state.last_refresh = datetime.now(); st.rerun()
    time.sleep(1); st.rerun()
