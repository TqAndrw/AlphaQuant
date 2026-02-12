# src/views/ai_forecast.py

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from scipy.stats import norm
# Import hàm render_metric_card để dùng cho các thẻ
from src.utils import render_metric_card

# --- 1. CORE LOGIC (Giữ nguyên) ---
def run_monte_carlo(prices, days_forecast, num_simulations):
    """Chạy mô phỏng Monte Carlo dựa trên Series giá đã được trích xuất."""
    returns = prices.pct_change().dropna()
    if len(returns) < 2: return None # Không đủ dữ liệu
    
    last_price = prices.iloc[-1]
    
    log_returns = np.log(1 + returns)
    u = log_returns.mean()
    var = log_returns.var()
    
    drift = u - (0.5 * var)
    std_dev = log_returns.std()
    
    # Tạo ma trận ngẫu nhiên
    daily_returns = np.exp(drift + std_dev * norm.ppf(np.random.rand(days_forecast, num_simulations)))
    
    price_paths = np.zeros_like(daily_returns)
    price_paths[0] = last_price
    
    for t in range(1, days_forecast):
        price_paths[t] = price_paths[t-1] * daily_returns[t]
        
    return price_paths

def get_single_ticker_data(df, ticker):
    """Trích xuất Series giá của 1 ticker từ DataFrame hỗn hợp."""
    try:
        if isinstance(df.columns, pd.MultiIndex):
            # Cố gắng lấy level 0 là ticker
            try:
                data = df.xs(ticker, level=0, axis=1)
            except KeyError:
                # Nếu không được thì thử level 1 (cấu trúc cũ)
                data = df.xs(ticker, level=1, axis=1)
        else:
            # Single Index (chỉ có 1 mã)
            data = df
            
        # Lấy cột giá Close/Adj Close
        col = 'Adj Close' if 'Adj Close' in data.columns else 'Close'
        return data[col]
    except Exception as e:
        return None

# --- 2. MAIN VIEW ---
def render_ai_forecast(df, tickers):
    st.markdown(f"### 🎲 Monte Carlo Simulation")
    st.caption("Stochastic modeling & Quantitative Risk Assessment for Portfolio Assets.")
    
    if df is None:
        st.error("No data available.")
        return

    # --- GLOBAL SETTINGS (Dùng chung cho tất cả các mã) ---
    with st.expander("⚙️ Simulation Settings (Apply to All)", expanded=True):
        c1, c2, c3 = st.columns([1, 1, 1])
        with c1:
            days_forecast = st.slider("Forecast Horizon (Days)", 7, 90, 30)
        with c2:
            num_sim = st.select_slider("Scenarios", options=[200, 500, 1000], value=500)
        with c3:
            st.write("") # Spacer
            st.write("")
            run_btn = st.button("🚀 Run All Simulations", type="primary", use_container_width=True)

    # --- TABS RENDERING ---
    # Tạo các tab tương ứng với các mã đã chọn
    if not tickers:
        st.warning("Please select tickers in the sidebar.")
        return

    # Tạo giao diện Tab
    tabs = st.tabs(tickers)

    if run_btn:
        # Nếu bấm nút chạy, duyệt qua từng mã và từng tab
        for i, ticker in enumerate(tickers):
            with tabs[i]:
                st.subheader(f"Analysis for {ticker}")
                
                # 1. Trích xuất dữ liệu riêng cho mã này
                prices = get_single_ticker_data(df, ticker)
                
                if prices is None or len(prices) < 30:
                    st.warning(f"Not enough data for {ticker}. Need at least 30 data points.")
                    continue

                with st.spinner(f"Simulating {ticker}..."):
                    # 2. Chạy mô phỏng
                    price_paths = run_monte_carlo(prices, days_forecast, num_sim)
                    
                    if price_paths is None:
                        st.error("Simulation failed due to data issues.")
                        continue

                    # 3. Tính toán kết quả
                    final_prices = price_paths[-1]
                    curr_price = prices.iloc[-1]
                    
                    mean_price = np.mean(final_prices)
                    bull_case = np.percentile(final_prices, 95)
                    bear_case = np.percentile(final_prices, 5)
                    prob_up = np.sum(final_prices > curr_price) / num_sim * 100
                    
                    # Metrics Quant
                    scenario_returns = (final_prices - curr_price) / curr_price
                    var_95 = np.percentile(scenario_returns, 5) 
                    
                    # Logic đề xuất
                    if abs(var_95) > 0.20:
                        risk_label = "EXTREME RISK"
                        color = "red"
                    elif abs(var_95) > 0.10:
                        risk_label = "HIGH RISK"
                        color = "orange"
                    else:
                        risk_label = "MODERATE"
                        color = "green"

                    # 4. Hiển thị UI cho từng Tab
                    # Metrics Row - SỬ DỤNG render_metric_card ĐỂ CÓ KHUNG
                    m1, m2, m3, m4 = st.columns(4)
                    with m1:
                        render_metric_card(
                            label="Current",
                            value=f"${curr_price:,.2f}",
                            delta="",
                            delta_desc="",
                            sub_text="",
                            is_positive=True
                        )
                    with m2:
                        mean_delta = (mean_price - curr_price) / curr_price * 100
                        render_metric_card(
                            label="Expected (Mean)",
                            value=f"${mean_price:,.2f}",
                            delta=f"{mean_delta:.1f}%",
                            delta_desc="Current",
                            sub_text="",
                            is_positive=mean_delta >= 0
                        )
                    with m3:
                        bull_delta = (bull_case - curr_price) / curr_price * 100
                        render_metric_card(
                            label="Bull Case (95%)",
                            value=f"${bull_case:,.2f}",
                            delta=f"{bull_delta:.1f}%",
                            delta_desc="Current",
                            sub_text="Best Case",
                            is_positive=True
                        )
                    with m4:
                        bear_delta = (bear_case - curr_price) / curr_price * 100
                        render_metric_card(
                            label="Bear Case (5%)",
                            value=f"${bear_case:,.2f}",
                            delta=f"{bear_delta:.1f}%",
                            delta_desc="Current",
                            sub_text="Worst Case",
                            is_positive=False
                        )
                    
                    # Chart
                    fig = go.Figure()
                    # Vẽ 50 đường mẫu
                    step = max(1, num_sim // 50)
                    for k in range(0, num_sim, step):
                        fig.add_trace(go.Scatter(y=price_paths[:, k], mode='lines', line=dict(width=1, color='rgba(132, 142, 156, 0.2)'), showlegend=False, hoverinfo='skip'))
                    
                    fig.add_trace(go.Scatter(y=np.mean(price_paths, axis=1), mode='lines', name='Mean Path', line=dict(width=3, color='#F0B90B')))
                    fig.add_trace(go.Scatter(x=[0], y=[curr_price], mode='markers', marker=dict(color='white', size=6), name='Start'))
                    
                    fig.update_layout(
                        template='plotly_dark', 
                        height=400, 
                        # FIX LỖI TIÊU ĐỀ BỊ CẮT: Tăng lề trên (t) từ 10 lên 40
                        margin=dict(l=10, r=10, t=40, b=10),
                        title=f"{ticker} Forecast ({days_forecast} Days)",
                        paper_bgcolor='rgba(0,0,0,0)',
                        plot_bgcolor='rgba(0,0,0,0)'
                    )
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # Insight Box
                    st.info(f"🤖 **Quant Insight for {ticker}:** Risk Level is **:{color}[{risk_label}]**. VaR (95%) is {var_95:.2%}. Probability of profit: **{prob_up:.1f}%**.")

    else:
        # Trạng thái chờ (khi chưa bấm nút Run)
        for i, ticker in enumerate(tickers):
            with tabs[i]:
                st.info(f"👈 Ready to simulate **{ticker}**. Click 'Run All Simulations' above.")