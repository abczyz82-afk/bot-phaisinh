import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import time
import pytz

VN_TZ = pytz.timezone('Asia/Ho_Chi_Minh')

# ══════════════════════════════════════════════════════════════
# PAGE CONFIG & CSS
# ══════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="VN30F Terminal PRO MAX v3",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600;700&family=Space+Grotesk:wght@400;500;600;700&display=swap');
html,body,[class*="css"]{font-family:'Space Grotesk',sans-serif;background:#080c18;color:#dde4f0;}
.stApp{background:#080c18;}
section[data-testid="stSidebar"]{background:#0c1020;border-right:1px solid #1a2540;}
section[data-testid="stSidebar"] *{color:#c0ccdf!important;}
.metric-box{background:#0f1626;border:1px solid #1a2540;border-radius:8px;padding:12px 14px;text-align:center;}
.metric-label{font-size:10px;color:#475569;text-transform:uppercase;letter-spacing:1.5px;margin-bottom:4px;font-family:'JetBrains Mono',monospace;}
.metric-value{font-family:'JetBrains Mono',monospace;font-size:17px;font-weight:700;}
.green{color:#00e676;}.red{color:#ff5252;}.yellow{color:#ffd600;}.white{color:#f1f5f9;}.blue{color:#38bdf8;}.purple{color:#a78bfa;}
.signal-card{border-radius:10px;padding:14px 18px;margin-bottom:8px;font-family:'JetBrains Mono',monospace;font-weight:700;font-size:13px;text-align:center;}
.uptrend{background:linear-gradient(135deg,#0a2218,#0d311f);border:1.5px solid #00e676;color:#00e676;}
.downtrend{background:linear-gradient(135deg,#220a0a,#310d0d);border:1.5px solid #ff5252;color:#ff5252;}
.sideway{background:linear-gradient(135deg,#18180a,#26240a);border:1.5px solid #ffd600;color:#ffd600;}
.sec-hdr{font-size:10px;font-weight:700;letter-spacing:2.5px;text-transform:uppercase;color:#334155;border-bottom:1px solid #1a2540;padding-bottom:5px;margin-bottom:10px;font-family:'JetBrains Mono',monospace;}
.rec-strong-long{background:linear-gradient(135deg,#052212,#072e18);border:2px solid #00e676;border-radius:12px;padding:18px 20px;font-family:'JetBrains Mono',monospace;}
.rec-strong-short{background:linear-gradient(135deg,#220505,#2e0707);border:2px solid #ff5252;border-radius:12px;padding:18px 20px;font-family:'JetBrains Mono',monospace;}
.rec-watch{background:linear-gradient(135deg,#141205,#1c1a07);border:2px solid #ffd600;border-radius:12px;padding:18px 20px;font-family:'JetBrains Mono',monospace;}
.rec-neutral{background:#0f1626;border:1.5px solid #1a2540;border-radius:12px;padding:18px 20px;font-family:'JetBrains Mono',monospace;}
.score-bar-wrap{background:#1a2540;border-radius:6px;height:12px;width:100%;margin:8px 0;}
.forecast-box{background:#0f1626;border:1px solid #1a2540;border-radius:8px;padding:12px 14px;margin-bottom:8px;font-family:'JetBrains Mono',monospace;font-size:11px;}
.pattern-tag{display:inline-block;border-radius:4px;padding:2px 7px;font-family:'JetBrains Mono',monospace;font-size:10px;font-weight:600;margin:2px;}
.stButton>button{background:linear-gradient(135deg,#1e3a8a,#1d4ed8);color:#fff;border:none;border-radius:6px;font-family:'JetBrains Mono',monospace;font-weight:600;}
.stButton>button:hover{background:linear-gradient(135deg,#1d4ed8,#3b82f6);}
.stTabs [data-baseweb="tab"]{font-family:'JetBrains Mono',monospace;font-size:11px;color:#475569;}
.stTabs [aria-selected="true"]{color:#38bdf8!important;border-bottom-color:#38bdf8!important;}
#MainMenu,footer,header{visibility:hidden;}
.block-container{padding-top:0.8rem;padding-bottom:0.5rem;}
.stSelectbox>div>div,.stNumberInput>div>div>input{background:#0f1626;border-color:#1a2540;color:#dde4f0;}
@keyframes pulse-green { 0%,100%{box-shadow:0 0 0 0 #00e67644} 50%{box-shadow:0 0 20px 4px #00e67622} }
@keyframes pulse-red    { 0%,100%{box-shadow:0 0 0 0 #ff525244} 50%{box-shadow:0 0 20px 4px #ff525222} }
.alert-long  { background:linear-gradient(135deg,#031a0d,#052212,#072e18);border:2px solid #00e676;border-radius:12px;padding:16px 20px;animation:pulse-green 2s infinite;font-family:'JetBrains Mono',monospace; }
.alert-short { background:linear-gradient(135deg,#1a0303,#220505,#2e0707);border:2px solid #ff5252;border-radius:12px;padding:16px 20px;animation:pulse-red 2s infinite;font-family:'JetBrains Mono',monospace; }
.alert-muted { background:#0f1626;border:1px solid #1a2540;border-radius:12px;padding:16px 20px;font-family:'JetBrains Mono',monospace;opacity:0.5; }
.alert-row-long  { border-left:3px solid #00e676;background:#0a1f12;border-radius:5px;padding:7px 10px;margin-bottom:4px;font-family:'JetBrains Mono',monospace;font-size:11px; }
.alert-row-short { border-left:3px solid #ff5252;background:#1f0a0a;border-radius:5px;padding:7px 10px;margin-bottom:4px;font-family:'JetBrains Mono',monospace;font-size:11px; }
.wr-badge-good { background:#052212;border:1px solid #00e676;color:#00e676;border-radius:5px;padding:3px 8px;font-family:'JetBrains Mono',monospace;font-size:11px;font-weight:700; }
.wr-badge-bad  { background:#220505;border:1px solid #ff5252;color:#ff5252;border-radius:5px;padding:3px 8px;font-family:'JetBrains Mono',monospace;font-size:11px;font-weight:700; }
.wr-badge-mid  { background:#141205;border:1px solid #ffd600;color:#ffd600;border-radius:5px;padding:3px 8px;font-family:'JetBrains Mono',monospace;font-size:11px;font-weight:700; }
.wr-row        { display:flex;justify-content:space-between;align-items:center;padding:7px 0;border-bottom:1px solid #1a2540;font-family:'JetBrains Mono',monospace;font-size:11px; }
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════
# SESSION STATE
# ══════════════════════════════════════════════════════════════
for k, v in {
    "trade_history": [], "last_refresh": datetime.now(VN_TZ),
    "alert_history": [], "alert_last_score": 0, "alert_muted": False,
}.items():
    if k not in st.session_state: st.session_state[k] = v

# ══════════════════════════════════════════════════════════════
# TIỆN ÍCH NGÀY ĐÁO HẠN VN30F1M
# ══════════════════════════════════════════════════════════════
def get_third_thursday(year: int, month: int) -> datetime:
    first_day = datetime(year, month, 1)
    days_to_thu = (3 - first_day.weekday()) % 7
    first_thu = first_day + timedelta(days=days_to_thu)
    return first_thu + timedelta(weeks=2)

def get_vn30f1m_expiry_info() -> dict:
    now = datetime.now(VN_TZ)
    curr_exp = get_third_thursday(now.year, now.month)
    if now.date() > curr_exp.date():
        last_exp = curr_exp
        nm, ny = (now.month + 1, now.year) if now.month < 12 else (1, now.year + 1)
        next_exp = get_third_thursday(ny, nm)
        c_month, c_year = nm, ny
    else:
        pm, py = (now.month - 1, now.year) if now.month > 1 else (12, now.year - 1)
        last_exp, next_exp = get_third_thursday(py, pm), curr_exp
        c_month, c_year = now.month, now.year

    days_since, days_to = (now.date() - last_exp.date()).days, (next_exp.date() - now.date()).days
    contract_name = f"VN30F{str(c_year)[-2:]}{c_month:02d}"
    
    return {"last_expiry": last_exp, "next_expiry": next_exp, "days_since": days_since, 
            "days_to": days_to, "contract_name": contract_name, "exact_symbol": contract_name}

def smart_days_back(symbol: str, tf_minutes: int) -> int:
    if "VN30F1M" not in symbol: return 14 if tf_minutes <= 5 else 60
    info = get_vn30f1m_expiry_info()
    max_avail = max(info["days_since"] + 2, 5)
    return min(max_avail, 14) if tf_minutes == 1 else min(max_avail, 31)

def is_trading_hours() -> bool:
    now = datetime.now(VN_TZ)
    if now.weekday() >= 5: return False
    t = now.time()
    from datetime import time as dtime
    return (dtime(9, 0) <= t <= dtime(11, 30)) or (dtime(13, 0) <= t <= dtime(14, 45))

def _simulate(tf_minutes: int, n: int = 350, seed: int = 42) -> pd.DataFrame:
    np.random.seed(seed)
    now = datetime.now(VN_TZ).replace(second=0, microsecond=0)
    now -= timedelta(minutes=now.minute % tf_minutes)
    times = [now - timedelta(minutes=tf_minutes * i) for i in range(n)][::-1]
    p = [1280.0]
    for i in range(1, n):
        phase = (i // 50) % 3
        drift = 0.18 if phase == 0 else (-0.15 if phase == 2 else 0.0)
        vol = 0.30 if phase == 1 else 0.62
        p.append(max(p[-1] + drift + np.random.normal(0, vol), 100))
    noise = np.abs(np.random.normal(0, 0.3, n)) + 0.1
    df = pd.DataFrame({"time": times, "close": p})
    df["open"] = df["close"].shift(1).fillna(df["close"].iloc[0])
    df["high"] = df[["open","close"]].max(axis=1) + noise
    df["low"]  = df[["open","close"]].min(axis=1) - noise
    df["volume"] = np.random.randint(200, 3500, n)
    df = df.set_index("time")
    df.attrs["_simulated"] = True
    return df

# ══════════════════════════════════════════════════════════════
# DATA FETCHING (DÙNG VNSTOCK 0.2.8.2)
# ══════════════════════════════════════════════════════════════
@st.cache_data(ttl=30, show_spinner=False)
def fetch_data(symbol: str, tf_minutes: int, days_back: int = 7) -> pd.DataFrame:
    end_date   = (datetime.now(VN_TZ) + timedelta(days=1)).strftime("%Y-%m-%d")
    start_date = (datetime.now(VN_TZ) - timedelta(days=days_back + 2)).strftime("%Y-%m-%d")

    symbols_to_try = [get_vn30f1m_expiry_info()["exact_symbol"], "VN30F1M"] if symbol == "VN30F1M" else [symbol]

    def _clean(df: pd.DataFrame) -> pd.DataFrame:
        df = df.rename(columns={c: c.lower() for c in df.columns})
        if "time" not in df.columns: df["time"] = pd.to_datetime(df.index)
        else: df["time"] = pd.to_datetime(df["time"])
        df = df.sort_values("time").set_index("time")
        cols = [c for c in ["open","high","low","close","volume"] if c in df.columns]
        return df[cols].dropna(how="all")

    for sym in symbols_to_try:
        try:
            from vnstock import stock_historical_data
            df = stock_historical_data(symbol=sym, start_date=start_date, end_date=end_date, resolution=str(tf_minutes), type="derivative")
            if df is not None and not df.empty:
                df = _clean(df)
                if not df.empty and len(df) > 5:
                    df.attrs["_simulated"] = False
                    return df
        except Exception:
            continue

    df_sim = _simulate(tf_minutes, n=350, seed=hash(symbol + str(tf_minutes)) % 9999)
    df_sim.attrs["_simulated"] = True
    return df_sim

@st.cache_data(ttl=300, show_spinner=False)
def fetch_data_extended(symbol: str, tf_minutes: int, days_back: int) -> pd.DataFrame:
    return fetch_data(symbol, tf_minutes, days_back)

# ══════════════════════════════════════════════════════════════
# INDICATORS & PATTERNS ENGINE
# ══════════════════════════════════════════════════════════════
def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    c, h, l = df["close"].values, df["high"].values, df["low"].values
    def ema(arr, p):
        r = np.full(len(arr), np.nan); k = 2/(p+1); r[p-1] = arr[:p].mean()
        for i in range(p, len(arr)): r[i] = arr[i]*k + r[i-1]*(1-k)
        return r

    df["ema9"], df["ema21"], df["ema50"] = ema(c, 9), ema(c, 21), ema(c, 50)
    rm = pd.Series(c).rolling(20).mean().values; rs = pd.Series(c).rolling(20).std().values
    df["bb_mid"], df["bb_upper"], df["bb_lower"] = rm, rm + 2*rs, rm - 2*rs
    df["bb_width"] = (df["bb_upper"] - df["bb_lower"]) / pd.Series(rm).replace(0, np.nan).values

    d = pd.Series(c).diff()
    g_ = d.clip(lower=0).rolling(14).mean(); l_ = (-d.clip(upper=0)).rolling(14).mean().replace(0, np.nan)
    df["rsi"] = (100 - 100/(1 + g_/l_)).fillna(50)

    e12, e26 = ema(c,12), ema(c,26)
    ml = e12 - e26
    df["macd"] = ml
    df["macd_signal"] = ema(np.nan_to_num(ml), 9)
    df["macd_hist"] = ml - df["macd_signal"].values
    df["macd_slope"] = pd.Series(df["macd_hist"].values).diff(3)

    df["prev_close"] = df["close"].shift(1)
    df["tr"] = df[["high","low","prev_close"]].apply(lambda r: max(r["high"]-r["low"], abs(r["high"]-r["prev_close"]), abs(r["low"]-r["prev_close"])), axis=1)
    df["up_move"]   = df["high"] - df["high"].shift(1)
    df["down_move"] = df["low"].shift(1) - df["low"]
    df["+dm"] = np.where((df["up_move"]>df["down_move"]) & (df["up_move"]>0), df["up_move"], 0)
    df["-dm"] = np.where((df["down_move"]>df["up_move"]) & (df["down_move"]>0), df["down_move"], 0)
    rma = lambda s, p: s.ewm(alpha=1/p, min_periods=p, adjust=False).mean()
    df["atr"] = rma(df["tr"], 14)
    dmp14, dmm14 = rma(df["+dm"], 14), rma(df["-dm"], 14)
    safe = lambda x: x.replace(0, np.nan)
    df["di_pos"] = 100 * dmp14 / safe(df["atr"])
    df["di_neg"] = 100 * dmm14 / safe(df["atr"])
    df["dx"]     = 100 * (df["di_pos"]-df["di_neg"]).abs() / (df["di_pos"]+df["di_neg"]).replace(0, np.nan)
    df["adx"]    = rma(df["dx"], 14)

    lo14 = pd.Series(l).rolling(14).min(); hi14 = pd.Series(h).rolling(14).max()
    k_   = (pd.Series(c)-lo14)/(hi14-lo14+1e-9)*100
    df["stoch_k"] = k_.rolling(3).mean(); df["stoch_d"] = df["stoch_k"].rolling(3).mean()

    df["date_"]  = df.index.date
    df["tp_"]    = (df["high"] + df["low"] + df["close"]) / 3
    df["cum_tv"] = (df["tp_"] * df["volume"]).groupby(df["date_"]).cumsum()
    df["cum_v"]  = df["volume"].groupby(df["date_"]).cumsum()
    df["vwap"]   = df["cum_tv"] / df["cum_v"].replace(0, np.nan)
    df["_tp_vwap_sq"] = df["volume"] * (df["tp_"] - df["vwap"]) ** 2
    df["_cum_var"]    = df["_tp_vwap_sq"].groupby(df["date_"]).cumsum()
    df["vwap_sd"]     = np.sqrt(df["_cum_var"] / df["cum_v"].replace(0, np.nan))
    df["vwap_u1"], df["vwap_u2"] = df["vwap"] + 1*df["vwap_sd"], df["vwap"] + 2*df["vwap_sd"]
    df["vwap_l1"], df["vwap_l2"] = df["vwap"] - 1*df["vwap_sd"], df["vwap"] - 2*df["vwap_sd"]
    df["vwap_dev_pct"] = (df["close"] - df["vwap"]) / df["vwap"].replace(0, np.nan) * 100

    df["vwap_buy"]  = (df["close"] > df["vwap"]) & (df["close"].shift(1) <= df["vwap"].shift(1))
    df["vwap_sell"] = (df["close"] < df["vwap"]) & (df["close"].shift(1) >= df["vwap"].shift(1))
    df.drop(["prev_close","up_move","down_move","+dm","-dm","dx","date_","tp_","cum_tv","cum_v","_tp_vwap_sq","_cum_var"], axis=1, inplace=True, errors="ignore")
    
    df["vol_ma"] = pd.Series(df["volume"].values).rolling(20).mean().values
    df["ema_buy"]     = (df["ema9"]>df["ema21"]) & (df["ema9"].shift(1)<=df["ema21"].shift(1))
    df["ema_sell"]    = (df["ema9"]<df["ema21"]) & (df["ema9"].shift(1)>=df["ema21"].shift(1))
    df["macd_buy"]    = (df["macd_hist"]>0)  & (df["macd_hist"].shift(1)<=0)
    df["macd_sell"]   = (df["macd_hist"]<0)  & (df["macd_hist"].shift(1)>=0)
    df["bb_break_up"] = (df["close"]>df["bb_upper"]) & (df["close"].shift(1)<=df["bb_upper"].shift(1))
    df["bb_break_dn"] = (df["close"]<df["bb_lower"]) & (df["close"].shift(1)>=df["bb_lower"].shift(1))
    return df

PATTERN_RELIABILITY = {"Morning Star":82,"Evening Star":80,"Three White Soldiers":78,"Three Black Crows":77,"Bull Engulfing":75,"Bear Engulfing":74,"Piercing Line":68,"Dark Cloud Cover":67,"Hammer":65,"Shooting Star":64,"Bullish Harami":60,"Bearish Harami":59,"Marubozu Bull":72,"Marubozu Bear":71,"Tweezer Bottom":63,"Tweezer Top":62,"Doji":55,"Spinning Top":50}

def detect_candle_patterns(df: pd.DataFrame) -> list:
    patterns = []
    if len(df) < 5: return patterns
    c0,c1,c2 = df.iloc[-1], df.iloc[-2], df.iloc[-3]
    def v(c): return c["open"],c["high"],c["low"],c["close"],abs(c["close"]-c["open"]),c["high"]-c["low"]+1e-9,c["high"]-max(c["close"],c["open"]),min(c["close"],c["open"])-c["low"]
    o0,h0,lo0,cl0,bd0,rg0,uw0,lw0 = v(c0)
    o1,h1,lo1,cl1,bd1,rg1,uw1,lw1 = v(c1)
    o2,h2,lo2,cl2,bd2,rg2,uw2,lw2 = v(c2)

    vwap, bb_lo_val, bb_up_val, vwap_l2, vwap_u2 = float(c0.get("vwap",0)), float(c0.get("bb_lower",0)), float(c0.get("bb_upper",9999)), float(c0.get("vwap_l2",0)), float(c0.get("vwap_u2",9999))
    bb_w = float(c0.get("bb_width",0.03))
    is_squeeze = bb_w < df["bb_width"].tail(50).quantile(0.20) if len(df)>10 else False
    at_bb_low, at_bb_high = cl0 <= bb_lo_val * 1.002, cl0 >= bb_up_val * 0.998
    vol_spike = float(c0.get("volume",0)) > float(c0.get("vol_ma",1))*1.5

    def add(name, bias, desc):
        cb = 0
        if bias == "BULL": cb += 12 if at_bb_low else 0; cb += 10 if (vwap_l2>0 and cl0<=vwap_l2*1.003) else 0
        elif bias == "BEAR": cb += 12 if at_bb_high else 0; cb += 10 if (vwap_u2<9998 and cl0>=vwap_u2*0.997) else 0
        cb += 8 if vol_spike else 0; cb += 5 if is_squeeze else 0
        rel = min(PATTERN_RELIABILITY.get(name, 55) + cb, 95)
        ql, qc = ("A","#00e676") if rel>=80 else (("B","#ffd600") if rel>=65 else ("C","#f97316"))
        patterns.append({"name":name,"bias":bias,"desc":desc,"reliability":rel,"context_bonus":cb,"quality":ql,"quality_color":qc})

    if (bd0/rg0<0.35) and (lw0/rg0>0.55) and (uw0/rg0<0.15) and cl1<o1: add("Hammer","BULL","Râu dưới dài ≥ 2× thân")
    if (bd0/rg0<0.35) and (uw0/rg0>0.55) and (lw0/rg0<0.15) and cl1>o1: add("Shooting Star","BEAR","Râu trên dài ≥ 2× thân")
    if cl1<o1 and cl0>o0 and cl0>o1 and o0<cl1 and bd0>bd1: add("Bull Engulfing","BULL","Xanh nuốt trọn đỏ")
    if cl1>o1 and cl0<o0 and cl0<o1 and o0>cl1 and bd0>bd1: add("Bear Engulfing","BEAR","Đỏ nuốt trọn xanh")
    if abs(lo0-lo1)/rg0<0.03 and cl1<o1 and cl0>o0: add("Tweezer Bottom","BULL","Chạm cùng đáy")
    if abs(h0-h1)/rg0<0.03 and cl1>o1 and cl0<o0: add("Tweezer Top","BEAR","Chạm cùng đỉnh")
    if cl2<o2 and bd2/rg2>0.5 and bd1/rg1<0.3 and cl0>o0 and cl0>=(o2+cl2)/2: add("Morning Star","BULL","Đỏ lớn → Nhỏ → Xanh lớn")
    if cl2>o2 and bd2/rg2>0.5 and bd1/rg1<0.3 and cl0<o0 and cl0<=(o2+cl2)/2: add("Evening Star","BEAR","Xanh lớn → Nhỏ → Đỏ lớn")
    if bd0/rg0<0.07: add("Doji","NEUTRAL","Do dự (Mở=Đóng)")
    return patterns

def scan_pattern_history(df: pd.DataFrame, lookback: int = 150) -> list:
    res = []; df_s = df.tail(lookback + 5); seen = set()
    for i in range(5, len(df_s)):
        sub = df_s.iloc[:i+1]; pats = detect_candle_patterns(sub)
        t, price, atr = sub.index[-1], float(sub["close"].iloc[-1]), float(sub["atr"].iloc[-1] if not np.isnan(sub["atr"].iloc[-1]) else 1.0)
        for p in pats:
            if f"{t}_{p['name']}" not in seen:
                seen.add(f"{t}_{p['name']}")
                res.append({**p, "time": t, "price": price, "chart_y": (price-atr*0.8) if p["bias"]=="BULL" else (price+atr*0.8)})
    return res

def detect_rsi_divergence(df: pd.DataFrame, lookback: int = 30) -> dict:
    sub = df.dropna(subset=["rsi"]).tail(lookback)
    if len(sub) < 10: return {"bull": False, "bear": False, "desc": ""}
    p, r = sub["close"].values, sub["rsi"].values
    plows = [(i, p[i]) for i in range(1, len(p)-1) if p[i]<p[i-1] and p[i]<p[i+1]]
    phighs = [(i, p[i]) for i in range(1, len(p)-1) if p[i]>p[i-1] and p[i]>p[i+1]]
    bull_div = len(plows)>=2 and plows[-1][1]<plows[-2][1] and r[plows[-1][0]]>r[plows[-2][0]]+2
    bear_div = len(phighs)>=2 and phighs[-1][1]>phighs[-2][1] and r[phighs[-1][0]]<r[phighs[-2][0]]-2
    return {"bull": bull_div, "bear": bear_div, "desc": "Giá tạo đáy thấp hơn nhưng RSI tạo đáy cao hơn" if bull_div else ("Giá tạo đỉnh cao hơn nhưng RSI tạo đỉnh thấp hơn" if bear_div else "")}

def analyze_volume_accumulation(df: pd.DataFrame, window: int = 10) -> dict:
    sub = df.tail(window)
    bull_v = sub.loc[sub["close"]>=sub["open"], "volume"].sum()
    bear_v = sub.loc[sub["close"]<sub["open"], "volume"].sum()
    ratio = bull_v / (bull_v + bear_v + 1e-9)
    if ratio > 0.65: bias, desc = "BULL", f"Mua áp đảo ({ratio*100:.0f}%)"
    elif ratio < 0.35: bias, desc = "BEAR", f"Bán áp đảo ({(1-ratio)*100:.0f}%)"
    else: bias, desc = "NEUTRAL", "Cân bằng"
    return {"bias": bias, "desc": desc}

# ══════════════════════════════════════════════════════════════
# ENGINES CHÍNH (CONFLUENCE, FORECAST, WINRATE, REGIME)
# ══════════════════════════════════════════════════════════════
def compute_confluence(df1: pd.DataFrame, df5: pd.DataFrame) -> dict:
    score, detail = 0, []
    def s(df, col, d=0): v=df.iloc[-1].get(col,d); return d if np.isnan(v) else float(v)
    
    adx5, di5p, di5n, rsi1, mh1, ms1, vwap1, c1 = s(df5,"adx",20), s(df5,"di_pos",20), s(df5,"di_neg",20), s(df1,"rsi",50), s(df1,"macd_hist"), s(df1,"macd_slope"), s(df1,"vwap"), s(df1,"close")
    e9_1, e21_1, e50_1, e9_5, e21_5 = s(df1,"ema9"), s(df1,"ema21"), s(df1,"ema50"), s(df5,"ema9"), s(df5,"ema21")

    if adx5>=22:
        w=min(int((adx5-22)/13*25),25)
        if di5p>di5n: score+=w; detail.append((w,f"ADX 5P UPTREND","#00e676"))
        else: score-=w; detail.append((w,f"ADX 5P DOWNTREND","#ff5252"))
    
    if e9_1>e21_1>e50_1: score+=15; detail.append((15,"EMA 1P MUA","#00e676"))
    elif e9_1<e21_1<e50_1: score-=15; detail.append((15,"EMA 1P BÁN","#ff5252"))

    if (e9_1>e21_1) and (e9_5>e21_5): score+=20; detail.append((20,"EMA 1P & 5P Đồng thuận LONG","#00e676"))
    elif (e9_1<e21_1) and (e9_5<e21_5): score-=20; detail.append((20,"EMA 1P & 5P Đồng thuận SHORT","#ff5252"))

    if mh1>0 and ms1>0: score+=15; detail.append((15,"MACD Momentum Tăng","#00e676"))
    elif mh1<0 and ms1<0: score-=15; detail.append((15,"MACD Momentum Giảm","#ff5252"))

    if rsi1<30: score+=10; detail.append((10,"RSI Quá bán","#00e676"))
    elif rsi1>70: score-=10; detail.append((10,"RSI Quá mua","#ff5252"))

    div1, div5 = detect_rsi_divergence(df1), detect_rsi_divergence(df5)
    if div1["bull"] or div5["bull"]: score+=20; detail.append((20,"RSI Divergence TĂNG","#00e676"))
    elif div1["bear"] or div5["bear"]: score-=20; detail.append((20,"RSI Divergence GIẢM","#ff5252"))

    va = analyze_volume_accumulation(df1)
    if va["bias"]=="BULL": score+=10; detail.append((10,"Volume Tích Lũy Mua","#00e676"))
    elif va["bias"]=="BEAR": score-=10; detail.append((10,"Volume Phân Phối Bán","#ff5252"))

    if vwap1>0:
        if c1>vwap1*1.001: score+=10; detail.append((10,"Giá > VWAP","#00e676"))
        elif c1<vwap1*0.999: score-=10; detail.append((10,"Giá < VWAP","#ff5252"))

    pats = detect_candle_patterns(df1)
    ps = sum(15 if p["bias"]=="BULL" else -15 if p["bias"]=="BEAR" else 0 for p in pats)
    if ps>0: score+=min(ps,15); detail.append((min(ps,15),"Mẫu nến TĂNG","#00e676"))
    elif ps<0: score-=min(abs(ps),15); detail.append((min(abs(ps),15),"Mẫu nến GIẢM","#ff5252"))

    score = max(-100, min(100, score))
    if score>=70: rec, css, c, rdesc = "LONG MẠNH", "rec-strong-long", "#00e676", "Xác suất tăng mạnh, ưu tiên vào lệnh pullback."
    elif score>=40: rec, css, c, rdesc = "NGHIÊNG LONG", "rec-watch", "#ffd600", "Thiên hướng tăng, chờ tín hiệu xác nhận."
    elif score<=-70: rec, css, c, rdesc = "SHORT MẠNH", "rec-strong-short", "#ff5252", "Xác suất giảm mạnh, ưu tiên lệnh hồi."
    elif score<=-40: rec, css, c, rdesc = "NGHIÊNG SHORT", "rec-watch", "#ffd600", "Thiên hướng giảm, chờ xác nhận."
    else: rec, css, c, rdesc = "TRUNG TÍNH", "rec-neutral", "#475569", "Không rõ xu hướng, đứng ngoài."

    return {"score":score, "rec":rec, "rec_css":css, "rec_color":c, "rec_desc":rdesc, "detail":detail, "patterns":pats, "div1":div1, "div5":div5, "va":va}

def compute_forecast(df1: pd.DataFrame, df5: pd.DataFrame) -> dict:
    factors = []
    adx_now, adx_prev = df5["adx"].iloc[-1], df5["adx"].iloc[-6] if len(df5)>6 else df5["adx"].iloc[-1]
    di5p, di5n = df5["di_pos"].iloc[-1], df5["di_neg"].iloc[-1]
    if adx_now > adx_prev+2 and adx_now>18: factors.append({"label":"ADX Tăng dần","bias":"UP" if di5p>di5n else "DOWN","weight":20,"desc":"Trend đang hình thành"})
    
    div = detect_rsi_divergence(df5, 40)
    if div["bull"]: factors.append({"label":"RSI Divergence","bias":"UP","weight":25,"desc":div["desc"]})
    elif div["bear"]: factors.append({"label":"RSI Divergence","bias":"DOWN","weight":25,"desc":div["desc"]})

    bb_w, hist_bw = df5["bb_width"].iloc[-1], df5["bb_width"].tail(60)
    if len(hist_bw)>15 and bb_w < hist_bw.quantile(0.15): factors.append({"label":"BB Squeeze","bias":"UP" if df5["ema9"].iloc[-1]>df5["ema21"].iloc[-1] else "DOWN","weight":20,"desc":"Sắp có Breakout mạnh"})

    va = analyze_volume_accumulation(df5, 15)
    if va["bias"] in ["BULL","BEAR"]: factors.append({"label":"Volume Flow","bias":"UP" if va["bias"]=="BULL" else "DOWN","weight":15,"desc":va["desc"]})

    ms = df5["macd_slope"].iloc[-1]
    if ms>0.05: factors.append({"label":"MACD Slope Tăng","bias":"UP","weight":20,"desc":"Momentum lên"})
    elif ms<-0.05: factors.append({"label":"MACD Slope Giảm","bias":"DOWN","weight":20,"desc":"Momentum xuống"})

    us = sum(f["weight"] for f in factors if f["bias"]=="UP")
    ds = sum(f["weight"] for f in factors if f["bias"]=="DOWN")
    tot = us + ds + 1e-9; up = us/tot*100; dn = ds/tot*100

    if up>=70: v, vc, vd = "TĂNG MẠNH", "#00e676", f"Xác suất TĂNG: {up:.0f}%"
    elif dn>=70: v, vc, vd = "GIẢM MẠNH", "#ff5252", f"Xác suất GIẢM: {dn:.0f}%"
    elif up>=55: v, vc, vd = "HƠI TĂNG", "#ffd600", f"Nghiêng TĂNG: {up:.0f}%"
    elif dn>=55: v, vc, vd = "HƠI GIẢM", "#ffd600", f"Nghiêng GIẢM: {dn:.0f}%"
    else: v, vc, vd = "TRUNG TÍNH", "#475569", "Chưa rõ xu hướng 3-5 phiên tới"

    return {"factors":factors,"up_prob":up,"down_prob":dn,"verdict":v,"verdict_color":vc,"verdict_desc":vd}

def compute_winrate() -> dict:
    closed = [t for t in st.session_state.trade_history if t["status"] == "CLOSED"]
    if not closed: return {"total":0,"wins":0,"losses":0,"win_rate":0,"total_pnl":0,"avg_win":0,"avg_loss":0,"expectancy":0,"profit_factor":0,"by_regime":{},"by_direction":{},"by_signal":{},"equity_curve":[],"max_drawdown":0,"consecutive_losses":0}
    wins = [t for t in closed if t.get("pnl_points",0)>0]; losses = [t for t in closed if t.get("pnl_points",0)<=0]
    total_pnl = sum(t.get("pnl_points",0) for t in closed)
    avg_win = float(np.mean([t["pnl_points"] for t in wins])) if wins else 0
    avg_loss = float(np.mean([t["pnl_points"] for t in losses])) if losses else 0
    win_rate = len(wins)/len(closed)*100
    gross_profit, gross_loss = sum(t["pnl_points"] for t in wins) if wins else 0, abs(sum(t["pnl_points"] for t in losses)) if losses else 1e-9
    pf = gross_profit/gross_loss
    exp = (win_rate/100*avg_win) + ((1-win_rate/100)*avg_loss)
    
    br, bd, bs = {}, {}, {}
    for t in closed:
        r, d, sc = t.get("regime","?"), t.get("direction","?"), t.get("score",0)
        bucket = "Score ≥70" if abs(sc)>=70 else ("Score 40-69" if abs(sc)>=40 else "Score <40")
        for dic, key in [(br,r), (bd,d), (bs,bucket)]:
            if key not in dic: dic[key] = {"wins":0,"total":0,"pnl":0}
            dic[key]["total"]+=1; dic[key]["pnl"]+=t.get("pnl_points",0)
            if t.get("pnl_points",0)>0: dic[key]["wins"]+=1
    for dic in [br,bd,bs]:
        for k in dic: dic[k]["wr"] = dic[k]["wins"]/dic[k]["total"]*100

    sc = sorted(closed, key=lambda x: x.get("exit_time","")); eq, run, peak, mdd, mcl, ccl = [], 0.0, 0.0, 0.0, 0, 0
    for t in sc:
        run += t.get("pnl_points",0); eq.append({"label":f"#{t['id']}","eq":run})
        if run>peak: peak=run
        mdd = max(mdd, peak-run)
        if t.get("pnl_points",0)<=0: ccl+=1; mcl=max(mcl,ccl)
        else: ccl=0
    return {"total":len(closed),"wins":len(wins),"losses":len(losses),"win_rate":win_rate,"total_pnl":total_pnl,"avg_win":avg_win,"avg_loss":avg_loss,"expectancy":exp,"profit_factor":pf,"by_regime":br,"by_direction":bd,"by_signal":bs,"equity_curve":eq,"max_drawdown":mdd,"consecutive_losses":mcl}

def detect_regime(df: pd.DataFrame) -> dict:
    last = df.iloc[-1]
    g = lambda col, d=0: float(last.get(col,d)) if not np.isnan(last.get(col,d)) else float(d)
    adx, dip, din, bbw = g("adx",20), g("di_pos",20), g("di_neg",20), g("bb_width",0.03)
    hist_bw = df["bb_width"].dropna().tail(50); sqz_thresh = hist_bw.quantile(0.15) if len(hist_bw)>10 else 0.0
    r = "SIDEWAY" if adx<22 else ("UPTREND" if dip>din else "DOWNTREND")
    s = "YẾU" if adx<18 else ("MẠNH" if adx>35 else "VỪA")
    return {"regime":r,"strength":s,"adx":adx,"di_pos":dip,"di_neg":din,"rsi":g("rsi",50),"ema9":g("ema9"),"ema21":g("ema21"),"bb_w":bbw,"sqz_thresh":sqz_thresh,"is_sqz":bbw<sqz_thresh,"atr":g("atr",2)}

# ══════════════════════════════════════════════════════════════
# CHART & ALERTS
# ══════════════════════════════════════════════════════════════
def push_alert(score: int, conf: dict, fc: dict, price: float, regime: str, threshold: int):
    if abs(score) < threshold: return
    prev = st.session_state.alert_last_score
    if abs(prev) >= threshold and (score>0) == (prev>0): return
    st.session_state.alert_last_score = score
    st.session_state.alert_history.insert(0, {"time": datetime.now(VN_TZ).strftime("%H:%M:%S"), "date": datetime.now(VN_TZ).strftime("%d/%m/%Y"), "score": score, "direction": "LONG" if score>0 else "SHORT", "rec": conf["rec"], "price": price, "regime": regime, "forecast": fc["verdict"], "up_prob": fc["up_prob"], "dn_prob": fc["down_prob"]})
    st.session_state.alert_history = st.session_state.alert_history[:100]

def build_chart(df, title, show_ema, show_bb, show_signals, show_trades, show_vwap, show_vwap_bands, show_patterns, score, pattern_history=None):
    df = df.dropna(subset=["ema21"]).iloc[-250:]
    BG, GR = "#080c18", "#1a2540"
    fig = make_subplots(rows=4, cols=1, shared_xaxes=True, row_heights=[0.52,0.14,0.17,0.17], vertical_spacing=0.008)

    fig.add_trace(go.Candlestick(x=df.index, open=df["open"], high=df["high"], low=df["low"], close=df["close"], increasing_line_color="#00e676", decreasing_line_color="#ff5252", increasing_fillcolor="#00e676", decreasing_fillcolor="#ff5252", name="OHLC"), row=1, col=1)

    if show_vwap and "vwap" in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df["vwap"], line=dict(color="#f59e0b", width=1.8, dash="dash"), name="VWAP"), row=1, col=1)
        if show_vwap_bands:
            fig.add_trace(go.Scatter(x=df.index, y=df["vwap_u2"], line=dict(color="#f97316", width=0.9, dash="dot")), row=1, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df["vwap_l2"], line=dict(color="#38bdf8", width=0.9, dash="dot"), fill="tonexty", fillcolor="rgba(249,115,22,0.04)"), row=1, col=1)

    if show_patterns and pattern_history:
        dft = set(df.index)
        for b, s, c, l in [("BULL","triangle-up","#00c853","Mẫu TĂNG"),("BEAR","triangle-down","#d50000","Mẫu GIẢM")]:
            grp = [p for p in pattern_history if p["bias"]==b and p["time"] in dft]
            if grp: fig.add_trace(go.Scatter(x=[p["time"] for p in grp], y=[p["chart_y"] for p in grp], mode="markers+text", marker=dict(symbol=s, size=13, color=c, line=dict(color=BG,width=1.5)), text=[p["name"][:4] for p in grp], textposition="bottom center" if b=="BULL" else "top center", textfont=dict(size=8,color=c), hoverinfo="text"), row=1, col=1)

    if show_bb:
        fig.add_trace(go.Scatter(x=df.index, y=df["bb_upper"], line=dict(color="#475569",width=1,dash="dot")), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df["bb_lower"], line=dict(color="#475569",width=1,dash="dot"), fill="tonexty", fillcolor="rgba(71,85,105,0.07)"), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df["bb_mid"], line=dict(color="#334155",width=0.8)), row=1, col=1)

    if show_ema:
        for c_, co_, l in [("ema9","#f59e0b","EMA9"),("ema21","#38bdf8","EMA21"),("ema50","#a78bfa","EMA50")]:
            fig.add_trace(go.Scatter(x=df.index, y=df[c_], line=dict(color=co_, width=1.5), name=l), row=1, col=1)

    if show_trades:
        for t in st.session_state.trade_history:
            if t["status"]=="OPEN":
                dc = "#00e676" if t["direction"]=="LONG" else "#ff5252"
                fig.add_hline(y=t["entry"],line_color=dc,line_width=1.5,row=1,col=1)
                for lv in [t["tp1"],t["tp2"],t["tp3"]]: fig.add_hline(y=lv,line_color="#00e676",line_dash="dash",row=1,col=1)
                fig.add_hline(y=t["sl"],line_color="#ff5252",line_dash="dash",row=1,col=1)

    fig.add_trace(go.Bar(x=df.index, y=df["volume"], marker_color=["rgba(0,230,118,0.55)" if c>=o else "rgba(255,82,82,0.55)" for c,o in zip(df["close"],df["open"])], showlegend=False), row=2, col=1)
    fig.add_trace(go.Bar(x=df.index, y=df["macd_hist"], marker_color=["#00e676" if v>=0 else "#ff5252" for v in df["macd_hist"]], showlegend=False), row=3, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df["macd"], line=dict(color="#38bdf8",width=1.2)), row=3, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df["macd_signal"], line=dict(color="#ffd600",width=1.2)), row=3, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df["rsi"], line=dict(color="#38bdf8",width=1.5)), row=4, col=1)
    fig.add_hline(y=70, line_color="#ff5252", line_dash="dot", row=4, col=1); fig.add_hline(y=30, line_color="#00e676", line_dash="dot", row=4, col=1)

    fig.update_layout(template="plotly_dark", paper_bgcolor=BG, plot_bgcolor=BG, margin=dict(l=0,r=0,t=32,b=0), height=600, title=dict(text=f"{title} | Score: {score:+d}", font=dict(family="JetBrains Mono",size=12,color="#00e676" if score>0 else "#ff5252"), x=0.01), xaxis_rangeslider_visible=False, hovermode="x unified", showlegend=False)
    for i in range(1,5): fig.update_xaxes(row=i,col=1,gridcolor=GR); fig.update_yaxes(row=i,col=1,gridcolor=GR,tickfont=dict(size=8,color="#475569"))
    return fig

# ══════════════════════════════════════════════════════════════
# ██ SIDEBAR
# ══════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown('<div style="font-family:JetBrains Mono;font-size:16px;font-weight:700;color:#38bdf8;padding:6px 0 14px">⚡ VN30F TERMINAL PRO MAX v3</div>', unsafe_allow_html=True)
    symbol = st.selectbox("Hợp đồng", ["VN30F1M","VN30F1Q","VN30F2Q"], index=0)

    if "VN30F1M" in symbol:
        _exp = get_vn30f1m_expiry_info()
        _ec = "#ff5252" if _exp["days_to"]<=3 else ("#ffd600" if _exp["days_to"]<=7 else "#38bdf8")
        st.markdown(f'<div style="background:#0c1020;border:1px solid #1a2540;border-left:3px solid {_ec};border-radius:6px;padding:8px;margin-bottom:10px;font-family:JetBrains Mono;font-size:10px;"><div style="color:{_ec};font-weight:700">📅 {_exp["contract_name"]}</div><div style="color:#64748b;margin-top:2px">Đáo hạn: <b style="color:{_ec}">{_exp["next_expiry"].strftime("%d/%m/%Y")}</b> (Còn {_exp["days_to"]}d)</div></div>', unsafe_allow_html=True)

    auto_refresh = st.toggle("🔄 Tự động cập nhật", value=True)
    refresh_sec  = st.slider("Chu kỳ (giây)", 10, 120, 30) if auto_refresh else 30

    st.markdown('<div class="sec-hdr" style="margin-top:14px">📊 BIỂU ĐỒ</div>', unsafe_allow_html=True)
    show_ema        = st.toggle("EMA 9/21/50", value=True)
    show_bb         = st.toggle("Bollinger Bands", value=True)
    show_signals    = st.toggle("Mũi tên tín hiệu", value=True)
    show_trades     = st.toggle("Đường Entry/TP/SL", value=True)
    show_vwap       = st.toggle("VWAP", value=True)
    show_vwap_bands = st.toggle("VWAP Bands (±1σ / ±2σ)", value=True)
    show_patterns   = st.toggle("🕯️ Mẫu nến trên chart", value=True)

    st.markdown('<div class="sec-hdr" style="margin-top:14px">🤖 BOT TỰ TÍNH RỦI RO</div>', unsafe_allow_html=True)
    lot_size  = st.number_input("Số hợp đồng", min_value=1, max_value=50, value=1)
    auto_sltp = st.toggle("Bot tự tính SL/TP theo ATR", value=True)
    if not auto_sltp:
        tp1_points, tp2_points, tp3_points = st.number_input("TP1", value=4.0), st.number_input("TP2", value=8.0), st.number_input("TP3", value=12.0)
        sl_points  = st.number_input("SL", value=4.0)

    auto_tp_target = st.selectbox("Bot đóng lệnh tại", ["TP1","TP2","TP3"], index=2)
    
    st.markdown("---")
    alert_threshold = st.slider("Ngưỡng Score Alert", 50, 90, 70, step=5)
    mute_alerts = st.toggle("🔕 Tắt banner cảnh báo", value=False)
    if st.button("🗑️ Xóa lịch sử lệnh", use_container_width=True): st.session_state.trade_history = []; st.rerun()

# ══════════════════════════════════════════════════════════════
# MAIN APP EXECUTION
# ══════════════════════════════════════════════════════════════
db1, db5 = smart_days_back(symbol, 1), smart_days_back(symbol, 5)

with st.spinner("Đang tải dữ liệu VN30F1M..."):
    df1_raw, df5_raw = fetch_data(symbol, 1, db1), fetch_data(symbol, 5, db5)

is_simulated = df1_raw.attrs.get("_simulated", False) or df5_raw.attrs.get("_simulated", False)

if is_simulated:
    st.warning("🖥️ **Đang dùng dữ liệu MÔ PHỎNG** do API thực trả về rỗng. (Đảm bảo đã cài `vnstock==0.2.8.2`)")

df1, df5 = add_indicators(df1_raw.copy()), add_indicators(df5_raw.copy())
current_price, prev_close = float(df1["close"].iloc[-1]), float(df1["close"].iloc[-2])
regime1, regime5 = detect_regime(df1), detect_regime(df5)
current_atr = regime5["atr"]

# Auto Manage Trades
for i, t in enumerate(st.session_state.trade_history):
    if t["status"] == "OPEN":
        tv = t[auto_tp_target.lower()]
        if t["direction"] == "LONG" and current_price >= tv: t.update({"status":"CLOSED", "exit_price":tv, "reason":f"🎯 Chạm {auto_tp_target}", "pnl_points":tv-t["entry"]}); t["pnl"]=t["pnl_points"]*t["size"]*100000
        elif t["direction"] == "LONG" and current_price <= t["sl"]: t.update({"status":"CLOSED", "exit_price":t["sl"], "reason":"🛡️ Cắt lỗ SL", "pnl_points":t["sl"]-t["entry"]}); t["pnl"]=t["pnl_points"]*t["size"]*100000
        elif t["direction"] == "SHORT" and current_price <= tv: t.update({"status":"CLOSED", "exit_price":tv, "reason":f"🎯 Chạm {auto_tp_target}", "pnl_points":t["entry"]-tv}); t["pnl"]=t["pnl_points"]*t["size"]*100000
        elif t["direction"] == "SHORT" and current_price >= t["sl"]: t.update({"status":"CLOSED", "exit_price":t["sl"], "reason":"🛡️ Cắt lỗ SL", "pnl_points":t["entry"]-t["sl"]}); t["pnl"]=t["pnl_points"]*t["size"]*100000

confluence = compute_confluence(df1, df5)
forecast   = compute_forecast(df1, df5)
score      = confluence["score"]

push_alert(score, confluence, forecast, current_price, regime5["regime"], alert_threshold)
pat_hist1, pat_hist5 = scan_pattern_history(df1, 120), scan_pattern_history(df5, 120)

# ── HEADER METRICS ──
h1,h2,h3,h4,h5,h6 = st.columns([2.2, 1.5, 1.4, 1.4, 1.4, 1.4])
pc = current_price - prev_close
h1.markdown(f'<div class="metric-box"><div class="metric-label">{symbol}</div><div class="metric-value white" style="font-size:26px">{current_price:.2f}</div><div style="font-size:12px;color:{"#00e676" if pc>=0 else "#ff5252"}">{"▲" if pc>=0 else "▼"} {pc:+.2f}</div></div>', unsafe_allow_html=True)
h2.markdown(f'<div class="metric-box"><div class="metric-label">Confluence Score</div><div class="metric-value" style="color:{"#00e676" if score>=40 else "#ff5252" if score<=-40 else "#ffd600"}">{score:+d}</div><div style="font-size:10px;color:#475569">{confluence["rec"]}</div></div>', unsafe_allow_html=True)
h3.markdown(f'<div class="metric-box"><div class="metric-label">Xu hướng 5P</div><div class="metric-value" style="color:{"#00e676" if regime5["regime"]=="UPTREND" else "#ff5252" if regime5["regime"]=="DOWNTREND" else "#ffd600"};font-size:14px">{regime5["regime"]}</div><div style="font-size:10px;color:#475569">ADX {regime5["adx"]:.1f}</div></div>', unsafe_allow_html=True)
h4.markdown(f'<div class="metric-box"><div class="metric-label">Dự báo 3-5 phiên</div><div class="metric-value" style="color:{forecast["verdict_color"]};font-size:14px">{forecast["verdict"]}</div><div style="font-size:10px;color:#475569">▲{forecast["up_prob"]:.0f}% ▼{forecast["down_prob"]:.0f}%</div></div>', unsafe_allow_html=True)
h5.markdown(f'<div class="metric-box"><div class="metric-label">RSI 1P</div><div class="metric-value {"green" if regime1["rsi"]<40 else "red" if regime1["rsi"]>60 else "yellow"}">{regime1["rsi"]:.1f}</div></div>', unsafe_allow_html=True)
vw = df1["vwap_dev_pct"].iloc[-1] if "vwap_dev_pct" in df1.columns else 0
h6.markdown(f'<div class="metric-box"><div class="metric-label">VWAP Dev %</div><div class="metric-value {"green" if vw>0 else "red"}">{vw:+.2f}%</div></div>', unsafe_allow_html=True)

# ── ALERT BANNER ──
if abs(score) >= alert_threshold and not mute_alerts:
    is_long = score > 0
    st.markdown(f"""<div class="{'alert-long' if is_long else 'alert-short'}"><div style="display:flex;justify-content:space-between;align-items:center;"><div><div style="font-size:22px;font-weight:800;color:{'#00e676' if is_long else '#ff5252'}">{'🚀' if is_long else '💥'} CẢNH BÁO: {confluence['rec']}</div><div style="font-size:12px;color:#94a3b8;margin-top:4px">{confluence['rec_desc']}</div></div><div style="font-size:28px;font-weight:800;color:{'#00e676' if is_long else '#ff5252'}">{score:+d}</div></div></div><div style="height:6px"></div>""", unsafe_allow_html=True)

# ── KHUYẾN NGHỊ & DỰ BÁO ──
st.markdown('<div class="sec-hdr">🤖 KHUYẾN NGHỊ HỆ THỐNG & DỰ BÁO</div>', unsafe_allow_html=True)
c_rec, c_fc = st.columns([1.5, 1])
with c_rec:
    st.markdown(f"""<div class="{confluence['rec_css']}"><div style="font-size:20px;font-weight:800;color:{confluence['rec_color']};margin-bottom:6px">{confluence['rec']}</div><div style="font-size:12px;color:#94a3b8">{confluence['rec_desc']}</div></div>""", unsafe_allow_html=True)
with c_fc:
    st.markdown(f"""<div style="background:#0f1626;border:1px solid #1a2540;border-radius:8px;padding:14px;font-family:JetBrains Mono"><div style="color:#38bdf8;font-size:11px;font-weight:700;margin-bottom:6px">DỰ BÁO 3-5 PHIÊN: {forecast['verdict']}</div><div style="color:#00e676;font-size:11px">▲ TĂNG {forecast['up_prob']:.0f}%</div><div style="background:#1a2540;height:6px;margin:2px 0 8px"><div style="height:6px;width:{forecast['up_prob']:.0f}%;background:#00e676"></div></div><div style="color:#ff5252;font-size:11px">▼ GIẢM {forecast['down_prob']:.0f}%</div><div style="background:#1a2540;height:6px;margin:2px 0"><div style="height:6px;width:{forecast['down_prob']:.0f}%;background:#ff5252"></div></div></div>""", unsafe_allow_html=True)

# ── REGIME BANNERS ──
c_r1, c_r5 = st.columns(2)
def reg_ban(r, lbl):
    css, icon, d = ({"UPTREND":("uptrend","🚀","Ưu tiên LONG"), "DOWNTREND":("downtrend","💥","Ưu tiên SHORT")}).get(r["regime"],("sideway","🔄","Đánh biên"))
    return f'<div class="signal-card {css}">{icon} [{lbl}] {r["regime"]} — {r["strength"]}<br><span style="font-size:10px;font-weight:400">{d} | ADX {r["adx"]:.1f} | DI+ {r["di_pos"]:.1f} DI- {r["di_neg"]:.1f}</span></div>'
with c_r1: st.markdown(reg_ban(regime1,"1 PHÚT"), unsafe_allow_html=True)
with c_r5: st.markdown(reg_ban(regime5,"5 PHÚT"), unsafe_allow_html=True)

# ── CHART & PANELS ──
chart_col, trade_col = st.columns([3.2, 1.2])

with chart_col:
    tab1, tab5, tab_pat, tab_wr = st.tabs(["📊 Biểu đồ 1P", "📊 Biểu đồ 5P", "🕯️ Mẫu Nến", "📈 Win Rate (Hiệu suất)"])
    with tab1: st.plotly_chart(build_chart(df1, "VN30F1M · 1P", show_ema, show_bb, show_signals, show_trades, show_vwap, show_vwap_bands, show_patterns, score, pat_hist1), use_container_width=True, config={"displayModeBar":False})
    with tab5: st.plotly_chart(build_chart(df5, "VN30F1M · 5P", show_ema, show_bb, show_signals, show_trades, show_vwap, show_vwap_bands, show_patterns, score, pat_hist5), use_container_width=True, config={"displayModeBar":False})
    
    with tab_pat:
        st.markdown('<div class="sec-hdr">MẪU NẾN ĐANG XUẤT HIỆN</div>', unsafe_allow_html=True)
        cur = [(p,"1P") for p in detect_candle_patterns(df1)] + [(p,"5P") for p in detect_candle_patterns(df5)]
        if cur:
            for p, tf in cur:
                bc = "#00e676" if p["bias"]=="BULL" else "#ff5252" if p["bias"]=="BEAR" else "#ffd600"
                st.markdown(f'<div style="background:#0f1626;border-left:3px solid {bc};padding:10px;margin-bottom:5px;font-family:JetBrains Mono;font-size:11px"><b style="color:{bc}">[{tf}] {p["name"]}</b> — {p["desc"]}<br>Tin cậy: {p["reliability"]}% (Chất lượng {p["quality"]})</div>', unsafe_allow_html=True)
        else: st.info("Không có mẫu nến đặc biệt ở nến hiện tại.")
        st.markdown('<div class="sec-hdr" style="margin-top:15px">LỊCH SỬ MẪU NẾN (120 NẾN GẦN NHẤT)</div>', unsafe_allow_html=True)
        all_h = sorted([(p,"1P") for p in pat_hist1] + [(p,"5P") for p in pat_hist5], key=lambda x: x[0]["time"], reverse=True)
        for p, tf in all_h[:20]:
            bc = "#00e676" if p["bias"]=="BULL" else "#ff5252" if p["bias"]=="BEAR" else "#ffd600"
            st.markdown(f'<div style="background:#0f1626;border-left:3px solid {bc};padding:8px;margin-bottom:3px;font-family:JetBrains Mono;font-size:11px"><span style="color:{bc}"><b>{p["name"]}</b></span> <span style="color:#64748b">[{tf}] {p["time"].strftime("%d/%m %H:%M")} | Độ tin cậy: {p["reliability"]}%</span></div>', unsafe_allow_html=True)

    with tab_wr:
        wr = compute_winrate()
        if wr["total"] == 0: st.info("Chưa có lệnh đóng.")
        else:
            c1,c2,c3,c4 = st.columns(4)
            c1.markdown(f'<div class="metric-box"><div class="metric-label">Win Rate</div><div class="metric-value" style="color:{"#00e676" if wr["win_rate"]>=50 else "#ff5252"}">{wr["win_rate"]:.1f}%</div></div>', unsafe_allow_html=True)
            c2.markdown(f'<div class="metric-box"><div class="metric-label">Tổng P&L</div><div class="metric-value" style="color:{"#00e676" if wr["total_pnl"]>=0 else "#ff5252"}">{wr["total_pnl"]:+.1f}đ</div></div>', unsafe_allow_html=True)
            c3.markdown(f'<div class="metric-box"><div class="metric-label">Profit Factor</div><div class="metric-value" style="color:{"#00e676" if wr["profit_factor"]>1 else "#ff5252"}">{wr["profit_factor"]:.2f}</div></div>', unsafe_allow_html=True)
            c4.markdown(f'<div class="metric-box"><div class="metric-label">Max Drawdown</div><div class="metric-value" style="color:#ff5252">{wr["max_drawdown"]:.1f}đ</div></div>', unsafe_allow_html=True)
            if wr["equity_curve"]:
                eq_df = pd.DataFrame(wr["equity_curve"])
                fig_eq = go.Figure(go.Scatter(x=eq_df["label"], y=eq_df["eq"], fill="tozeroy", fillcolor="rgba(0,230,118,0.08)", line=dict(color="#00e676")))
                fig_eq.update_layout(template="plotly_dark", paper_bgcolor="#080c18", plot_bgcolor="#080c18", margin=dict(l=0,r=0,t=28,b=0), height=200, title="Đường Vốn (Equity Curve)")
                st.plotly_chart(fig_eq, use_container_width=True, config={"displayModeBar":False})

with trade_col:
    st.markdown('<div class="sec-hdr">🔫 VÀO LỆNH & QUẢN LÝ</div>', unsafe_allow_html=True)
    active_sl = current_atr*1.0 if auto_sltp else sl_points
    risk = active_sl*lot_size*100000
    st.markdown(f'<div style="background:#0f1626;border-left:3px solid {"#ff5252" if risk>2000000 else "#ffd600"};border-radius:6px;padding:10px;margin-bottom:10px;font-family:JetBrains Mono;font-size:11px"><div style="color:#64748b">Rủi ro (SL): <b style="color:#ff5252">-{risk:,.0f} ₫</b></div></div>', unsafe_allow_html=True)

    if auto_sltp:
        tp1, tp2, tp3, sl = current_atr*1.0, current_atr*2.0, current_atr*3.0, current_atr*1.0
        st.markdown(f'<div style="background:#0f1626;border:1px dashed #38bdf8;border-radius:6px;padding:8px;margin-bottom:10px;font-family:JetBrains Mono;font-size:11px"><div style="color:#00e676">TP: +{tp1:.1f} | +{tp2:.1f} | +{tp3:.1f}</div><div style="color:#ff5252">SL: -{sl:.1f}</div></div>', unsafe_allow_html=True)
    else:
        tp1, tp2, tp3, sl = tp1_points, tp2_points, tp3_points, sl_points

    ep = st.number_input("Giá", value=float(current_price), step=0.1)
    c1, c2 = st.columns(2)
    if c1.button("🟢 BUY (LONG)", use_container_width=True):
        st.session_state.trade_history.insert(0, {"id":len(st.session_state.trade_history)+1,"date":datetime.now(VN_TZ).strftime("%d/%m"),"time":datetime.now(VN_TZ).strftime("%H:%M"),"direction":"LONG","entry":ep,"tp1":ep+tp1,"tp2":ep+tp2,"tp3":ep+tp3,"sl":ep-sl,"size":lot_size,"status":"OPEN","score":score,"regime":regime5["regime"]})
        st.rerun()
    if c2.button("🔴 SELL (SHORT)", use_container_width=True):
        st.session_state.trade_history.insert(0, {"id":len(st.session_state.trade_history)+1,"date":datetime.now(VN_TZ).strftime("%d/%m"),"time":datetime.now(VN_TZ).strftime("%H:%M"),"direction":"SHORT","entry":ep,"tp1":ep-tp1,"tp2":ep-tp2,"tp3":ep-tp3,"sl":ep+sl,"size":lot_size,"status":"OPEN","score":score,"regime":regime5["regime"]})
        st.rerun()

    st.markdown('<div style="font-size:11px;color:#94a3b8;font-family:JetBrains Mono;margin:12px 0 6px;font-weight:700">📋 LỆNH ĐANG MỞ</div>', unsafe_allow_html=True)
    for i, t in enumerate(st.session_state.trade_history):
        if t["status"] == "OPEN":
            live = (current_price-t["entry"]) * (1 if t["direction"]=="LONG" else -1)
            dc = "#00e676" if t["direction"]=="LONG" else "#ff5252"
            st.markdown(f'<div style="background:#0f1626;border-left:2px solid {dc};padding:8px;margin-bottom:5px;font-size:10px;font-family:JetBrains Mono"><b style="color:{dc}">#{t["id"]} {t["direction"]}</b> | Entry: {t["entry"]:.2f} <br>Lãi/Lỗ: <span style="color:{"#00e676" if live>=0 else "#ff5252"}">{live:+.1f}</span></div>', unsafe_allow_html=True)
            if st.button(f"Đóng #{t['id']}", key=f"cl_{i}"):
                t.update({"status":"CLOSED", "exit_price":current_price, "reason":"Đóng thủ công", "exit_time":datetime.now(VN_TZ).strftime("%H:%M"), "pnl_points":live}); t["pnl"]=live*t["size"]*100000; st.rerun()

# ══════════════════════════════════════════════════════════════
# FOOTER & LOG
# ══════════════════════════════════════════════════════════════
st.markdown("<hr>", unsafe_allow_html=True)
st.markdown('<div class="sec-hdr">📔 NHẬT KÝ LỆNH ĐÃ ĐÓNG</div>', unsafe_allow_html=True)
closed = [t for t in st.session_state.trade_history if t["status"] == "CLOSED"]
if closed:
    st.dataframe(pd.DataFrame([{"Mã":f"#{t['id']}","Lệnh":"🟢 LONG" if t["direction"]=="LONG" else "🔴 SHORT","Vào":f"{t['date']} {t['time']}","Ra":t["exit_time"],"Entry":f"{t['entry']:.1f}","Exit":f"{t['exit_price']:.1f}","Lãi/Lỗ":f"{t['pnl_points']:+.1f}đ","Tiền VNĐ":f"{t.get('pnl',0):+,.0f} ₫","Ghi chú":t["reason"]} for t in closed]), use_container_width=True, hide_index=True)

fl, fr = st.columns([4,1])
fl.markdown(f'<div style="font-size:10px;color:#334155;font-family:JetBrains Mono">VN30F Terminal PRO MAX v3 · {"🖥️ Mô phỏng" if is_simulated else "📡 API Thực"} · {"● Đang GD" if is_trading_hours() else "○ Ngoài giờ"} · {datetime.now(VN_TZ).strftime("%d/%m/%Y %H:%M:%S")}</div>', unsafe_allow_html=True)
if auto_refresh:
    rem = max(0, refresh_sec-(datetime.now(VN_TZ)-st.session_state.last_refresh).seconds)
    fr.markdown(f'<div style="font-size:10px;color:#38bdf8;font-family:JetBrains Mono;text-align:right">🔄 {rem}s</div>', unsafe_allow_html=True)
    if (datetime.now(VN_TZ)-st.session_state.last_refresh).seconds >= refresh_sec: st.session_state.last_refresh = datetime.now(VN_TZ); st.rerun()
    time.sleep(1); st.rerun()
