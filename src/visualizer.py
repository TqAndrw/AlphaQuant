# src/visualizer.py

import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import pandas as pd
from scipy.stats import norm

def plot_return_distribution(returns, ticker):
    """
    Vẽ biểu đồ phân phối lợi nhuận so với phân phối chuẩn.
    """
    # --- BƯỚC XỬ LÝ DỮ LIỆU ĐẦU VÀO (QUAN TRỌNG) ---
    
    # 1. Nếu là DataFrame (Bảng), chuyển thành Series (Danh sách)
    if isinstance(returns, pd.DataFrame):
        # Lấy cột đầu tiên của bảng
        returns = returns.iloc[:, 0]
        
    # 2. Ép kiểu về số (để tránh lỗi string/object)
    # errors='coerce' sẽ biến chữ thành NaN
    returns = pd.to_numeric(returns, errors='coerce')
    
    # 3. Loại bỏ dữ liệu lỗi (NaN) và Vô cực (inf)
    returns = returns.dropna()
    returns = returns[~returns.isin([np.inf, -np.inf])]
    # -----------------------------------------------

    # Kiểm tra xem còn dữ liệu để vẽ không
    if len(returns) == 0:
        print(f"❌ Không đủ dữ liệu sạch để vẽ biểu đồ cho {ticker}")
        return

    plt.figure(figsize=(10, 6))
    
    # 1. Vẽ Histogram dữ liệu thực tế (Màu xanh dương)
    # stat='density' để so sánh được với đường chuẩn
    sns.histplot(returns, kde=True, stat="density", 
                 color="blue", label=f"Actual Returns ({ticker})", alpha=0.5)
    
    # 2. Vẽ đường Phân phối chuẩn lý thuyết (Màu đỏ)
    mu, std = returns.mean(), returns.std()
    
    # Tạo trục X từ min đến max của dữ liệu
    x = np.linspace(returns.min(), returns.max(), 100)
    p = norm.pdf(x, mu, std)
    
    plt.plot(x, p, 'r--', linewidth=2, label="Normal Distribution (Theoretical)")
    
    # Trang trí
    plt.title(f"Distribution of Log Returns: {ticker}", fontsize=14)
    plt.xlabel("Daily Log Returns")
    plt.ylabel("Density")
    plt.legend()
    plt.grid(True, alpha=0.3)
    
    # Hiển thị biểu đồ
    plt.show()

# Test nhanh khi chạy trực tiếp file này
if __name__ == "__main__":
    # Giả lập dữ liệu DataFrame để test lỗi cũ
    df_test = pd.DataFrame({'Ret': np.random.normal(0, 0.02, 1000)})
    print("Testing with DataFrame input...")
    plot_return_distribution(df_test, "TEST_DF")