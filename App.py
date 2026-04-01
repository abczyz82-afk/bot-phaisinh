import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from vnstock import stock_historical_data
from datetime import datetime, timedelta

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

# --- HÀM XỬ LÝ DỮ LIỆU PHÁI SINH PRO (TỰ TÍNH TOÁN, KHÔNG DÙNG PANDAS-TA) ---
@st.cache_data(ttl=60, show_spinner=False)
def get_ps_pro_data(resolution_val, days_back, f_ema, s_ema, rsi_l, atr_l, tp1_m, tp2_m, tp3_m, sl_m):
    today = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")
    try:
        df = stock_historical_data(symbol='VN30F1M', start_date=start_date, end_date=today, resolution=resolution_val, type='derivative')
        if df is None or df.empty:
            return None
        
        df = df.sort_values(by='time').reset_index(drop=True)
        if len(df) < max(f_ema, s_ema, rsi_l, atr_l):
            return None

        # 1. Tự tính EMA Nhanh và Chậm
        df['EMA_Fast'] = df['close'].ewm(span=f_ema, adjust=False).mean()
        df['EMA_Slow'] = df['close'].ewm(span=s_ema, adjust=False).mean()

        # 2. Tự tính RSI (Chuẩn RMA của TradingView)
        delta = df['close'].diff()
        gain = delta.where(delta > 0, 0.0).ewm(alpha=1/rsi_l, adjust=False).mean()
        loss = (-delta.where(delta < 0, 0.0)).ewm(alpha=1/rsi_l, adjust=False).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))

        # 3. Tự tính ATR (Chuẩn RMA của TradingView)
        tr1 = df['high'] - df['low']
        tr2 = (df['high'] - df['close'].shift(1)).abs()
        tr3 = (df['low'] - df['close'].shift(1)).abs()
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        df['ATR'] = tr.ewm(alpha=1/atr_l, adjust=False).mean()

        # Điều kiện Signal
        df['EMA_Fast_Prev'] = df['EMA_Fast'].shift(1)
        df['EMA_Slow_Prev'] = df['EMA_Slow'].shift(1)

        df['Long_Signal'] = (df['EMA_Fast'] > df['EMA_Slow']) & (df['EMA_Fast_Prev'] <= df['EMA_Slow_Prev']) & (df['RSI'] > 50)
        df['Short_Signal'] = (df['EMA_Fast'] < df['EMA_Slow']) & (df['EMA_Fast_Prev'] >= df['EMA_Slow_Prev']) & (df['RSI'] < 50)
        
        df['Tín Hiệu'] = '-'
        df['TP1'] = '-'
        df['TP2'] = '-'
        df['TP3'] = '-'
        df['SL'] = '-'

        # Áp dụng TP/SL LONG
        long_idx = df[df['Long_Signal'] == True].index
        if len(long_idx) > 0:
            df.loc[long_idx, 'Tín Hiệu'] = '🟢 LONG'
            df.loc[long_idx, 'TP1'] = round(df.loc[long_idx, 'close'] + (df.loc[long_idx, 'ATR'] * tp1_m), 1)
            df.loc[long_idx, 'TP2'] = round(df.loc[long_idx, 'close'] + (df.loc[long_idx, 'ATR'] * tp2_m), 1)
            df.loc[long_idx, 'TP3'] = round(df.loc[long_idx, 'close'] + (df.loc[long_idx, 'ATR'] * tp3_m), 1)
            df.loc[long_idx, 'SL'] = round(df.loc[long_idx, 'close'] - (df.loc[long_idx, 'ATR'] * sl_m), 1)

        # Áp dụng TP/SL SHORT
        short_idx = df[df['Short_Signal'] == True].index
        if len(short_idx) > 0:
            df.loc[short_idx, 'Tín Hiệu'] = '🔴 SHORT'
            df.loc[short_idx, 'TP1'] = round(df.loc[short_idx, 'close'] - (df.loc[short_idx, 'ATR'] * tp1_m), 1)
            df.loc[short_idx, 'TP2'] = round(df.loc[short_idx, 'close'] - (df.loc[short_idx, 'ATR'] * tp2_m), 1)
            df.loc[short_idx, 'TP3'] = round(df.loc[short_idx, 'close'] - (df.loc[short_idx, 'ATR'] * tp3_m), 1)
            df.loc[short_idx, 'SL'] = round(df.loc[short_idx, 'close'] + (df.loc[short_idx, 'ATR'] * sl_m), 1)

        df['RSI'] = df['RSI'].round(2)
        return df
    except Exception as e:
        return f"LỖI: {str(e)}"

# --- HÀM HIỂN THỊ GIAO DIỆN PHÁI SINH ---
def render_ps_bot(df_ps, timeframe_name):
    if isinstance(df_ps, str):
        st.error(f"Lỗi hệ thống: {df_ps}")
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

        col1, col2 = st.columns([1, 2])
        with col1:
            st.metric(label=f"Giá VN30F1M hiện tại", value=f"{latest['close']}", delta=f"{change:.1f} điểm ({pct_change:.2f}%) so với hôm qua")
        with col2:
            st.write("")
            st.write(f"**🕒 Cập nhật nến lúc:** `{latest['time']}`")
            st.caption("ℹ️ Đang chạy với cấu hình tham số tùy chỉnh từ Sidebar.")
        
        st.divider()
        
        if latest['Long_Signal'] or latest['Short_Signal']:
            signal_type = "🟢 LONG" if latest['Long_Signal'] else "🔴 SHORT"
            st.success(f"### 🚨 PHÁT HIỆN TÍN HIỆU {signal_type} TẠI GIÁ {latest['close']}")
            
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
                st.write("Chưa có tín hiệu nào được ghi nhận trong khoảng thời gian này.")
        
        st.write("---")
        st.subheader(f"Bảng dữ liệu 20 nến gần nhất ({timeframe_name})")
