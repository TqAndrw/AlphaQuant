# main.py

import sys
import pandas as pd
from src.data_loader import fetch_stock_data
from src.quant_engine import calculate_log_returns, calculate_descriptive_stats
from src.visualizer import plot_return_distribution

def main():
    print("=== ALPHAQUANT ANALYTICS SUITE V1.1 ===")
    print("Note: Nhập 'EXIT' để thoát chương trình bất cứ lúc nào.\n")
    
    # --- VÒNG LẶP NHẬP LIỆU (UX IMPROVEMENT) ---
    while True:
        # 1. Nhập Input
        ticker = input("👉 Nhập mã cổ phiếu (VD: AAPL, VNM.HM, BTC-USD): ").strip().upper()
        
        # Cho phép người dùng thoát
        if ticker == 'EXIT':
            print("Đã thoát chương trình. Hẹn gặp lại!")
            sys.exit()
            
        if not ticker:
            print("⚠️ Mã cổ phiếu không được để trống. Vui lòng nhập lại.")
            continue # Quay lại đầu vòng lặp
            
        start_date = input("   Ngày bắt đầu (YYYY-MM-DD) [Enter = 2023-01-01]: ").strip()
        if not start_date:
            start_date = "2023-01-01"
            
        # 2. Data Ingestion (Thử tải dữ liệu)
        print(f"\n[1/3] Đang kiểm tra mã {ticker}...")
        df = fetch_stock_data(ticker, start_date=start_date)
        
        # KEY LOGIC: Kiểm tra xem dữ liệu có tải về thành công không
        if df is None or df.empty:
            print(f"❌ LỖI: Không tìm thấy mã '{ticker}' hoặc không có dữ liệu.")
            print("🔄 Vui lòng kiểm tra lại mã (VD: Thử thêm .HM nếu là cổ phiếu Việt Nam)")
            print("-" * 30)
            continue # Quay lại đầu vòng lặp để nhập lại
        else:
            # Nếu có dữ liệu, thoát khỏi vòng lặp nhập liệu và đi tiếp
            break
    # ---------------------------------------------

    try:
        # 3. Quant Calculation (Tính toán)
        print("\n[2/3] Đang tính toán các chỉ số CFA...")
        
        # Xử lý cột giá
        if 'Adj Close' in df.columns:
            target_col = 'Adj Close'
        else:
            target_col = 'Close'
            
        returns = calculate_log_returns(df, col_name=target_col)
        
        # Kiểm tra xem có đủ dữ liệu để tính toán không
        if len(returns) < 2:
            print("❌ Dữ liệu quá ít để tính toán lợi nhuận. Vui lòng chọn khoảng thời gian dài hơn.")
            return

        stats_table = calculate_descriptive_stats(returns)
        
        # 4. Reporting (Báo cáo)
        print("\n" + "="*40)
        print(f"BÁO CÁO PHÂN TÍCH RỦI RO: {ticker}")
        print("="*40)
        print(stats_table)
        print("="*40)
        
        # Nhận xét tự động
        vol_str = stats_table.loc["Annualized Volatility", "Value"]
        vol = float(vol_str.strip('%'))
        
        if vol > 30:
            print(f"⚠️ CẢNH BÁO: Biến động CAO ({vol}%/năm). Rủi ro lớn.")
        elif vol < 15:
            print(f"✅ AN TOÀN: Biến động THẤP ({vol}%/năm). Khá ổn định.")
        else:
            print(f"ℹ️ TRUNG BÌNH: Biến động ({vol}%/năm).")
            
        # 5. Visualization
        print("\n[3/3] Đang vẽ biểu đồ phân phối...")
        plot_return_distribution(returns, ticker)
        print("✅ Hoàn tất! Biểu đồ đã được hiển thị.")
        
    except Exception as e:
        print(f"❌ Lỗi không xác định trong quá trình xử lý: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()