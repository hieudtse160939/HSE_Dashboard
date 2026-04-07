import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# --- 1. CẤU HÌNH ---
st.set_page_config(page_title="HSE Smart Dashboard", layout="wide")

def process_data(df):
    # Xử lý tiêu đề: Xóa khoảng trắng thừa và chuyển về string
    df.columns = [str(c).strip() for c in df.columns]
    
    # Kiểm tra các cột cần thiết (Case-sensitive: Phải khớp từng chữ)
    required_cols = ['Lớp', 'Môn', 'Tong_Luot_Giao_Bai', 'Tong_Hoan_Thanh']
    
    # Tìm xem có cột nào bị thiếu không
    missing = [c for c in required_cols if c not in df.columns]
    
    if missing:
        st.error(f"❌ Không tìm thấy cột: {', '.join(missing)}")
        st.info(f"Các cột hiện có trong file của bạn là: {list(df.columns)}")
        st.warning("Mẹo: Hãy kiểm tra xem tên cột trong Excel có đúng là 'Tong_Luot_Giao_Bai' và 'Tong_Hoan_Thanh' không.")
        st.stop()
    
    # Chuyển đổi dữ liệu sang dạng số (tránh lỗi nếu có ô trống hoặc chữ)
    df['Tong_Luot_Giao_Bai'] = pd.to_numeric(df['Tong_Luot_Giao_Bai'], errors='coerce').fillna(0)
    df['Tong_Hoan_Thanh'] = pd.to_numeric(df['Tong_Hoan_Thanh'], errors='coerce').fillna(0)
    
    # Tính tỷ lệ %
    df['Ty_le'] = (df['Tong_Hoan_Thanh'] / df['Tong_Luot_Giao_Bai'] * 100).round(1)
    df['Ty_le'] = df['Ty_le'].replace([float('inf'), -float('inf')], 0).fillna(0)
    
    return df

# --- 2. GIAO DIỆN TẢI FILE ---
st.title("📊 Báo cáo Học tập theo Lớp")

uploaded_file = st.file_uploader("Bước 1: Tải file Bao_Cao_HSE_Phan_Hoi_Chi_Tiet.xlsx", type=["xlsx"])

if uploaded_file:
    # Đọc file (mặc định lấy sheet đầu tiên)
    raw_df = pd.read_excel(uploaded_file)
    df = process_data(raw_df)
else:
    st.info("👆 Vui lòng tải file Excel lên để xem báo cáo.")
    st.stop()

# --- 3. THANH DROPDOWN CHỌN LỚP ---
st.sidebar.header("Bộ lọc")
list_classes = sorted(df['Lớp'].unique().tolist())
selected_class = st.sidebar.selectbox("🎯 Chọn Lớp để xem chi tiết:", list_classes)

# Lọc dữ liệu cho lớp được chọn
class_df = df[df['Lớp'] == selected_class]
avg_school = df['Ty_le'].mean()
avg_class = class_df['Ty_le'].mean()

# --- 4. HIỂN THỊ Ý KIẾN & NHẬN XÉT ---
st.header(f"📝 Nhận xét báo cáo: {selected_class}")

col_note, col_chart = st.columns([1, 2])

with col_note:
    st.subheader("💡 Phân tích nhanh")
    
    # Nhận xét về hiệu suất
    diff = avg_class - avg_school
    status = "CAO HƠN" if diff > 0 else "THẤP HƠN"
    color = "green" if diff > 0 else "red"
    
    st.markdown(f"Hiệu suất trung bình của lớp là **{avg_class:.1f}%**, "
                f"<{span style='color:{color}'>**{status}**</span> bình quân toàn trường ({avg_school:.1f}%).")

    # Môn tốt nhất / yếu nhất
    best = class_df.loc[class_df['Ty_le'].idxmax()]
    worst = class_df.loc[class_df['Ty_le'].idxmin()]
    
    st.write(f"✅ **Môn hoàn thành tốt nhất:** {best['Môn']} ({best['Ty_le']}%)")
    st.write(f"⚠️ **Môn cần đôn đốc thêm:** {worst['Môn']} ({worst['Ty_le']}%)")

    # Cảnh báo môn dưới 50%
    danger_zone = class_df[class_df['Ty_le'] < 50]['Môn'].tolist()
    if danger_zone:
        st.error(f"🚨 Cảnh báo môn học yếu (<50%): {', '.join(danger_zone)}")

with col_chart:
    # Biểu đồ cột tỷ lệ % của lớp đó
    fig = px.bar(class_df, x='Môn', y='Ty_le', text='Ty_le', 
                 color='Ty_le', color_continuous_scale='RdYlGn',
                 range_color=[0, 100], title=f"Tỷ lệ hoàn thành lớp {selected_class}")
    st.plotly_chart(fig, use_container_width=True)

# --- 5. SO SÁNH SỐ LƯỢNG CHI TIẾT ---
st.divider()
st.subheader("📋 Chi tiết số lượng Bài giao & Hoàn thành")

fig_compare = go.Figure(data=[
    go.Bar(name='Số lượng giao', x=class_df['Môn'], y=class_df['Tong_Luot_Giao_Bai'], marker_color='#3498db'),
    go.Bar(name='Đã hoàn thành', x=class_df['Môn'], y=class_df['Tong_Hoan_Thanh'], marker_color='#2ecc71')
])
fig_compare.update_layout(barmode='group', height=400)
st.plotly_chart(fig_compare, use_container_width=True)

# Hiển thị bảng dữ liệu cuối trang
with st.expander("Xem bảng dữ liệu gốc của lớp"):
    st.dataframe(class_df[['Môn', 'Tong_Luot_Giao_Bai', 'Tong_Hoan_Thanh', 'Ty_le']])
