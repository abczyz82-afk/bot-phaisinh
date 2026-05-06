import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from vnstock import stock_historical_data
from datetime import datetime, timedelta
from ta.trend import EMAIndicator, MACD, ADXIndicator
from ta.momentum import RSIIndicator
from ta.volatility import BollingerBands

# --- CẤU HÌNH TRANG WEB ---
st.set_page_config(page_title="Hệ Sinh Thái Trading Cá Nhân", layout="wide", page_icon="📈")
st.title("⚡ TRADING DASHBOARD TỔNG HỢP")

# --- SIDEBAR (THANH ĐIỀU KHIỂN BÊN TRÁI) ---
st.sidebar.header("🛠️ Tùy chỉnh tham số Cơ bản")
symbol = st.sidebar.text_input("Mã cổ phiếu cơ sở (VD: DGW, PLX, HDB):", "DGW").upper()
days_to_lookback = st.sidebar.slider("Số ngày xem lịch sử (Cơ sở):", 30, 365, 90)

if st.sidebar.button("🔄 Cập nhật dữ liệu mới nhất"):
    st.cache_data.clear()

st.sidebar.markdown("---")
st.sidebar.header("👑 Cấu hình Bot Pro (Pine Script)")
with st.sidebar.expander("Nhấn để mở cấu hình thông số", expanded=False):
    c1, c2 = st.columns(2)
    lenFast = c1.number_input("EMA Nhanh", value=9, min_value=1)
    lenSlow = c2.number_input("EMA Chậm", value=21, min_value=2)
    lenRsi = c1.number_input("Chu kỳ RSI", value=14, min_value=2)
    lenAtr = c2.number_input("Chu kỳ ATR", value=14, min_value=2)
    
    st.markdown("**Hệ số nhân ATR (Chốt lời / Cắt lỗ):**")
    c3, c4 = st.columns(2)
    tp1_mult = c3.number_input("Hệ số TP1", value=1.5, step=0.1)
    tp2_mult = c4.number_input("Hệ số TP2", value=2.5, step=0.1)
    tp3_mult = c3.number_input("Hệ số TP3", value=4.0, step=0.1)
    sl_mult = c4.number_input("Hệ số SL", value=1.5, step=0.1)

# --- HÀM XỬ LÝ DỮ LIỆU CƠ SỞ ---
@st.cache_data(ttl=60, show_spinner=False)
def get_stock_data(ticker, days):
    today = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    try:
        df = stock_historical_data(symbol=ticker, start_date=start_date, end_date=today, resolution='1D', type='stock')
        if df is None or df.empty: 
            return None
        return df.sort_values(by='time').reset_index(drop=True)
    except Exception as e:
        st.sidebar.error(f"Lỗi tải mã {ticker}: {str(e)}")
        return None

# --- HÀM XỬ LÝ DỮ LIỆU PHÁI SINH PRO ---
@st.cache_data(ttl=60, show_spinner=False)
def get_ps_pro_data(resolution_val, days_back, f_ema, s_ema, rsi_l, atr_l, tp1_m, tp2_m, tp3_m, sl_m):
    today = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")
    try:
        df = stock_historical_data(symbol='VN30F1M', start_date=start_date, end_date=today, resolution=resolution_val, type='derivative')
        if df is None or df.empty:
            return None
        
        df = df.sort_values(by='time').reset_index(drop=True)
        if len(df) < 50: # Đảm bảo đủ nến cho EMA50
            return None

        # 1. Tính toán EMA
        df['EMA9'] = EMAIndicator(close=df['close'], window=f_ema).ema_indicator()
        df['EMA21'] = EMAIndicator(close=df['close'], window=s_ema).ema_indicator()
        df['EMA50'] = EMAIndicator(close=df['close'], window=50).ema_indicator()

        # 2. Tính toán RSI & MACD
        df['RSI'] = RSIIndicator(close=df['close'], window=rsi_l).rsi()
        macd = MACD(close=df['close'])
        df['MACD_Hist'] = macd.macd_diff()

        # 3. Tính toán Bollinger Bands & Vol MA
        bb = BollingerBands(close=df['close'], window=20, window_dev=2)
        df['BB_Upper'] = bb.bollinger_hband()
        df['BB_Lower'] = bb.bollinger_lband()
        df['BB_Width'] = bb.bollinger_wband()
        df['Vol_MA'] = df['volume'].rolling(window=20).mean()

        # 4. Tính toán ADX & Phân loại Regime
        adx = ADXIndicator(high=df['high'], low=df['low'], close=df['close'], window=14)
        df['ADX'] = adx.adx()
        df['DI+'] = adx.adx_pos()
        df['DI-'] = adx.adx_neg()

        cond_regime = [
            (df['ADX'] < 22),
            (df['DI+'] > df['DI-']) & (df['ADX'] >= 22),
            (df['DI-'] > df['DI+']) & (df['ADX'] >= 22)
        ]
        choices_regime = ['🔄 SIDEWAY', '🚀 UPTREND', '💥 DOWNTREND']
        df['Regime'] = np.select(cond_regime, default='KHÔNG RÕ', condlist=cond_regime, choicelist=choices_regime)

        # 5. ATR để tính Chốt lời / Cắt lỗ
        tr1 = df['high'] - df['low']
        tr2 = (df['high'] - df['close'].shift(1)).abs()
        tr3 = (df['low'] - df['close'].shift(1)).abs()
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        df['ATR'] = tr.ewm(alpha=1/atr_l, adjust=False).mean()

        # 6. Quét Tín hiệu Real-time
        df['Tín Hiệu'] = '-'
        df['Long_Signal'] = False
        df['Short_Signal'] = False
        df['TP1'] = '-'
        df['TP2'] = '-'
        df['TP3'] = '-'
        df['SL'] = '-'

        p15_bbw = df['BB_Width'].quantile(0.15)

        for i in range(1, len(df)):
            signals = []
            is_long = False
            is_short = False
            
            # Logic Tín hiệu
            ema_cross_up = df['EMA9'].iloc[i] > df['EMA21'].iloc[i] and df['EMA9'].iloc[i-1] <= df['EMA21'].iloc[i-1]
            ema_cross_down = df['EMA9'].iloc[i] < df['EMA21'].iloc[i] and df['EMA9'].iloc[i-1] >= df['EMA21'].iloc[i-1]
            ema_bull = df['EMA9'].iloc[i] > df['EMA21'].iloc[i] > df['EMA50'].iloc[i] and df['Regime'].iloc[i] == '🚀 UPTREND'
            
            rsi_os = df['RSI'].iloc[i] < 30
            rsi_ob = df['RSI'].iloc[i] > 70
            macd_up = df['MACD_Hist'].iloc[i] > 0 and df['MACD_Hist'].iloc[i-1] <= 0
            
            bb_breakup = df['close'].iloc[i] > df['BB_Upper'].iloc[i]
            bb_bounce = df['low'].iloc[i] <= df['BB_Lower'].iloc[i] and df['close'].iloc[i] > df['open'].iloc[i]
            bb_squeeze = df['BB_Width'].iloc[i] < p15_bbw
            vol_spike = df['volume'].iloc[i] > (2 * df['Vol_MA'].iloc[i])

            # Áp dụng Hành động
            if ema_cross_up: 
                signals.append("🟢 EMA 9x21 Cắt Lên")
                is_long = True
            if ema_cross_down: 
                signals.append("🔴 EMA 9x21 Cắt Xuống")
                is_short = True
            if ema_bull and not (df['EMA9'].iloc[i-1] > df['EMA21'].iloc[i-1] > df['EMA50'].iloc[i-1]):
                signals.append("🟢 EMA Xếp BULL")
                is_long = True
            if rsi_os: 
                signals.append("💎 RSI Quá Bán")
                is_long = True
            if rsi_ob: 
                signals.append("🔥 RSI Quá Mua")
                is_short = True
            if macd_up: 
                signals.append("📈 MACD Cắt Lên")
                is_long = True
            if bb_breakup: 
                signals.append("🚀 BB Break Up")
                is_long = True
            if bb_bounce: 
                signals.append("🟢 BB Bounce Up")
                is_long = True
            if bb_squeeze: 
                signals.append("⚡ BB Squeeze")
            if vol_spike: 
                signals.append("📊 Volume Spike")

            if signals:
                df.at[i, 'Tín Hiệu'] = " | ".join(signals)
            
            # Đánh dấu tín hiệu để tính ATR TP/SL
            if is_long: df.at[i, 'Long_Signal'] = True
            if is_short: df.at[i, 'Short_Signal'] = True

        # Áp dụng TP / SL cho các nến có tín hiệu Long/Short
        long_idx = df[df['Long_Signal'] == True].index
        if len(long_idx) > 0:
            df.loc[long_idx, 'TP1'] = round(df.loc[long_idx, 'close'] + (df.loc[long_idx, 'ATR'] * tp1_m), 1).astype(str)
            df.loc[long_idx, 'TP2'] = round(df.loc[long_idx, 'close'] + (df.loc[long_idx, 'ATR'] * tp2_m), 1).astype(str)
            df.loc[long_idx, 'TP3'] = round(df.loc[long_idx, 'close'] + (df.loc[long_idx, 'ATR'] * tp3_m), 1).astype(str)
            df.loc[long_idx, 'SL'] = round(df.loc[long_idx, 'close'] - (df.loc[long_idx, 'ATR'] * sl_m), 1).astype(str)

        short_idx = df[df['Short_Signal'] == True].index
        if len(short_idx) > 0:
            df.loc[short_idx, 'TP1'] = round(df.loc[short_idx, 'close'] - (df.loc[short_idx, 'ATR'] * tp1_m), 1).astype(str)
            df.loc[short_idx, 'TP2'] = round(df.loc[short_idx, 'close'] - (df.loc[short_idx, 'ATR'] * tp2_m), 1).astype(str)
            df.loc[short_idx, 'TP3'] = round(df.loc[short_idx, 'close'] - (df.loc[short_idx, 'ATR'] * tp3_m), 1).astype(str)
            df.loc[short_idx, 'SL'] = round(df.loc[short_idx, 'close'] + (df.loc[short_idx, 'ATR'] * sl_m), 1).astype(str)

        df['RSI'] = df['RSI'].round(2)
        return df
    except Exception as e:
        return f"LỖI API: {str(e)}"

# --- THUẬT TOÁN TÍNH TOÁN DÒNG TIỀN KHỐI NGOẠI ---
def calculate_foreign_flow(current_price, historical_daily_data):
    total_hold_vol = 0
    total_capital = 0  
    
    for day in historical_daily_data:
        net_vol = day['buy_vol'] - day['sell_vol'] 
        vwap = day['vwap'] 
        total_hold_vol += net_vol
        total_capital += (net_vol * vwap)
        
    avg_hold_price = total_capital / total_hold_vol if total_hold_vol != 0 else 0
    hold_type = "Long" if total_hold_vol > 0 else "Short"
    
    estimated_pnl_vnd = (current_price - avg_hold_price) * total_hold_vol * 100000
    estimated_pnl_ty = estimated_pnl_vnd / 1000000000  
    
    today_data = historical_daily_data[-1]
    today_net_vol = today_data['buy_vol'] - today_data['sell_vol']
    today_net_type = "Long" if today_net_vol > 0 else "Short"
    today_pnl = (current_price - today_data['vwap']) * today_net_vol * 100000 / 1000000000

    return {
        "today_net_vol": today_net_vol,
        "today_net_type": today_net_type,
        "today_pnl_ty": round(today_pnl, 1),
        "hold_vol": total_hold_vol,
        "hold_type": hold_type,
        "avg_hold_price": round(avg_hold_price, 1),
        "month_pnl_ty": round(estimated_pnl_ty, 1)
    }

# --- HÀM HIỂN THỊ GIAO DIỆN PHÁI SINH ---
def render_ps_bot(df_ps, timeframe_name):
    if isinstance(df_ps, str):
        st.error(f"Hệ thống API tải dữ liệu phái sinh đang quá tải. Chi tiết: {df_ps}")
        st.info("💡 Mẹo: Nhấn nút 'Cập nhật dữ liệu mới nhất' ở thanh menu bên trái để thử lại.")
        return

    if df_ps is not None and not df_ps.empty:
        df_ps['Datetime'] = pd.to_datetime(df_ps['time'])
        df_ps['DateOnly'] = df_ps['Datetime'].dt.date
        latest = df_ps.iloc[-1]
        latest_date = latest['DateOnly']
        
        past_df = df_ps[df_ps['DateOnly'] < latest_date]
        yesterday_close = past_df.iloc[-1]['close'] if not past_df.empty else df_ps.iloc[0]['close']
            
        change = latest['close'] - yesterday_close
        pct_change = (change / yesterday_close) * 100 if yesterday_close != 0 else 0

        col1, col2, col3 = st.columns([2, 1, 1])
        with col1:
            st.metric(label=f"Giá VN30F1M hiện tại", value=f"{latest['close']}", delta=f"{change:.1f} điểm ({pct_change:.2f}%) so với qua")
        with col2:
            st.metric(label="Thị trường (Regime)", value=latest['Regime'])
        with col3:
            st.metric(label="Chỉ số RSI", value=latest['RSI'])
            
        st.write(f"**🕒 Cập nhật nến lúc:** `{latest['time']}`")
        
        # Bảng thông báo quy tắc
        with st.expander("📖 HIỂN THỊ CHIẾN LƯỢC THEO REGIME", expanded=False):
            st.markdown("""
            **Chiến lược theo regime:**
            - 🔄 **SIDEWAY** (ADX<22): Canh BB Lower mua, BB Upper bán. SL 2-3 điểm.
            - 🚀 **UPTREND** (DI+>DI-): Chỉ LONG, pullback về EMA21. Ride trend.
            - 💥 **DOWNTREND** (DI->DI+): Chỉ SHORT, hồi về EMA21. Ride trend.
            - ⚡ **BB Squeeze**: Chờ Vol Spike xác nhận hướng → vào lệnh.
            """)
        
        st.divider()
        
        if latest['Long_Signal'] or latest['Short_Signal']:
            signal_type = "🟢 LONG" if latest['Long_Signal'] else "🔴 SHORT"
            st.success(f"### 🚨 PHÁT HIỆN TÍN HIỆU {signal_type} TẠI GIÁ {latest['close']}")
            st.write(f"**Nguyên nhân kích hoạt:** {latest['Tín Hiệu']}")
            
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("🎯 Chốt lời 1 (TP1)", latest['TP1'])
            c2.metric("🎯 Chốt lời 2 (TP2)", latest['TP2'])
            c3.metric("🚀 Chốt lời 3 (TP3)", latest['TP3'])
            c4.metric("🛡️ Dừng lỗ (SL)", latest['SL'])
        else:
            st.info("⚪ Hệ thống đang theo dõi. Chưa có điểm vào lệnh an toàn.")

        st.write("---")
        with st.expander(f"📜 XEM NHẬT KÝ CÁC LỆNH ĐÃ QUA ({timeframe_name})", expanded=False):
            history_df = df_ps[(df_ps['Long_Signal'] == True) | (df_ps['Short_Signal'] == True)].copy()
            if not history_df.empty:
                history_display = history_df[['time', 'Tín Hiệu', 'close', 'TP1', 'TP2', 'TP3', 'SL']].copy()
                history_display.rename(columns={'close': 'Điểm vào (Entry)', 'time': 'Thời gian xuất hiện lệnh'}, inplace=True)
                history_display = history_display.sort_values('Thời gian xuất hiện lệnh', ascending=False).reset_index(drop=True)
                st.dataframe(history_display, use_container_width=True)
            else:
                st.write("Chưa có tín hiệu BUY/SELL nào được ghi nhận trong khoảng thời gian này.")
        
        st.write("---")
        st.subheader(f"Bảng dữ liệu 20 nến gần nhất ({timeframe_name})")
        display_df = df_ps[['time', 'open', 'high', 'low', 'close', 'Regime', 'Tín Hiệu', 'TP1', 'TP2', 'TP3', 'SL']].tail(20)
        st.dataframe(display_df.sort_index(ascending=False), use_container_width=True)
    else:
        st.warning("Không có dữ liệu trả về từ API. Có thể ngoài giờ giao dịch.")

# --- HÀM HIỂN THỊ THỐNG KÊ DÒNG TIỀN PHÁI SINH ---
def render_market_flow(current_ps_price):
    st.subheader("📊 Thống kê Dòng tiền Phái Sinh")
    
    foreign_data_history = [
        {"date": "02/05", "buy_vol": 5000, "sell_vol": 3000, "vwap": 1230.5},
        {"date": "03/05", "buy_vol": 4000, "sell_vol": 2000, "vwap": 1240.0},
        {"date": "04/05", "buy_vol": 1000, "sell_vol": 2644, "vwap": 1245.5}, 
    ]
    f_result = calculate_foreign_flow(current_ps_price, foreign_data_history)
    
    data = {
        "date": datetime.now().strftime("%d/%m/%Y"),
        "prop": {"net": 405, "net_type": "Long", "daily_pnl": -2.1, "hold_vol": -1948, "hold_type": "Short", "avg_price": 1962.1, "month_pnl": -9.6},
        "retail": {"net": 1237, "net_type": "Long", "daily_pnl": -4.8, "hold_vol": -2097, "hold_type": "Short", "avg_price": 1962.6, "month_pnl": -54.2}
    }

    st.write(f"**Phái Sinh ngày {data['date']} (Cập nhật Real-time Lãi/Lỗ theo giá: {current_ps_price})**")
    
    f_icon = "🔴" if f_result['today_net_type'] == "Short" else "🟢"
    st.markdown(f"""
    {f_icon} **Hnay Tây {f_result['today_net_type']} ròng :** {f_result['today_net_vol']}HĐ ; lãi (lướt)/ngày : {f_result['today_pnl_ty']} tỷ.  
    **Hold:** {f_result['hold_vol']} {f_result['hold_type']}, giá vốn {f_result['avg_hold_price']}. Ước tính Lãi tháng này (Lướt+ Hold) **{f_result['month_pnl_ty']} tỷ**;
    """)
    st.markdown("---")

    p_icon = "🔴" if data['prop']['net_type'] == "Short" else "✅"
    st.markdown(f"""
    {p_icon} **Hnay TD {data['prop']['net_type']} :** {data['prop']['net']}HĐ ; lỗ/ngày : {data['prop']['daily_pnl']} tỷ.  
    **Hold:** {data['prop']['hold_vol']} {data['prop']['hold_type']}, giá vốn {data['prop']['avg_price']}. Ước tính Lỗ tháng này (Lướt+ Hold) **{data['prop']['month_pnl']} tỷ**;
    """)
    st.markdown("---")

    r_icon = "🔴" if data['retail']['net_type'] == "Short" else "✅"
    st.markdown(f"""
    {r_icon} **Hnay CN Nhỏ lẻ # {data['retail']['net_type']} :** {data['retail']['net']}HĐ ; lỗ/ngày : {data['retail']['daily_pnl']} tỷ.  
    **Hold:** {data['retail']['hold_vol']} {data['retail']['hold_type']}, giá vốn {data['retail']['avg_price']}. Ước tính Lỗ tháng này (Lướt+ Hold) **{data['retail']['month_pnl']} tỷ**;
    """)

# --- TẠO 4 TABS GIAO DIỆN CHÍNH ---
tab1, tab2, tab3, tab4 = st.tabs(["📈 CƠ SỞ", "👑 PS PRO (1 Phút)", "👑 PS PRO (5 Phút)", "📊 DÒNG TIỀN"])

# TAB 1: CỔ PHIẾU CƠ SỞ
with tab1:
    df_stock = get_stock_data(symbol, days_to_lookback)
    if df_stock is not None and len(df_stock) >= 2:
        latest_close = df_stock['close'].iloc[-1]
        prev_close = df_stock['close'].iloc[-2]
        change = latest_close - prev_close
        pct_change = (change / prev_close) * 100
        
        col_info, col_chart = st.columns([1, 4])
        with col_info:
            st.subheader("Thông tin")
            st.metric(label=f"Giá {symbol}", value=f"{latest_close:,.0f} ₫", delta=f"{change:,.0f} ₫ ({pct_change:.2f}%)")
            st.write(f"**Ngày:** `{df_stock['time'].iloc[-1]}`")
            st.write("---")
            st.write("**Bảng 20 phiên gần nhất:**")
            st.dataframe(df_stock[['time', 'close']].tail(20), use_container_width=True)
            
        with col_chart:
            st.subheader(f"Biểu đồ kỹ thuật: {symbol}")
            fig = go.Figure(data=[go.Candlestick(x=df_stock['time'], open=df_stock['open'], high=df_stock['high'], low=df_stock['low'], close=df_stock['close'], name=symbol)])
            fig.update_layout(height=550, xaxis_rangeslider_visible=False, template="plotly_dark", margin=dict(l=0, r=0, t=30, b=0))
            st.plotly_chart(fig, use_container_width=True)
    else: 
        st.error("Lỗi dữ liệu cổ phiếu cơ sở hoặc đang bị từ chối truy cập API.")

# TAB 2 & 3: PHÁI SINH PRO
with tab2:
    st.subheader("Hệ thống Bot VN30F1M - Khung 1 Phút (Bản PRO)")
    df_1m_pro = get_ps_pro_data('1', 5, lenFast, lenSlow, lenRsi, lenAtr, tp1_mult, tp2_mult, tp3_mult, sl_mult)
    render_ps_bot(df_1m_pro, "1 Phút PRO")

with tab3:
    st.subheader("Hệ thống Bot VN30F1M - Khung 5 Phút (Bản PRO)")
    df_5m_pro = get_ps_pro_data('5', 14, lenFast, lenSlow, lenRsi, lenAtr, tp1_mult, tp2_mult, tp3_mult, sl_mult)
    render_ps_bot(df_5m_pro, "5 Phút PRO")

# TAB 4: THỐNG KÊ DÒNG TIỀN
with tab4:
    current_ps_price = 1250.0  
    if 'df_1m_pro' in locals() and isinstance(df_1m_pro, pd.DataFrame) and not df_1m_pro.empty:
        current_ps_price = df_1m_pro.iloc[-1]['close']
        
    render_market_flow(current_ps_price)
    
    st.info("💡 Lưu ý: Hệ thống đang chạy bằng thuật toán tính toán Real-time giá vốn dựa trên tập dữ liệu Khối ngoại mô phỏng. Để có số liệu thực tế chính xác từng ngày, bạn hãy nhập tay dữ liệu Mua/Bán/VWAP vào list `foreign_data_history` bên trong hàm `render_market_flow` mỗi cuối ngày.")
