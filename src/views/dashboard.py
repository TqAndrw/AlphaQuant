# src/views/dashboard.py

import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from plotly.subplots import make_subplots
from src.utils import render_metric_card

def render_dashboard(df, tickers):
    """
    Hiển thị Dashboard. 
    - Nếu 1 ticker: Hiển thị chế độ chi tiết (Card + Nến).
    - Nếu > 1 ticker: Hiển thị chế độ so sánh (Comparison Chart).
    """
    if not tickers:
        st.warning("Please select a ticker.")
        return
    # === TRƯỜNG HỢP 1: CHỌN NHIỀU MÃ (COMPARISON MODE) ===
    if len(tickers) > 1:
        st.markdown(f"### ⚔️ Market Comparison: {', '.join(tickers)}")
        
        # 1. Chuẩn bị dữ liệu so sánh (Lấy cột Close)
        try:
            if isinstance(df.columns, pd.MultiIndex):
                # FIX LỖI 'Close': Dùng xs để lấy dữ liệu ở Level 1 (Price Type)
                # Kiểm tra xem cột giá tên là 'Adj Close' hay 'Close'
                price_levels = df.columns.get_level_values(1).unique()
                target_col = 'Adj Close' if 'Adj Close' in price_levels else 'Close'
                
                # Lấy tất cả cột có tên target_col ở Level 1
                comp_df = df.xs(target_col, level=1, axis=1)
            else:
                st.error("Data structure error: Expected MultiIndex for multiple tickers.")
                return
        except Exception as e:
            st.error(f"Error preparing comparison data: {e}")
            return

        # 2. Tính % Tăng trưởng tích lũy (Cumulative Return)
        # Công thức: (Giá / Giá đầu kỳ) - 1
        # dropna() để tránh lỗi nếu các mã có ngày bắt đầu khác nhau
        normalized_df = (comp_df / comp_df.iloc[0]) - 1
        
        # 3. Vẽ biểu đồ so sánh
        fig = go.Figure()
        
        for ticker in tickers:
            if ticker in normalized_df.columns:
                fig.add_trace(go.Scatter(
                    x=normalized_df.index,
                    y=normalized_df[ticker],
                    mode='lines',
                    name=ticker,
                    hovertemplate='%{y:.2%}'
                ))
            
        fig.update_layout(
            template='plotly_dark',
            title="Relative Performance (%)",
            xaxis_title="Date",
            yaxis_title="Cumulative Return",
            height=600,
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            yaxis_tickformat='.0%'
        )
        st.plotly_chart(fig, use_container_width=True)
        
        # 4. Bảng Correlation (Tương quan)
        with st.expander("📊 Correlation Matrix (Ma trận tương quan)"):
            corr = comp_df.corr()
            fig_corr = go.Figure(data=go.Heatmap(
                z=corr.values,
                x=corr.columns,
                y=corr.columns,
                colorscale='Viridis',
                texttemplate="%{z:.2f}"
            ))
            fig_corr.update_layout(height=500, template='plotly_dark', paper_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig_corr, use_container_width=True)
            st.caption("Gần 1: Cùng chiều | Gần -1: Ngược chiều | Gần 0: Không liên quan")

        return # Kết thúc hàm so sánh

    # === TRƯỜNG HỢP 2: CHỌN 1 MÃ (SINGLE MODE) ===
    # Lấy ticker duy nhất
    ticker = tickers[0]
    
    # Xử lý data frame đơn (Flatten MultiIndex nếu có)
    if isinstance(df.columns, pd.MultiIndex):
        # FIX LỖI KEYERROR: Kiểm tra xem Ticker nằm ở Level 0 hay Level 1
        try:
            # Thử lấy ở Level 0 trước (Chuẩn group_by='ticker')
            single_df = df.xs(ticker, level=0, axis=1)
        except KeyError:
            # Fallback (phòng hờ)
            try:
                single_df = df.xs(ticker, level=1, axis=1)
            except KeyError:
                st.error(f"Cannot find data for {ticker}")
                return
    else:
        single_df = df

    # --- CODE HIỂN THỊ CHI TIẾT ---
    st.markdown(f"### 📊 Market Overview: {ticker}")
    
    if single_df is None or single_df.empty:
        st.warning("No data available.")
        return

    close_col = 'Adj Close' if 'Adj Close' in single_df.columns else 'Close'

    # --- 1. METRIC CARDS ---
    if len(single_df) < 30:
        st.warning("Load at least 30 data points for full visualization.")
    
    lookback = 50 
    recent_df = single_df.tail(lookback)
    
    # Tính toán Metrics
    curr_price = single_df[close_col].iloc[-1]
    pct_price = (curr_price - single_df[close_col].iloc[-2]) / single_df[close_col].iloc[-2] * 100
    last_date = single_df.index[-1].strftime('%d/%m %H:%M') if hasattr(single_df.index, 'hour') else single_df.index[-1].strftime('%d/%m/%Y')
    
    curr_vol = single_df['Volume'].iloc[-1]
    avg_vol = single_df['Volume'].iloc[-20:].mean()
    pct_vol = ((curr_vol - avg_vol) / avg_vol) * 100
    
    high_52w = single_df['High'].max()
    dist_to_high = ((curr_price - high_52w) / high_52w) * 100
    
    daily_range = single_df['High'] - single_df['Low']
    curr_range_pct = (daily_range.iloc[-1] / single_df['Low'].iloc[-1]) * 100
    avg_range_pct = (daily_range.tail(20).mean() / single_df['Low'].tail(20).mean()) * 100
    delta_volatility = curr_range_pct - avg_range_pct

    # Render Cards
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        render_metric_card("Current Price", f"${curr_price:,.2f}", f"{pct_price:.2f}%", "Yesterday", f"Close: {last_date}", pct_price >= 0, recent_df[close_col])
    with col2:
        render_metric_card("Volume (Session)", f"{curr_vol:,.0f}", f"{pct_vol:.1f}%", "20-Day Avg", f"Avg: {avg_vol:,.0f}", pct_vol >= 0, recent_df['Volume'])
    with col3:
        render_metric_card("Dist to Peak", f"${high_52w:,.2f}", f"{dist_to_high:.2f}%", "Period High", "Highest Price in Range", dist_to_high >= -5, recent_df['High'])
    with col4:
        render_metric_card("Daily Volatility", f"{curr_range_pct:.2f}%", f"{delta_volatility:.2f}%", "20-Day Avg", f"Range: ${(single_df['High'].iloc[-1] - single_df['Low'].iloc[-1]):,.2f}", delta_volatility <= 0, daily_range.tail(lookback))

    # --- 2. MAIN CHART ---
    with st.expander("⚙️ Chart Settings", expanded=False):
        c1, c2 = st.columns(2)
        with c1: show_ma = st.multiselect("Indicators", ["MA20", "MA50"], default=["MA20"])
        with c2: chart_type = st.radio("Type", ["Candlestick", "Line"], horizontal=True)

    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_width=[0.2, 0.7], vertical_spacing=0.05)
    
    if chart_type == "Candlestick":
        fig.add_trace(go.Candlestick(x=single_df.index, open=single_df['Open'], high=single_df['High'], low=single_df['Low'], close=single_df[close_col], name='OHLC'), row=1, col=1)
    else:
        fig.add_trace(go.Scatter(x=single_df.index, y=single_df[close_col], line=dict(color='#0ECB81', width=2), name='Close'), row=1, col=1)
    
    if "MA20" in show_ma: 
        single_df['MA20'] = single_df[close_col].rolling(20).mean()
        fig.add_trace(go.Scatter(x=single_df.index, y=single_df['MA20'], line=dict(color='#F0B90B', width=1), name='MA 20'), row=1, col=1)
    if "MA50" in show_ma: 
        single_df['MA50'] = single_df[close_col].rolling(50).mean()
        fig.add_trace(go.Scatter(x=single_df.index, y=single_df['MA50'], line=dict(color='#9945FF', width=1), name='MA 50'), row=1, col=1)

    colors = ['#0ECB81' if o < c else '#F6465D' for o, c in zip(single_df['Open'], single_df[close_col])]
    fig.add_trace(go.Bar(x=single_df.index, y=single_df['Volume'], marker_color=colors, name='Volume'), row=2, col=1)
    
    fig.update_layout(template='plotly_dark', height=600, xaxis_rangeslider_visible=False, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
    st.plotly_chart(fig, use_container_width=True)