import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# --- 1. CẤU HÌNH ---
st.set_page_config(page_title="HSE Master Dashboard", layout="wide")

def process_data(df):
    df.columns = [str(c).strip() for c in df.columns]
    req = ['Lớp', 'Môn', 'Tong_Luot_Giao_Bai', 'Tong_Hoan_Thanh']
    if not all(c in df.columns for c in req):
        st.error(f"File thiếu cột. Cần có: {req}")
        st.stop()
    df['Tong_Luot_Giao_Bai'] = pd.to_numeric(df['Tong_Luot_Giao_Bai'], errors='coerce').fillna(0)
    df['Tong_Hoan_Thanh'] = pd.to_numeric(df['Tong_Hoan_Thanh'], errors='coerce').fillna(0)
    df['Ty_le'] = (df['Tong_Hoan_Thanh'] / df['Tong_Luot_Giao_Bai'] * 100).round(1).fillna(0)
    return df

# --- 2. LOAD DATA ---
st.title("🛡️ Hệ thống Quản lý & Phân tích HSE")

uploaded_file = st.file_uploader("Tải file Excel báo cáo chi tiết", type=["xlsx"])

if uploaded_file:
    df = process_data(pd.read_excel(uploaded_file))
else:
    try:
        df = process_data(pd.read_excel("Bao_Cao_HSE_Phan_Hoi_Chi_Tiet.xlsx"))
    except:
        st.warning("Vui lòng tải file để bắt đầu.")
        st.stop()

# --- 3. DROPDOWN CHỌN LỚP ---
st.sidebar.header("Phạm vi báo cáo")
list_classes = ["Tất cả các lớp"] + sorted(df['Lớp'].unique().tolist())
selected_class = st.sidebar.selectbox("🎯 Chọn đối tượng phân tích:", list_classes)

# --- 4. XỬ LÝ HIỂN THỊ ---

if selected_class == "Tất cả các lớp":
    # --- PHÂN TÍCH TỔNG TOÀN TRƯỜNG ---
    st.header("🌍 Phân tích Tổng thể Toàn trường")
    
    # Tính toán bảng xếp hạng theo lớp
    class_rank = df.groupby('Lớp').agg({
        'Tong_Luot_Giao_Bai': 'sum',
        'Tong_Hoan_Thanh': 'sum'
    }).reset_index()
    class_rank['Ty_le_TB'] = (class_rank['Tong_Hoan_Thanh'] / class_rank['Tong_Luot_Giao_Bai'] * 100).round(1)
    class_rank = class_rank.sort_values('Ty_le_TB', ascending=False)

    # Metrics tổng
    avg_school = class_rank['Ty_le_TB'].mean()
    col1, col2, col3 = st.columns(3)
    col1.metric("Hiệu suất Trung bình Trường", f"{avg_school:.1f}%")
    col2.metric("Lớp dẫn đầu", f"{class_rank.iloc[0]['Lớp']} ({class_rank.iloc[0]['Ty_le_TB']}%)")
    col3.metric("Lớp thấp nhất", f"{class_rank.iloc[-1]['Lớp']} ({class_rank.iloc[-1]['Ty_le_TB']}%)")

    st.divider()
    
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("🏆 Xếp hạng Hiệu suất các Lớp")
        fig_rank = px.bar(class_rank, x='Lớp', y='Ty_le_TB', text='Ty_le_TB',
                          color='Ty_le_TB', color_continuous_scale='RdYlGn')
        st.plotly_chart(fig_rank, use_container_width=True)
    
    with c2:
        st.subheader("📚 Hiệu suất theo Môn học (Toàn trường)")
        sub_rank = df.groupby('Môn')['Ty_le'].mean().reset_index().sort_values('Ty_le', ascending=False)
        fig_sub = px.bar(sub_rank, x='Ty_le', y='Môn', orientation='h', color='Ty_le', color_continuous_scale='Blues')
        st.plotly_chart(fig_sub, use_container_width=True)

    st.subheader("🌡️ Bản đồ nhiệt (Heatmap): Tỷ lệ hoàn thành chi tiết")
    heatmap_data = df.pivot_table(index='Lớp', columns='Môn', values='Ty_le').fillna(0)
    fig_heat = px.imshow(heatmap_data, text_auto=True, color_continuous_scale='RdYlGn', aspect="auto")
    st.plotly_chart(fig_heat, use_container_width=True)

else:
    # --- PHÂN TÍCH TỪNG LỚP (NHƯ CŨ) ---
    st.header(f"📝 Phân tích chi tiết: {selected_class}")
    class_df = df[df['Lớp'] == selected_class]
    avg_school = df['Ty_le'].mean()
    avg_class = class_df['Ty_le'].mean()

    col_i1, col_i2 = st.columns([1, 2])
    with col_i1:
        st.subheader("💡 Nhận xét nhanh")
        color = "green" if avg_class > avg_school else "red"
        status = "CAO HƠN" if avg_class > avg_school else "THẤP HƠN"
        st.markdown(f"Hiệu suất lớp: **{avg_class:.1f}%** (:{color}[**{status}**] TB trường {avg_school:.1f}%)")
        
        best = class_df.loc[class_df['Ty_le'].idxmax()]
        st.write(f"🌟 **Môn tốt nhất:** {best['Môn']} ({best['Ty_le']}%)")
        
        danger = class_df[class_df['Ty_le'] < 50]['Môn'].tolist()
        if danger: st.error(f"❗ Cần đôn đốc: {', '.join(danger)}")
    
    with col_i2:
        fig = px.bar(class_df, x='Môn', y='Ty_le', text='Ty_le', color='Ty_le', color_continuous_scale='RdYlGn', range_color=[0,100])
        st.plotly_chart(fig, use_container_width=True)

# --- 5. ĐỀ XUẤT XUẤT FILE ---
st.sidebar.divider()
st.sidebar.subheader("📤 Xuất báo cáo cho GVCN")
st.sidebar.info("Đề xuất: Xuất file Excel kèm 'Màu sắc cảnh báo' (Conditional Formatting) để gửi cho các GVCN.")

# Nút giả lập (Dành cho việc hướng dẫn)
if st.sidebar.button("Tạo file báo cáo GVCN (.xlsx)"):
    st.sidebar.success("Đã sẵn sàng file: Bao_Cao_Tong_Hop_GVCN.xlsx")
