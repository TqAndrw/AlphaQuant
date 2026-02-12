# src/views/portfolio.py

import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from src.quant_engine import optimize_portfolio

def render_portfolio_builder(df, tickers):
    st.markdown(f"### 💼 Portfolio Optimization (Markowitz Model)")
    st.caption("Xây dựng danh mục đầu tư tối ưu dựa trên đường biên hiệu quả (Efficient Frontier).")

    # 1. Kiểm tra đầu vào
    if len(tickers) < 2:
        st.warning("⚠️ Portfolio Optimization requires **at least 2 tickers**. Please select more assets in the sidebar.")
        st.info("💡 Tip: Try combining uncorrelated assets like BTC-USD (Crypto) + AAPL (Stock) + GLD (Gold).")
        return

    if df is None:
        st.error("No data available.")
        return

    # 2. Nút chạy tối ưu
    col_ctrl1, col_ctrl2 = st.columns([1, 3])
    with col_ctrl1:
        with st.container(border=True):
            st.markdown("**Settings**")
            num_sim = st.select_slider("Simulations", options=[2000, 5000, 10000], value=5000)
            rf_rate = st.number_input("Risk-Free Rate (%)", 0.0, 10.0, 3.0, step=0.5) / 100
            run_opt = st.button("🚀 Optimize Portfolio", type="primary", use_container_width=True)

    if run_opt:
        with st.spinner("Finding the best allocation matrix..."):
            # Gọi engine tối ưu
            opt_results = optimize_portfolio(df, num_portfolios=num_sim, risk_free_rate=rf_rate)
            
            if opt_results is None:
                st.error("Optimization failed. Please check data quality.")
                return

            # --- 3. HIỂN THỊ KẾT QUẢ ---
            
            # A. Efficient Frontier Chart (Biểu đồ quan trọng nhất)
            results = opt_results["results"]
            max_sharpe = opt_results["max_sharpe"]
            min_vol = opt_results["min_vol"]
            
            col_chart, col_alloc = st.columns([2, 1])
            
            with col_chart:
                fig = go.Figure()
                
                # 1. Vẽ 5000 điểm mô phỏng
                fig.add_trace(go.Scatter(
                    x=results[1,:], # Volatility (X)
                    y=results[0,:], # Return (Y)
                    mode='markers',
                    marker=dict(
                        color=results[2,:], # Màu theo Sharpe Ratio
                        colorscale='Viridis',
                        showscale=True,
                        size=4,
                        opacity=0.6,
                        colorbar=dict(title="Sharpe Ratio")
                    ),
                    name='Portfolios'
                ))
                
                # 2. Điểm Max Sharpe (Ngôi sao vàng)
                fig.add_trace(go.Scatter(
                    x=[max_sharpe['std']], y=[max_sharpe['return']],
                    mode='markers',
                    marker=dict(color='#F0B90B', size=15, symbol='star'),
                    name='Max Sharpe (Optimal)'
                ))
                
                # 3. Điểm Min Volatility (Ngôi sao xanh)
                fig.add_trace(go.Scatter(
                    x=[min_vol['std']], y=[min_vol['return']],
                    mode='markers',
                    marker=dict(color='#3B82F6', size=15, symbol='star'),
                    name='Min Volatility (Safest)'
                ))
                
                fig.update_layout(
                    template='plotly_dark',
                    title="Efficient Frontier",
                    xaxis_title="Annualized Volatility (Risk)",
                    yaxis_title="Annualized Return",
                    height=500,
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01)
                )
                st.plotly_chart(fig, use_container_width=True)
                
            # B. Allocation Pie Charts (Phân bổ vốn)
            with col_alloc:
                st.subheader("🎯 Optimal Allocation")
                
                # Tab chọn xem Max Sharpe hay Min Vol
                alloc_tab1, alloc_tab2 = st.tabs(["Max Sharpe", "Min Risk"])
                
                with alloc_tab1:
                    # Pie Chart cho Max Sharpe
                    labels = list(max_sharpe['weights'].keys())
                    values = list(max_sharpe['weights'].values())
                    
                    fig_pie1 = go.Figure(data=[go.Pie(labels=labels, values=values, hole=.4)])
                    fig_pie1.update_layout(
                        template='plotly_dark', 
                        height=350, 
                        margin=dict(l=0, r=0, t=30, b=0),
                        paper_bgcolor='rgba(0,0,0,0)'
                    )
                    st.plotly_chart(fig_pie1, use_container_width=True)
                    
                    st.metric("Exp. Return", f"{max_sharpe['return']:.2%}")
                    st.metric("Sharpe Ratio", f"{max_sharpe['sharpe']:.2f}")

                with alloc_tab2:
                    # Pie Chart cho Min Vol
                    labels2 = list(min_vol['weights'].keys())
                    values2 = list(min_vol['weights'].values())
                    
                    fig_pie2 = go.Figure(data=[go.Pie(labels=labels2, values=values2, hole=.4)])
                    fig_pie2.update_layout(
                        template='plotly_dark', 
                        height=350, 
                        margin=dict(l=0, r=0, t=30, b=0),
                        paper_bgcolor='rgba(0,0,0,0)'
                    )
                    st.plotly_chart(fig_pie2, use_container_width=True)
                    
                    st.metric("Exp. Return", f"{min_vol['return']:.2%}")
                    st.metric("Volatility", f"{min_vol['std']:.2%}")
                    
                    st.markdown("---")
                    st.subheader("🧐 Why this allocation?")
            
            # Tính chỉ số riêng lẻ cho từng mã để user hiểu
            # Lấy data giá
            try:
                if isinstance(df.columns, pd.MultiIndex):
                    price_levels = df.columns.get_level_values(1).unique()
                    target_col = 'Adj Close' if 'Adj Close' in price_levels else 'Close'
                    data = df.xs(target_col, level=1, axis=1)
                else:
                    data = df
            except:
                data = df

            if data is not None:
                returns = np.log(data / data.shift(1)).dropna()
                mean_ret = returns.mean() * 252
                vol = returns.std() * np.sqrt(252)
                sharpes = (mean_ret - rf_rate) / vol
                
                metrics_df = pd.DataFrame({
                    "Annual Return": mean_ret,
                    "Volatility": vol,
                    "Sharpe Ratio": sharpes
                })
                
                # Format hiển thị
                st.dataframe(
                    metrics_df.style.format("{:.2%}", subset=["Annual Return", "Volatility"]).format("{:.2f}", subset=["Sharpe Ratio"])
                    .background_gradient(cmap="RdYlGn", subset=["Sharpe Ratio"]),
                    use_container_width=True
                )
                st.caption("💡 **Insight:** Thuật toán sẽ dồn tỷ trọng vào các mã có **Sharpe Ratio** cao (Màu xanh) và hạn chế các mã có Sharpe thấp hoặc âm (Màu đỏ).")

    else:
        st.info("👈 Select parameters and click 'Optimize Portfolio'.")
        st.markdown("""
        **What is Efficient Frontier?** 
        It is a set of optimal portfolios that offer the highest expected return for a defined level of risk.
        * **Max Sharpe Portfolio:** The "sweet spot" that gives the best return per unit of risk.
        * **Min Volatility Portfolio:** The safest possible combination of your selected assets.
        """)