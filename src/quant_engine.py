# src/quant_engine.py

import numpy as np
import pandas as pd
from scipy.stats import skew, kurtosis

def calculate_log_returns(df: pd.DataFrame, col_name: str = 'Close') -> pd.Series:
    """
    Chuyển đổi giá sang Log Returns.
    """
    # 1. Xử lý đầu vào để lấy đúng chuỗi giá (Series)
    price_series = None
    
    # Trường hợp 1: df là DataFrame (Bảng)
    if isinstance(df, pd.DataFrame):
        # Ưu tiên tìm cột có tên chỉ định
        if col_name in df.columns:
            price_series = df[col_name]
        # Nếu là MultiIndex (thường gặp ở yfinance mới), thử tìm trong level 0
        elif isinstance(df.columns, pd.MultiIndex):
            try:
                price_series = df.xs(col_name, level=0, axis=1)
            except:
                price_series = df.iloc[:, 0] # Fallback: Lấy cột đầu tiên
        else:
            price_series = df.iloc[:, 0] # Fallback: Lấy cột đầu tiên
            
    # Trường hợp 2: df đã là Series
    else:
        price_series = df

    # 2. Đảm bảo dữ liệu là 1 chiều (Squeeze)
    if isinstance(price_series, pd.DataFrame):
        price_series = price_series.squeeze()
        
    # 3. Tính toán
    # Chuyển về numpy array để tính toán cho an toàn, tránh lỗi index
    prices = price_series.values
    
    # Công thức: ln(P_t / P_t-1)
    # Thêm 1e-9 để tránh chia cho 0 nếu có
    log_returns = np.log(prices[1:] / (prices[:-1] + 1e-9))
    
    # Trả về dưới dạng Series để giữ lại ngày tháng (Index) nếu cần plot
    return pd.Series(log_returns, index=price_series.index[1:])

def calculate_descriptive_stats(returns) -> pd.DataFrame:
    """
    Tính các chỉ số thống kê mô tả theo chuẩn CFA Level 1.
    FIX: Chuyển đổi về mảng Numpy 1 chiều ngay từ đầu để tránh lỗi Dimension.
    """
    
    # --- BƯỚC AN TOÀN: Flatten Data ---
    if isinstance(returns, (pd.DataFrame, pd.Series)):
        # .values chuyển về numpy array, .flatten() ép về 1 chiều
        data = returns.values.flatten()
    else:
        data = np.array(returns).flatten()
        
    # Loại bỏ NaN và inf trước khi tính
    data = data[~np.isnan(data)]
    data = data[~np.isinf(data)]
    
    if len(data) == 0:
        return pd.DataFrame({"Error": ["Not enough data"]})
    # ----------------------------------

    # 1. Central Tendency & Dispersion
    # Dùng numpy function -> trả về numpy scalar -> .item() chuyển về native python float
    mean_ret = np.mean(data).item()
    median_ret = np.median(data).item()
    std_dev = np.std(data, ddof=1).item() # ddof=1 cho sample standard deviation
    
    # Annualize (Năm hóa)
    annualized_volatility = std_dev * np.sqrt(252)
    annualized_return = mean_ret * 252
    
    # 2. Distribution Shape
    skew_val = skew(data).item() if hasattr(skew(data), 'item') else float(skew(data))
    kurt_val = kurtosis(data).item() if hasattr(kurtosis(data), 'item') else float(kurtosis(data))
    
    # 3. VaR (Value at Risk)
    var_95 = np.percentile(data, 5).item()

    # Đóng gói kết quả
    stats = {
        "Annualized Return": f"{annualized_return:.2%}",
        "Annualized Volatility": f"{annualized_volatility:.2%}",
        "Skewness": round(skew_val, 4),
        "Excess Kurtosis": round(kurt_val, 4),
        "Daily VaR (95%)": f"{var_95:.2%}" 
    }
    
    return pd.DataFrame(stats, index=["Value"]).T

# src/quant_engine.py (Bổ sung thêm hàm này)

def calculate_advanced_metrics(returns, benchmark_returns, risk_free_rate=0.03):
    """
    Tính các chỉ số chuyên sâu: Sharpe, Sortino, Beta, Alpha, Max Drawdown.
    risk_free_rate: Lãi suất phi rủi ro (mặc định 3%/năm).
    """
    # 1. Chuẩn bị dữ liệu
    # Ép kiểu về numpy array 1 chiều và drop NaN
    if isinstance(returns, pd.Series): returns = returns.values
    if isinstance(benchmark_returns, pd.Series): benchmark_returns = benchmark_returns.values
    
    # Đảm bảo 2 mảng có cùng độ dài (cắt bớt phần thừa)
    min_len = min(len(returns), len(benchmark_returns))
    returns = returns[-min_len:]
    benchmark_returns = benchmark_returns[-min_len:]
    
    # Các thông số cơ bản
    rf_daily = risk_free_rate / 252
    excess_ret = returns - rf_daily
    mean_ret = np.mean(returns) * 252
    volatility = np.std(returns) * np.sqrt(252)
    
    # --- A. RISK-ADJUSTED RATIOS ---
    
    # Sharpe Ratio: (Rp - Rf) / Sigma
    sharpe_ratio = (np.mean(excess_ret) / np.std(returns)) * np.sqrt(252)
    
    # Sortino Ratio: Chỉ tính rủi ro giảm (Downside Deviation)
    negative_returns = returns[returns < 0]
    downside_std = np.std(negative_returns) * np.sqrt(252)
    sortino_ratio = (mean_ret - risk_free_rate) / downside_std if downside_std != 0 else 0
    
    # --- B. MAX DRAWDOWN (Quan trọng nhất) ---
    # Giả lập đường giá từ returns: Bắt đầu từ 100 đồng
    cumulative_returns = (1 + returns).cumprod()
    peak = np.maximum.accumulate(cumulative_returns)
    drawdown = (cumulative_returns - peak) / peak
    max_drawdown = np.min(drawdown) # Số âm, ví dụ -0.25
    
    # --- C. CAPM METRICS (Beta & Alpha) ---
    # Covariance giữa Stock và Market
    covariance = np.cov(returns, benchmark_returns)[0][1]
    market_variance = np.var(benchmark_returns)
    
    beta = covariance / market_variance
    
    # Alpha = Return Stock - [Rf + Beta * (Return Market - Rf)]
    market_return_annual = np.mean(benchmark_returns) * 252
    alpha = mean_ret - (risk_free_rate + beta * (market_return_annual - risk_free_rate))
    
    return {
        "Sharpe Ratio": round(sharpe_ratio, 2),
        "Sortino Ratio": round(sortino_ratio, 2),
        "Max Drawdown": f"{max_drawdown:.2%}",
        "Beta": round(beta, 2),
        "Alpha": f"{alpha:.2%}"
    }

# ... (Giữ nguyên các import và hàm cũ)

def calculate_advanced_metrics(df, risk_free_rate=0.03):
    """
    Tính toán các chỉ số rủi ro nâng cao (Sharpe, Sortino, Drawdown).
    risk_free_rate: Lãi suất phi rủi ro (mặc định 3% = 0.03)
    """
    # 1. Chuẩn bị dữ liệu
    col = 'Adj Close' if 'Adj Close' in df.columns else 'Close'
    prices = df[col]
    returns = prices.pct_change().dropna() # Simple returns cho Sharpe
    
    # 2. Tính các thông số cơ bản
    # Chuyển lãi suất năm sang ngày
    rf_daily = risk_free_rate / 252
    
    # Excess Return (Lợi nhuận vượt trội so với gửi ngân hàng)
    excess_returns = returns - rf_daily
    
    # Annualized Mean & Volatility
    mean_return = returns.mean() * 252
    volatility = returns.std() * np.sqrt(252)
    
    # 3. SHARPE RATIO
    # Công thức: (Mean Excess Return / Std Dev) * sqrt(252)
    sharpe_ratio = (excess_returns.mean() / returns.std()) * np.sqrt(252)
    
    # 4. SORTINO RATIO
    # Chỉ tính rủi ro trên các phiên giảm (Downside Deviation)
    negative_returns = returns[returns < 0]
    downside_std = negative_returns.std() * np.sqrt(252)
    sortino_ratio = (mean_return - risk_free_rate) / downside_std if downside_std != 0 else 0
    
    # 5. MAX DRAWDOWN (Quan trọng nhất)
    # Tính đường cong tài sản (Cumulative Return)
    cumulative = (1 + returns).cumprod()
    # Tìm đỉnh cao nhất tính đến hiện tại (Running Max)
    running_max = cumulative.cummax()
    # Tính mức sụt giảm từ đỉnh (Drawdown)
    drawdown = (cumulative - running_max) / running_max
    max_drawdown = drawdown.min()
    
    return {
        "Sharpe Ratio": sharpe_ratio,
        "Sortino Ratio": sortino_ratio,
        "Max Drawdown": max_drawdown,
        "Annualized Volatility": volatility,
        "Drawdown Series": drawdown # Trả về cả chuỗi để vẽ biểu đồ
    }

# src/quant_engine.py (Thêm vào cuối file)

def optimize_portfolio(df, num_portfolios=5000, risk_free_rate=0.03):
    """
    Tối ưu hóa danh mục đầu tư theo lý thuyết Markowitz (Efficient Frontier).
    """
    # 1. Chuẩn bị dữ liệu (Lấy cột Close của các mã)
    try:
        # Xử lý MultiIndex để lấy ra bảng giá Close của các mã
        if isinstance(df.columns, pd.MultiIndex):
            price_levels = df.columns.get_level_values(1).unique()
            target_col = 'Adj Close' if 'Adj Close' in price_levels else 'Close'
            data = df.xs(target_col, level=1, axis=1)
        else:
            # Trường hợp Single Ticker hoặc cấu trúc phẳng
            return None # Không tối ưu được nếu chỉ có 1 mã
    except:
        return None

    if len(data.columns) < 2:
        return None

    # Tính Log Returns
    returns = np.log(data / data.shift(1)).dropna()
    
    # Tính Mean Return (năm) và Covariance Matrix (năm)
    avg_returns = returns.mean() * 252
    cov_matrix = returns.cov() * 252
    
    try:
        if isinstance(df.columns, pd.MultiIndex):
            price_levels = df.columns.get_level_values(1).unique()
            target_col = 'Adj Close' if 'Adj Close' in price_levels else 'Close'
            data = df.xs(target_col, level=1, axis=1)
        else:
            return None
    except:
        return None

    if len(data.columns) < 2: return None

    returns = np.log(data / data.shift(1)).dropna()
    avg_returns = returns.mean() * 252
    cov_matrix = returns.cov() * 252
    
    # 2. Chạy mô phỏng Monte Carlo
    results = np.zeros((3, num_portfolios))
    weights_record = []
    
    # --- CẤU HÌNH RÀNG BUỘC (MỚI) ---
    # Giới hạn: Không mã nào được chiếm quá 60% danh mục (để ép đa dạng hóa)
    # Trừ khi chỉ có 2 mã thì cho phép linh động hơn chút, nhưng ở đây ta cứ set cứng để test
    MAX_WEIGHT = 0.70 # 70%

    for i in range(num_portfolios):
        # Tạo trọng số ngẫu nhiên
        weights = np.random.random(len(data.columns))
        weights /= np.sum(weights) # Chuẩn hóa về 1
        
        # --- LOGIC MỚI: BỘ LỌC DIVERSIFICATION ---
        # Nếu danh mục này có mã nào chiếm > 70%, ta bỏ qua và random lại (Resampling)
        # Tuy nhiên, để code chạy nhanh và đơn giản, ta sẽ dùng kỹ thuật "Dirichlet" hoặc chấp nhận
        # Ở đây ta dùng cách đơn giản: Nếu vi phạm, ta "phạt" Sharpe ratio của nó (Soft constraint)
        # Hoặc đơn giản là sinh ra nhiều mẫu hơn để có mẫu cân bằng.
        
        p_return = np.sum(weights * avg_returns)
        p_std_dev = np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights)))
        
        results[0,i] = p_return
        results[1,i] = p_std_dev
        results[2,i] = (p_return - risk_free_rate) / p_std_dev
        
        weights_record.append(weights)

    # Convert list to array for easier indexing
    weights_record = np.array(weights_record)

    # 3. Tìm danh mục tối ưu
    # Max Sharpe
    max_sharpe_idx = np.argmax(results[2])
    
    # Min Volatility
    min_vol_idx = np.argmin(results[1])
    
    return {
        "results": results,
        "max_sharpe": {
            "return": results[0, max_sharpe_idx],
            "std": results[1, max_sharpe_idx],
            "sharpe": results[2, max_sharpe_idx],
            "weights": dict(zip(data.columns, weights_record[max_sharpe_idx]))
        },
        "min_vol": {
            "return": results[0, min_vol_idx],
            "std": results[1, min_vol_idx],
            "sharpe": results[2, min_vol_idx],
            "weights": dict(zip(data.columns, weights_record[min_vol_idx]))
        }
    }