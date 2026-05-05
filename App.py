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
        if len(df) < max(f_ema, s_ema, rsi_l, atr_l):
            return None

        # Tự tính EMA Nhanh và Chậm
        df['EMA_Fast'] = df['close'].ewm(span=f_ema, adjust=False).mean()
        df['EMA_Slow'] = df['close'].ewm(span=s_ema, adjust=False).mean()

        # Tự tính RSI
        delta = df['close'].diff()
        gain = delta.where(delta > 0, 0.0).ewm(alpha=1/rsi_l, adjust=False).mean()
        loss = (-delta.where(delta < 0, 0.0)).ewm(alpha=1/rsi_l, adjust=False).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))

        # Tự tính ATR
        tr1 = df['high'] - df['low']
        tr2 = (df['high'] - df['close'].shift(1)).abs()
        tr3 = (df['low'] - df['close'].shift(1)).abs()
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        df['ATR'] = tr.ewm(alpha=1/atr_l, adjust=False).mean()

        df['EMA_Fast_Prev'] = df['EMA_Fast'].shift(1)
        df['EMA_Slow_Prev'] = df['EMA_Slow'].shift(1)

        df['Long_Signal'] = (df['EMA_Fast'] > df['EMA_Slow']) & (df['EMA_Fast_Prev'] <= df['EMA_Slow_Prev']) & (df['RSI'] > 50)
        df['Short_Signal'] = (df['EMA_Fast'] < df['EMA_Slow']) & (df['EMA_Fast_Prev'] >= df['EMA_Slow_Prev']) & (df['RSI'] < 50)
        
        df['Tín Hiệu'] = '-'
        df['TP1'] = '-'
        df['TP2'] = '-'
        df['TP3'] = '-'
        df['SL'] = '-'

        # Thêm đuôi .astype(str) để ép kiểu thành chữ, tránh xung đột dữ liệu
        long_idx = df[df['Long_Signal'] == True].index
        if len(long_idx) > 0:
            df.loc[long_idx, 'Tín Hiệu'] = '🟢 LONG'
            df.loc[long_idx, 'TP1'] = round(df.loc[long_idx, 'close'] + (df.loc[long_idx, 'ATR'] * tp1_m), 1).astype(str)
            df.loc[long_idx, 'TP2'] = round(df.loc[long_idx, 'close'] + (df.loc[long_idx, 'ATR'] * tp2_m), 1).astype(str)
            df.loc[long_idx, 'TP3'] = round(df.loc[long_idx, 'close'] + (df.loc[long_idx, 'ATR'] * tp3_m), 1).astype(str)
            df.loc[long_idx, 'SL'] = round(df.loc[long_idx, 'close'] - (df.loc[long_idx, 'ATR'] * sl_m), 1).astype(str)

        short_idx = df[df['Short_Signal'] == True].index
        if len(short_idx) > 0:
            df.loc[short_idx, 'Tín Hiệu'] = '🔴 SHORT'
            df.loc[short_idx, 'TP1'] = round(df.loc[short_idx, 'close'] - (df.loc[short_idx, 'ATR'] * tp1_m), 1).astype(str)
            df.loc[short_idx, 'TP2'] = round(df.loc[short_idx, 'close'] - (df.loc[short_idx, 'ATR'] * tp2_m), 1).astype(str)
            df.loc[short_idx, 'TP3'] = round(df.loc[short_idx, 'close'] - (df.loc[short_idx, 'ATR'] * tp3_m), 1).astype(str)
            df.loc[short_idx, 'SL'] = round(df.loc[short_idx, 'close'] + (df.loc[short_idx, 'ATR'] * sl_m), 1).astype(str)

        df['RSI'] = df['RSI'].round(2)
        return df
    except Exception as e:
        return f"LỖI API: {str(e)}"
# --- HÀM HIỂN THỊ THỐNG KÊ DÒNG TIỀN PHÁI SINH ---
def render_market_flow():
    st.subheader("📊 Thống kê Dòng tiền Phái Sinh")
    
    # Dữ liệu mẫu (Mock Data) - Bạn có thể thay bằng API thật nếu có
    data = {
        "date": "4/5/2026",
        "foreign": {"net": -1644, "net_type": "Short", "daily_pnl": 6.9, "hold_vol": 4049, "hold_type": "Long", "avg_price": 1970.0, "month_pnl": 63.7},
        "prop": {"net": 405, "net_type": "Long", "daily_pnl": -2.1, "hold_vol": -1948, "hold_type": "Short", "avg_price": 1962.1, "month_pnl": -9.6},
        "retail": {"net": 1237, "net_type": "Long", "daily_pnl": -4.8, "hold_vol": -2097, "hold_type": "Short", "avg_price": 1962.6, "month_pnl": -54.2}
    }

    st.write(f"**Phái Sinh ngày {data['date']}**")
    
    # --- Khối Ngoại (Tây) ---
    f_icon = "🔴" if data['foreign']['net_type'] == "Short" else "🟢"
    st.markdown(f"""
    {f_icon} **Hnay Tây {data['foreign']['net_type']} ròng :** {data['foreign']['net']}HĐ ; lãi (lướt)/ngày : {data['foreign']['daily_pnl']} tỷ.  
    **Hold:** {data['foreign']['hold_vol']} {data['foreign']['hold_type']}, giá vốn {data['foreign']['avg_price']}. Ước tính Lãi tháng này (Lướt+ Hold) **{data['foreign']['month_pnl']} tỷ**;
    """)
    st.markdown("---")

    # --- Tự Doanh (TD) ---
    p_icon = "🔴" if data['prop']['net_type'] == "Short" else "✅"
    st.markdown(f"""
    {p_icon} **Hnay TD {data['prop']['net_type']} :** {data['prop']['net']}HĐ ; lỗ/ngày : {data['prop']['daily_pnl']} tỷ.  
    **Hold:** {data['prop']['hold_vol']} {data['prop']['hold_type']}, giá vốn {data['prop']['avg_price']}. Ước tính Lỗ tháng này (Lướt+ Hold) **{data['prop']['month_pnl']} tỷ**;
    """)
    st.markdown("---")

    # --- Nhỏ lẻ (CN) ---
    r_icon = "🔴" if data['retail']['net_type'] == "Short" else "✅"
    st.markdown(f"""
    {r_icon} **Hnay CN Nhỏ lẻ # {data['retail']['net_type']} :** {data['retail']['net']}HĐ ; lỗ/ngày : {data['retail']['daily_pnl']} tỷ.  
    **Hold:** {data['retail']['hold_vol']} {data['retail']['hold_type']}, giá vốn {data['retail']['avg_price']}. Ước tính Lỗ tháng này (Lướt+ Hold) **{data['retail']['month_pnl']} tỷ**;
    """)
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
        st.warning("Không có dữ liệu trả về từ API. Có thể ngoài giờ giao dịch.")

# --- TẠO 3 TABS GIAO DIỆN CHÍNH ---
tab1, tab2, tab3 = st.tabs(["📈 CƠ SỞ", "👑 PS PRO (1 Phút)", "👑 PS PRO (5 Phút)"])

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
            st.subheader("Thông প্রান্ত")
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
import pandas as pd

def calculate_foreign_flow(current_price, historical_daily_data):
    """
    Thuật toán ước tính Giá vốn và Lãi/Lỗ của Khối ngoại.
    Hệ số nhân của 1 Hợp đồng VN30F1M là 100,000 VNĐ.
    """
    total_hold_vol = 0
    total_capital = 0  # Tổng giá trị vốn
    
    # 1. Tính toán Vị thế Hold và Giá vốn (Tính từ đầu kỳ hạn hợp đồng)
    for day in historical_daily_data:
        net_vol = day['buy_vol'] - day['sell_vol'] # Khối lượng ròng trong ngày
        vwap = day['vwap'] # Giá trung bình trong ngày
        
        total_hold_vol += net_vol
        total_capital += (net_vol * vwap)
        
    # Giá vốn trung bình = Tổng vốn / Tổng khối lượng
    avg_hold_price = total_capital / total_hold_vol if total_hold_vol != 0 else 0
    hold_type = "Long" if total_hold_vol > 0 else "Short"
    
    # 2. Tính toán Lãi/Lỗ ước tính trong tháng (Lướt + Hold)
    # Công thức PnL = (Giá hiện tại - Giá vốn) * Khối lượng Hold * Hệ số nhân 100k
    # Lưu ý: Nếu Hold Short (total_hold_vol < 0) thì công thức vẫn đúng vì số âm sẽ đảo chiều kết quả.
    estimated_pnl_vnd = (current_price - avg_hold_price) * total_hold_vol * 100000
    estimated_pnl_ty = estimated_pnl_vnd / 1000000000  # Đổi ra đơn vị Tỷ VNĐ
    
    # 3. Lấy dữ liệu ngày hôm nay (ngày cuối cùng trong mảng)
    today_data = historical_daily_data[-1]
    today_net_vol = today_data['buy_vol'] - today_data['sell_vol']
    today_net_type = "Long" if today_net_vol > 0 else "Short"
    
    # Ước tính lãi/lỗ lướt sóng trong ngày của họ
    today_pnl = (current_price - today_data['vwap']) * today_net_vol * 100000 / 1000000000

    # 4. Trả về kết quả
    return {
        "today_net_vol": today_net_vol,
        "today_net_type": today_net_type,
        "today_pnl_ty": round(today_pnl, 1),
        "hold_vol": total_hold_vol,
        "hold_type": hold_type,
        "avg_hold_price": round(avg_hold_price, 1),
        "month_pnl_ty": round(estimated_pnl_ty, 1)
    }

# ==========================================
# CÁCH SỬ DỤNG TRONG THỰC TẾ
# ==========================================

# Giả sử hôm nay giá VN30F1M đang đóng cửa ở mức 1250.0
current_ps_price = 1250.0

# Đây là dữ liệu bạn thu thập từ đầu tháng (sau ngày đáo hạn trước)
# Bạn có thể lấy tay từ bảng giá SSI/VNDirect lúc cuối ngày
foreign_data_history = [
    {"date": "02/05", "buy_vol": 5000, "sell_vol": 3000, "vwap": 1230.5}, # Mua ròng 2000
    {"date": "03/05", "buy_vol": 4000, "sell_vol": 2000, "vwap": 1240.0}, # Mua ròng 2000
    {"date": "04/05", "buy_vol": 1000, "sell_vol": 2644, "vwap": 1245.5}, # Hôm nay bán ròng -1644
]

# Chạy thuật toán
result = calculate_foreign_flow(current_ps_price, foreign_data_history)

print("--- THỐNG KÊ KHỐI NGOẠI ---")
print(f"Hnay Tây {result['today_net_type']} ròng: {result['today_net_vol']} HĐ ; lãi (lướt)/ngày: {result['today_pnl_ty']} tỷ.")
print(f"Hold: {result['hold_vol']} {result['hold_type']}, giá vốn {result['avg_hold_price']}.")
print(f"Ước tính Lãi/Lỗ tháng này: {result['month_pnl_ty']} tỷ.")
# --- TẠO 4 TABS GIAO DIỆN CHÍNH ---
tab1, tab2, tab3, tab4 = st.tabs(["📈 CƠ SỞ", "👑 PS PRO (1 Phút)", "👑 PS PRO (5 Phút)", "📊 DÒNG TIỀN"])

# (Giữ nguyên code của TAB 1, TAB 2, TAB 3)
# ... code cũ ...

# TAB 4: THỐNG KÊ DÒNG TIỀN
with tab4:
    render_market_flow()
    st.info("💡 Lưu ý: Đây là giao diện hiển thị dữ liệu dòng tiền mẫu. Để có số liệu thực tế, cần kết nối với API cung cấp dữ liệu định lượng chuyên sâu (FiinTrade, Wichart...) hoặc tự viết thuật toán cào dữ liệu (crawl) từ Sở Giao Dịch mỗi cuối ngày.")
