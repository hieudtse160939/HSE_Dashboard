import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# --- CẤU HÌNH GIAO DIỆN ---
st.set_page_config(page_title="HSE Report Dashboard", layout="wide")

# --- HÀM XỬ LÝ DỮ LIỆU ---
def process_data(df):
    # Tính tỷ lệ hoàn thành theo công thức:
    # Ty_le = (Hoàn thành / Giao bài) * 100
    df['Ty_le_Hoan_Thanh'] = (df['Tong_Hoan_Thanh'] / df['Tong_Luot_Giao_Bai'] * 100).round(2)
    df['Ty_le_Hoan_Thanh'] = df['Ty_le_Hoan_Thanh'].fillna(0) # Xử lý lỗi chia cho 0
    return df

# --- TẢI DỮ LIỆU ---
st.title("📊 Hệ thống Phân tích Phản hồi HSE Chi tiết")

# Cho phép người dùng tải file lên hoặc tự động đọc file tên 'Bao_Cao_HSE_Phan_Hoi_Chi_Tiet.xlsx'
uploaded_file = st.file_uploader("Tải lên file Excel báo cáo:", type=["xlsx"])

if uploaded_file is not None:
    df_raw = pd.read_excel(uploaded_file)
    df = process_data(df_raw)
else:
    try:
        df_raw = pd.read_excel("BC_HSE.xlsx")
        df = process_data(df_raw)
        st.info("✅ Đang sử dụng dữ liệu từ file: Bao_Cao_HSE_Phan_Hoi_Chi_Tiet.xlsx")
    except FileNotFoundError:
        st.warning("⚠️ Vui lòng tải file Excel lên hoặc để file 'Bao_Cao_HSE_Phan_Hoi_Chi_Tiet.xlsx' cùng thư mục với code.")
        st.stop()

# --- BỘ LỌC (SIDEBAR) ---
st.sidebar.header("🔍 Bộ lọc báo cáo")
selected_class = st.sidebar.selectbox("Chọn Lớp:", ["Tất cả"] + sorted(df['Lớp'].unique().tolist()))

if selected_class != "Tất cả":
    df_filtered = df[df['Lớp'] == selected_class]
else:
    df_filtered = df

selected_subject = st.sidebar.selectbox("Chọn Môn:", ["Tất cả"] + sorted(df_filtered['Môn'].unique().tolist()))

if selected_subject != "Tất cả":
    df_filtered = df_filtered[df_filtered['Môn'] == selected_subject]

# --- HIỂN THỊ CHỈ SỐ TỔNG QUAN ---
total_assigned = df_filtered['Tong_Luot_Giao_Bai'].sum()
total_done = df_filtered['Tong_Hoan_Thanh'].sum()
avg_rate = (total_done / total_assigned * 100).round(2) if total_assigned > 0 else 0

c1, c2, c3 = st.columns(3)
c1.metric("Tổng bài đã giao", f"{total_assigned:,}")
c2.metric("Tổng hoàn thành", f"{total_done:,}")
c3.metric("Hiệu suất trung bình", f"{avg_rate}%")

st.divider()

# --- BIỂU ĐỒ TƯƠNG TÁC ---
col_left, col_right = st.columns(2)

with col_left:
    st.subheader("📊 Khối lượng Giao bài vs Hoàn thành")
    # Sử dụng Bar Chart để so sánh
    fig_bar = px.bar(df_filtered, x='Môn' if selected_class != "Tất cả" else 'Lớp', 
                     y=['Tong_Luot_Giao_Bai', 'Tong_Hoan_Thanh'],
                     barmode='group', title="So sánh số lượng bài",
                     color_discrete_sequence=['#1f77b4', '#2ca02c'])
    st.plotly_chart(fig_bar, use_container_width=True)

with col_right:
    st.subheader("📈 Tỷ lệ Hoàn thành (%)")
    # Biểu đồ đường thể hiện hiệu suất
    fig_line = px.line(df_filtered, x='Môn' if selected_class != "Tất cả" else 'Lớp', 
                       y='Ty_le_Hoan_Thanh', markers=True, 
                       title="Hiệu suất học tập theo %",
                       color_discrete_sequence=['#ff7f0e'])
    st.plotly_chart(fig_line, use_container_width=True)

# --- BẢN ĐỒ NHIỆT (HEATMAP) ---
if selected_class == "Tất cả":
    st.divider()
    st.subheader("🌡️ Bản đồ nhiệt Hiệu suất (Lớp vs Môn)")
    heat_data = df.pivot_table(index='Lớp', columns='Môn', values='Ty_le_Hoan_Thanh').fillna(0)
    fig_heat = px.imshow(heat_data, text_auto=True, color_continuous_scale='RdYlGn', 
                         aspect="auto", title="Độ đậm nhạt thể hiện % hoàn thành")
    st.plotly_chart(fig_heat, use_container_width=True)

# --- BẢNG DỮ LIỆU ---
with st.expander("📝 Xem bảng dữ liệu chi tiết"):
    st.write(df_filtered)
