import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# --- 1. CẤU HÌNH GIAO DIỆN ---
st.set_page_config(page_title="HSE Smart Dashboard", layout="wide")

# --- 2. HÀM XỬ LÝ DỮ LIỆU ---
def process_data(df):
    # Xóa khoảng trắng thừa ở tên cột để tránh lỗi KeyError
    df.columns = [str(c).strip() for c in df.columns]
    
    # Kiểm tra các cột bắt buộc
    required_cols = ['Lớp', 'Môn', 'Tong_Luot_Giao_Bai', 'Tong_Hoan_Thanh']
    missing = [c for c in required_cols if c not in df.columns]
    
    if missing:
        st.error(f"❌ File Excel thiếu các cột: {', '.join(missing)}")
        st.stop()
    
    # Chuyển đổi dữ liệu sang dạng số
    df['Tong_Luot_Giao_Bai'] = pd.to_numeric(df['Tong_Luot_Giao_Bai'], errors='coerce').fillna(0)
    df['Tong_Hoan_Thanh'] = pd.to_numeric(df['Tong_Hoan_Thanh'], errors='coerce').fillna(0)
    
    # Tính tỷ lệ hoàn thành
    df['Ty_le'] = (df['Tong_Hoan_Thanh'] / df['Tong_Luot_Giao_Bai'] * 100).round(1)
    df['Ty_le'] = df['Ty_le'].fillna(0).replace([float('inf'), -float('inf')], 0)
    
    return df

# --- 3. GIAO DIỆN TẢI FILE ---
st.title("📊 Báo cáo Học tập Thông minh")
st.markdown("Hệ thống tự động phân tích và đưa ra nhận xét theo từng lớp.")

uploaded_file = st.file_uploader("Bước 1: Tải file Excel (Bao_Cao_HSE_Phan_Hoi_Chi_Tiet.xlsx)", type=["xlsx"])

if uploaded_file:
    # Đọc dữ liệu
    df_raw = pd.read_excel(uploaded_file)
    df = process_data(df_raw)
else:
    st.info("👆 Vui lòng tải file Excel lên để bắt đầu.")
    st.stop()

# --- 4. THANH ĐIỀU HƯỚNG (DROPDOWN CHỌN LỚP) ---
st.sidebar.header("Bộ lọc")
list_classes = sorted(df['Lớp'].unique().tolist())
selected_class = st.sidebar.selectbox("🎯 Chọn Lớp để xem nhận xét:", list_classes)

# Lọc dữ liệu cho lớp được chọn
class_df = df[df['Lớp'] == selected_class]
avg_school = df['Ty_le'].mean()
avg_class = class_df['Ty_le'].mean()

# --- 5. HIỂN THỊ Ý KIẾN & NHẬN XÉT TỰ ĐỘNG ---
st.header(f"📝 Nhận xét báo cáo: {selected_class}")

col_note, col_chart = st.columns([1, 2])

with col_note:
    st.subheader("💡 Phân tích nhanh")
    
    # Nhận xét về hiệu suất so với toàn trường
    diff = avg_class - avg_school
    status = "CAO HƠN" if diff > 0 else "THẤP HƠN"
    color_code = "green" if diff > 0 else "red"
    
    # Sử dụng cú pháp :color[text] của Streamlit để tô màu văn bản
    st.markdown(f"Hiệu suất trung bình của lớp là **{avg_class:.1f}%**, "
                f":{color_code}[**{status}**] so với bình quân toàn trường ({avg_school:.1f}%).")

    # Tìm môn tốt nhất và yếu nhất
    best_row = class_df.loc[class_df['Ty_le'].idxmax()]
    worst_row = class_df.loc[class_df['Ty_le'].idxmin()]
    
    st.write(f"✅ **Môn hoàn thành tốt nhất:** {best_row['Môn']} ({best_row['Ty_le']}%)")
    st.write(f"⚠️ **Môn cần chú ý đôn đốc:** {worst_row['Môn']} ({worst_row['Ty_le']}%)")

    # Cảnh báo các môn dưới 50%
    danger_zone = class_df[class_df['Ty_le'] < 50]['Môn'].tolist()
    if danger_zone:
        st.error(f"🚨 Các môn có tỷ lệ quá thấp (<50%): {', '.join(danger_zone)}")

with col_chart:
    # Biểu đồ cột thể hiện tỷ lệ % các môn trong lớp
    fig_rate = px.bar(class_df, x='Môn', y='Ty_le', text='Ty_le',
                      color='Ty_le', color_continuous_scale='RdYlGn',
                      range_color=[0, 100], title=f"Tỷ lệ hoàn thành (%) - {selected_class}")
    fig_rate.update_traces(textposition='outside')
    st.plotly_chart(fig_rate, use_container_width=True)

# --- 6. BIỂU ĐỒ CHI TIẾT SỐ LƯỢNG ---
st.divider()
st.subheader("📋 Chi tiết số lượng Bài giao & Hoàn thành")

fig_compare = go.Figure(data=[
    go.Bar(name='Số lượng giao bài', x=class_df['Môn'], y=class_df['Tong_Luot_Giao_Bai'], marker_color='#3498db'),
    go.Bar(name='Số lượng hoàn thành', x=class_df['Môn'], y=class_df['Tong_Hoan_Thanh'], marker_color='#2ecc71')
])
fig_compare.update_layout(barmode='group', height=400, title=f"So sánh khối lượng công việc lớp {selected_class}")
st.plotly_chart(fig_compare, use_container_width=True)

# Hiển thị bảng dữ liệu cuối trang
with st.expander("🔍 Xem bảng dữ liệu chi tiết của lớp"):
    st.dataframe(class_df[['Môn', 'Tong_Luot_Giao_Bai', 'Tong_Hoan_Thanh', 'Ty_le']], use_container_width=True)
