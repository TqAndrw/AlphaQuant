# src/data_loader.py

import yfinance as yf
import pandas as pd

def fetch_stock_data(tickers, start_date, end_date, interval='1d'):
    """
    Tải dữ liệu cho 1 hoặc nhiều mã cổ phiếu.
    tickers: Có thể là string "AAPL" hoặc list ["AAPL", "MSFT"]
    """
    if isinstance(tickers, list):
        tickers_str = " ".join(tickers)
    else:
        tickers_str = tickers

    print(f"🔄 Fetching: {tickers_str}...")
    
    try:
        # Tải dữ liệu
        df = yf.download(
            tickers_str, 
            start=start_date, 
            end=end_date, 
            interval=interval, 
            group_by='ticker', # Gom nhóm theo mã để dễ xử lý
            auto_adjust=True,
            progress=False
        )
        
        if df.empty: return None
        
        return df
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return None