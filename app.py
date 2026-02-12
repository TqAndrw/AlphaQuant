# app.py

import streamlit as st
import pandas as pd
from datetime import date, timedelta
from streamlit_option_menu import option_menu

# Import core modules
from src.data_loader import fetch_stock_data
from src.views import dashboard, risk, ai_forecast, portfolio

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="AlphaQuant Terminal", layout="wide", page_icon="⚡", initial_sidebar_state="expanded")

# --- 2. GLOBAL CSS ---
st.markdown("""
<style>
    .stApp { background-color: #0b0e11; color: #e0e0e0; }
    section[data-testid="stSidebar"] { background-color: #181a20; border-right: 1px solid #2b3139; }
    div[data-testid="stExpander"] { background-color: #1e2329; border: 1px solid #2b3139; border-radius: 8px; }
    
    /* Tùy chỉnh Multiselect để giống "Tags" hiển thị */
    .stMultiSelect span[data-baseweb="tag"] {
        background-color: #2b3139 !important;
        border: 1px solid #474d57;
    }
    
    /* Ẩn label của ô Quick Add cho gọn */
    div[data-testid="stTextInput"] label { display: none; }
    
    /* Card CSS */
    .metric-card { background-color: #1e2329; border: 1px solid #2b3139; border-radius: 8px; padding: 15px; margin-bottom: 10px; height: 180px; display: flex; flex-direction: column; justify-content: space-between; overflow: hidden; }
    .metric-label { font-size: 12px; color: #848e9c; text-transform: uppercase; font-weight: 600; margin-bottom: 2px; }
    .metric-value { font-size: 24px; font-weight: 700; color: #ffffff; line-height: 1.2; }
    .metric-bottom-container { display: flex; flex-direction: column; justify-content: flex-end; }
    .metric-delta { font-size: 13px; font-weight: 500; display: flex; align-items: center; gap: 5px; margin-bottom: 5px; }
    .sparkline-container { width: 100%; height: 40px; margin-bottom: 2px; }
    .metric-sub { font-size: 11px; color: #5E6673; margin-top: 0px; }
    .positive { color: #0ECB81; }
    .negative { color: #F6465D; }
    
    div[data-testid="stMetricValue"] { color: #F0B90B; }
    .sidebar-brand { font-size: 24px; font-weight: bold; color: #ffffff; display: flex; align-items: center; margin-bottom: 10px; }
    .sidebar-brand-icon { color: #F0B90B; margin-right: 10px; }
</style>
""", unsafe_allow_html=True)

# --- 3. STATE MANAGEMENT ---
if 'tickers' not in st.session_state: 
    st.session_state.tickers = ["BTC-USD", "ETH-USD", "AAPL"]
if 'df' not in st.session_state: st.session_state.df = None

# Hàm callback: Thêm mã khi ấn Enter
def add_ticker_callback():
    new_val = st.session_state.new_ticker_input.strip().upper()
    if new_val:
        if new_val not in st.session_state.tickers:
            st.session_state.tickers.append(new_val)
        st.session_state.new_ticker_input = "" # Reset ô nhập liệu

# --- 4. SIDEBAR NAVIGATION ---
with st.sidebar:
    st.markdown("""<div class="sidebar-brand"><span class="sidebar-brand-icon">⚡</span> AlphaQuant</div>""", unsafe_allow_html=True)
    st.caption("Professional Analytics v2.3")
    st.write("") 
    nav_selection = option_menu(
        menu_title=None,
        options=["Market Overview", "Risk Analysis (CFA)", "AI Forecast", "Portfolio Builder"],
        icons=["graph-up-arrow", "shield-check", "cpu", "briefcase"], 
        default_index=0,
        styles={
            "container": {"padding": "0!important", "background-color": "transparent"},
            "icon": {"color": "#848e9c", "font-size": "18px"}, 
            "nav-link": {"color": "#e0e0e0", "font-size": "16px", "margin": "5px 0px", "border-radius": "8px"},
            "nav-link-selected": {"background-color": "#ffffff", "color": "#181a20", "icon-color": "#181a20"},
        }
    )

# --- 5. TOP FILTER BAR (SEARCH & ADD MODE) ---
with st.container(border=True):
    c1, c2, c3, c4 = st.columns([2, 0.8, 1, 0.8])
    
    with c1:
        # 1. Ô nhập liệu (Search Box)
        st.text_input(
            "Add Ticker", 
            key="new_ticker_input",
            placeholder="🔍 Type ticker & Enter to add (e.g. VNM, TSLA, GLD)",
            on_change=add_ticker_callback # Gọi hàm khi Enter
        )
        
        # 2. Hiển thị Tags (Cho phép xóa)
        # Multiselect này lấy data từ session_state và cập nhật ngược lại nếu user xóa tag
        current_selection = st.multiselect(
            "Watchlist",
            options=st.session_state.tickers,
            default=st.session_state.tickers,
            label_visibility="collapsed"
        )
        
        # Logic đồng bộ: Nếu user xóa trên UI -> Cập nhật session_state
        if len(current_selection) != len(st.session_state.tickers):
            st.session_state.tickers = current_selection
            st.rerun()

    with c2:
        interval_map = {"1 Minute": "1m", "5 Minutes": "5m", "30 Minutes": "30m", "1 Hour": "1h", "1 Day": "1d", "1 Week": "1wk"}
        interval_label = st.selectbox("Interval", options=list(interval_map.keys()), index=4, label_visibility="collapsed")
        selected_interval = interval_map[interval_label]
        
    with c3:
        today = date.today()
        default_start = today - timedelta(days=365)
        if selected_interval in ['1m', '5m', '30m', '1h']: default_start = today - timedelta(days=59)
        date_range = st.date_input("Range", value=(default_start, today), max_value=today, format="DD/MM/YYYY", label_visibility="collapsed")
        
    with c4:
        st.write("") # Spacer
        if st.button("🔄 UPDATE", type="primary", use_container_width=True):
            if not st.session_state.tickers: st.warning("Watchlist is empty.")
            elif len(date_range) != 2: st.warning("Select range.")
            else:
                s, e = date_range
                with st.spinner(f"Fetching data for {len(st.session_state.tickers)} assets..."):
                    df_res = fetch_stock_data(st.session_state.tickers, str(s), str(e), selected_interval)
                    if df_res is not None and not df_res.empty:
                        st.session_state.df = df_res
                        st.success("Loaded!")
                    else: st.error("No Data.")

# --- 6. MAIN ROUTING (CLEAN VERSION) ---

# 1. Kiểm tra Data đã load chưa
if st.session_state.df is None:
    st.info("👋 Welcome to AlphaQuant! Type a ticker above (e.g., BTC-USD) and press Enter to start.")
    st.stop()

# 2. Kiểm tra Watchlist có rỗng không (FIX LỖI INDEX ERROR)
if not st.session_state.tickers:
    st.warning("⚠️ Your watchlist is empty. Please add a ticker in the 'Add Ticker' box above.")
    st.stop()

# 3. Điều hướng vào các View
if nav_selection == "Market Overview":
    dashboard.render_dashboard(st.session_state.df, st.session_state.tickers)

elif nav_selection == "Risk Analysis (CFA)":
    risk.render_risk_analysis(st.session_state.df, st.session_state.tickers)

elif nav_selection == "AI Forecast":
    ai_forecast.render_ai_forecast(st.session_state.df, st.session_state.tickers)

elif nav_selection == "Portfolio Builder":
    portfolio.render_portfolio_builder(st.session_state.df, st.session_state.tickers)