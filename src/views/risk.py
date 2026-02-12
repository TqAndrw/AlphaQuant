# src/views/risk.py

import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import numpy as np
import scipy.stats as stats
from src.quant_engine import calculate_advanced_metrics, calculate_log_returns
from src.utils import render_metric_card

def get_single_ticker_df(df, ticker):
    """Trích xuất DataFrame chuẩn cho 1 ticker."""
    try:
        if isinstance(df.columns, pd.MultiIndex):
            try:
                data = df.xs(ticker, level=0, axis=1)
            except KeyError:
                data = df.xs(ticker, level=1, axis=1)
        else:
            data = df
            
        # --- FIX QUAN TRỌNG: LOẠI BỎ CÁC DÒNG RỖNG (NaN) ---
        # Điều này xử lý việc Cổ phiếu nghỉ cuối tuần khi so với Crypto
        return data.dropna()
        
    except:
        return None

def render_risk_analysis(df, tickers):
    st.markdown(f"### 🛡️ Risk Analysis (CFA Mode)")
    st.caption("Deep-dive portfolio risk metrics: Sharpe, Sortino, Drawdown & Value-at-Risk.")
    
    if df is None:
        st.error("No data available.")
        return

    # --- 1. GLOBAL SETTINGS ---
    with st.expander("⚙️ Risk Parameters (Global)", expanded=True):
        rf_input = st.slider("Risk-Free Rate (Annual %)", 0.0, 10.0, 4.0, step=0.1)
        rf_rate = rf_input / 100

    # --- 2. TABS RENDERING ---
    if not tickers:
        st.warning("Please select tickers in the sidebar.")
        return

    tabs = st.tabs(tickers)

    for i, ticker in enumerate(tickers):
        with tabs[i]:
            st.subheader(f"Risk Profile: {ticker}")
            
            # 1. Trích xuất dữ liệu riêng (Đã bao gồm dropna)
            single_df = get_single_ticker_df(df, ticker)
            
            if single_df is None or len(single_df) < 30:
                st.warning(f"Not enough data for {ticker}. Need at least 30 data points (excluding weekends).")
                continue

            # 2. Tính toán Metrics
            metrics = calculate_advanced_metrics(single_df, risk_free_rate=rf_rate)
            
            # Lấy Log returns
            col_name = 'Adj Close' if 'Adj Close' in single_df.columns else 'Close'
            log_returns = calculate_log_returns(single_df, col_name)
            
            # --- FIX BỔ SUNG: Đảm bảo log_returns không còn NaN (double check) ---
            log_returns = log_returns.dropna()

            # 3. Hiển thị UI (Card có khung)
            c1, c2, c3, c4 = st.columns(4)
            
            with c1:
                sharpe = metrics["Sharpe Ratio"]
                if sharpe >= 2.0: desc, color = "Excellent", True
                elif sharpe >= 1.0: desc, color = "Good", True
                else: desc, color = "Suboptimal", False
                
                render_metric_card("Sharpe Ratio", f"{sharpe:.2f}", desc, "Rating", "Risk-Adjusted Return", is_positive=color)
                
            with c2:
                sortino = metrics["Sortino Ratio"]
                render_metric_card("Sortino Ratio", f"{sortino:.2f}", f"{sortino - sharpe:.2f}", "vs Sharpe", "Downside Focus", is_positive=sortino >= 1.0)
                
            with c3:
                mdd = metrics["Max Drawdown"]
                is_safe = mdd > -0.20
                render_metric_card("Max Drawdown", f"{mdd:.2%}", "All-Time Low", "Depth", "Worst Case Loss", is_positive=is_safe)
                
            with c4:
                vol = metrics["Annualized Volatility"]
                is_stable = vol < 0.30
                render_metric_card("Annual Volatility", f"{vol:.2%}", "High" if not is_stable else "Low", "Risk Level", "Standard Deviation", is_positive=is_stable)

            st.write("") # Spacer

            # 4. Charts Section
            col_chart1, col_chart2 = st.columns(2)

            with col_chart1:
                dd_series = metrics["Drawdown Series"]
                fig_dd = go.Figure()
                fig_dd.add_trace(go.Scatter(x=dd_series.index, y=dd_series, mode='lines', fill='tozeroy', name='Drawdown', line=dict(color='#F6465D', width=1), fillcolor='rgba(246, 70, 93, 0.2)'))
                fig_dd.update_layout(
                    template='plotly_dark',
                    height=350,
                    margin=dict(l=10, r=10, t=40, b=10),
                    title=f"🌊 {ticker} Underwater Plot (Drawdown)",
                    paper_bgcolor='rgba(0,0,0,0)', 
                    plot_bgcolor='rgba(0,0,0,0)',
                    yaxis_tickformat='.0%'
                )
                st.plotly_chart(fig_dd, use_container_width=True)

            with col_chart2:
                fig_dist = go.Figure()
                fig_dist.add_trace(go.Histogram(x=log_returns, histnorm='probability density', name='Actual Returns', marker_color='#3B82F6', opacity=0.6, nbinsx=50))
                
                if len(log_returns) > 1:
                    x_range = np.linspace(min(log_returns), max(log_returns), 100)
                    mu, std = np.mean(log_returns), np.std(log_returns)
                    pdf = stats.norm.pdf(x_range, mu, std)
                    fig_dist.add_trace(go.Scatter(x=x_range, y=pdf, mode='lines', name='Normal Distribution', line=dict(color='#F6465D', dash='dash', width=2)))
                
                fig_dist.update_layout(
                    template='plotly_dark',
                    height=350,
                    margin=dict(l=10, r=10, t=40, b=10),
                    title=f"🔔 {ticker} Return Distribution (Fat Tails)",
                    paper_bgcolor='rgba(0,0,0,0)', 
                    plot_bgcolor='rgba(0,0,0,0)',
                    xaxis_title="Daily Return"
                )
                st.plotly_chart(fig_dist, use_container_width=True)
            
            # 5. Quant Insight Box (Fix lỗi nan)
            try:
                skew = stats.skew(log_returns)
                kurt = stats.kurtosis(log_returns)
                
                # Kiểm tra nếu vẫn là nan (phòng hờ)
                if np.isnan(skew) or np.isnan(kurt):
                    insight_msg = "Insufficient data points to calculate distribution moments."
                else:
                    insight_msg = f"**Skewness:** {skew:.2f} (Lệch {'Phải' if skew>0 else 'Trái'}) | **Kurtosis:** {kurt:.2f} (Độ nhọn)."
                    if kurt > 3.0:
                        insight_msg += " Cảnh báo: **Fat Tails** (Đuôi béo) - Rủi ro sự kiện thiên nga đen cao hơn phân phối chuẩn."
            except:
                insight_msg = "Calculation Error."
            
            st.info(f"💡 **CFA Insight for {ticker}:** {insight_msg}")