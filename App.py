import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import pandas_ta as ta
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

# --- HÀM XỬ LÝ DỮ LIỆU PHÁI SINH PRO ---
@st.cache_data(ttl=60, show_spinner=False)
def get_ps_pro_data(resolution_val, days_back, f_ema, s_ema, rsi_l, atr_l, tp1_m, tp2_m, tp3_m, sl_m):
    today = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")
    try:
        # Kéo dữ liệu
        df = stock_historical_data(symbol='VN30F1M', start_date=start_date, end_date=today, resolution=resolution_val, type='derivative')
        if df is None or df.empty:
            return None
        
        df = df.sort_values(by='time').reset_index(drop=True)
        
        # Bỏ qua nếu dữ liệu quá ngắn không đủ tính toán
        if len(df) < max(f_ema, s_ema, rsi_l, atr_l):
            return None

        # Tính toán chỉ báo
        df['EMA_Fast'] = ta.ema(df['close'], length=f_ema)
        df['EMA_Slow'] = ta.ema(df['close'], length=s_ema)
        df['RSI'] = ta.rsi(df['close'], length=rsi_l)
        df['ATR'] = ta.atr(df['high'], df['low'], df['close'], length=atr_l)

        df['EMA_Fast_Prev'] = df['EMA_Fast'].shift(1)
        df['EMA_Slow_Prev'] = df['EMA_Slow'].shift(1)

        df['Long_Signal'] = (df['EMA_Fast'] > df['EMA_Slow']) & (df['EMA_Fast_Prev'] <= df['EMA_Slow_Prev']) & (df['RSI'] > 50)
        df['Short_Signal'] = (df['EMA_Fast'] < df['EMA_Slow']) & (df['EMA_Fast_Prev'] >= df['EMA_Slow_Prev']) & (df['RSI'] < 50)
        
        # Điền mặc định
        df['Tín Hiệu'] = '-'
        df['TP1'] = '-'
        df['TP2'] = '-'
        df['TP3'] = '-'
        df['SL'] = '-'

        # Áp dụng TP/SL cho các vị trí có tín hiệu LONG
        long_idx = df[df['Long_Signal'] == True].index
        if len(long_idx) > 0:
            df.loc[long_idx, 'Tín Hiệu'] = '🟢 LONG'
            df.loc[long_idx, 'TP1'] = round(df.loc[long_idx, 'close'] + (df.loc[long_idx, 'ATR'] * tp1_m), 1)
            df.loc[long_idx, 'TP2'] = round(df.loc[long_idx, 'close'] + (df.loc[long_idx, 'ATR'] * tp2_m), 1)
            df.loc[long_idx, 'TP3'] = round(df.loc[long_idx, 'close'] + (df.loc[long_idx, 'ATR'] * tp3_m), 1)
            df.loc[long_idx, 'SL'] = round(df.loc[long_idx, 'close'] - (df.loc[long_idx, 'ATR'] * sl_m), 1)

        # Áp dụng TP/SL cho các vị trí có tín hiệu SHORT
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
        st.error(f"Hệ thống API tải dữ liệu phái sinh đang có vấn đề. Chi tiết: {df_ps}")
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
        display_df = df_ps[['time', 'open', 'high', 'low', 'close', 'RSI', 'Tín Hiệu', 'TP1', 'TP2', 'TP3', 'SL']].tail(20)
        st.dataframe(display_df, use_container_width=True)
    else:
        st.warning("Không có dữ liệu trả về từ API. API có thể đang bảo trì hoặc ngoài giờ giao dịch.")

# --- TẠO 3 TABS GIAO DIỆN CHÍNH ---
tab1, tab2, tab3 = st.tabs([
    "📈 CƠ SỞ", 
    "👑 PS PRO (1 Phút)", 
    "👑 PS PRO (5 Phút)"
])

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
        st.error("Lỗi dữ liệu cổ phiếu cơ sở. Vui lòng kiểm tra lại mã hoặc kết nối mạng.")

# TAB 2: PHÁI SINH PRO (1 Phút) - Giữ nguyên 5 ngày
with tab2:
    st.subheader("Hệ thống Bot VN30F1M - Khung 1 Phút (Bản PRO)")
    df_1m_pro = get_ps_pro_data('1', 5, lenFast, lenSlow, lenRsi, lenAtr, tp1_mult, tp2_mult, tp3_mult, sl_mult)
    render_ps_bot(df_1m_pro, "1 Phút PRO")

# TAB 3: PHÁI SINH PRO (5 Phút) - Giữ nguyên 14 ngày
with tab3:
    st.subheader("Hệ thống Bot VN30F1M - Khung 5 Phút (Bản PRO)")
    df_5m_pro = get_ps_pro_data('5', 14, lenFast, lenSlow, lenRsi, lenAtr, tp1_mult, tp2_mult, tp3_mult, sl_mult)
    render_ps_bot(df_5m_pro, "5 Phút PRO")
