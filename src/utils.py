# src/utils.py
import streamlit as st
import numpy as np

def generate_sparkline_svg(data_series, color="#0ECB81", width=200, height=50):
    """Tạo mã SVG cho biểu đồ đường thu nhỏ."""
    if len(data_series) < 2: return ""
    data = np.array(data_series)
    data = data[~np.isnan(data)]
    if len(data) < 2: return ""
    
    min_val, max_val = np.min(data), np.max(data)
    if max_val == min_val: normalized = np.zeros_like(data)
    else: normalized = (data - min_val) / (max_val - min_val)
    
    points = []
    n_points = len(data)
    for i, val in enumerate(normalized):
        x = i * (width / (n_points - 1)) if n_points > 1 else 0
        y = height - (val * height)
        points.append(f"{x:.1f},{y:.1f}")
    
    polyline_points = " ".join(points)
    return f'<svg width="100%" height="100%" viewBox="0 0 {width} {height}" preserveAspectRatio="none" xmlns="http://www.w3.org/2000/svg"><polyline points="{polyline_points}" fill="none" stroke="{color}" stroke-width="2" vector-effect="non-scaling-stroke"/></svg>'

def render_metric_card(label, value, delta, delta_desc, sub_text, is_positive, sparkline_data=None):
    """Hiển thị Card HTML theo style Power BI."""
    color_class = "positive" if is_positive else "negative"
    color_hex = "#0ECB81" if is_positive else "#F6465D"
    arrow = "▲" if is_positive else "▼"
    
    sparkline_svg = ""
    if sparkline_data is not None and len(sparkline_data) > 2:
        sparkline_svg = generate_sparkline_svg(sparkline_data, color=color_hex)
    
    html_code = f"""
    <div class="metric-card">
        <div>
            <div class="metric-label">{label}</div>
            <div class="metric-value">{value}</div>
        </div>
        <div class="metric-bottom-container">
            <div class="metric-delta {color_class}">
                <span>{arrow} {delta}</span>
                <span style="color: #848e9c; font-size: 12px; font-weight: 400;">vs {delta_desc}</span>
            </div>
            <div class="sparkline-container">{sparkline_svg}</div>
            <div class="metric-sub">{sub_text}</div>
        </div>
    </div>"""
    st.markdown(html_code, unsafe_allow_html=True)