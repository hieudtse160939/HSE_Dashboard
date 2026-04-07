import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from io import BytesIO

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

# Hàm tạo file Excel có tô màu
def to_excel_with_style(df):
    output = BytesIO()
    # Sử dụng XlsxWriter làm engine để format màu
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Bao_Cao_Chi_Tiet')
        workbook  = writer.book
        worksheet = writer.sheets['Bao_Cao_Chi_Tiet']

        # Định nghĩa các format màu
        format_red = workbook.add_format({'bg_color': '#FFC7CE', 'font_color': '#9C0006'})
        format_yellow = workbook.add_format({'bg_color': '#FFEB9C', 'font_color': '#9C6500'})
        format_green = workbook.add_format({'bg_color': '#C6EFCE', 'font_color': '#006100'})

        # Áp dụng Conditional Formatting cho cột Tỷ lệ (Giả định là cột E - index 4)
        # Tìm vị trí cột 'Ty_le'
        col_idx = df.columns.get_loc('Ty_le')
        row_count = len(df)

        worksheet.conditional_format(1, col_idx, row_count, col_idx,
                                    {'type': 'cell', 'criteria': '<', 'value': 50, 'format': format_red})
        worksheet.conditional_format(1, col_idx, row_count, col_idx,
                                    {'type': 'cell', 'criteria': 'between', 'minimum': 50, 'maximum': 80, 'format': format_yellow})
        worksheet.conditional_format(1, col_idx, row_count, col_idx,
                                    {'type': 'cell', 'criteria': '>', 'value': 80, 'format': format_green})
        
    return output.getvalue()

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

# --- 3. BỘ LỌC & NÚT TẢI ---
st.sidebar.header("Phạm vi báo cáo")
list_classes = ["Tất cả các lớp"] + sorted(df['Lớp'].unique().tolist())
selected_class = st.sidebar.selectbox("🎯 Chọn đối tượng phân tích:", list_classes)

# Nút tải file nằm ở Sidebar
st.sidebar.divider()
st.sidebar.subheader("📤 Xuất dữ liệu")
excel_data = to_excel_with_style(df if selected_class == "Tất cả các lớp" else df[df['Lớp'] == selected_class])
st.sidebar.download_button(
    label="📥 Tải Báo cáo Excel cho GVCN",
    data=excel_data,
    file_name=f"Bao_Cao_HSE_{selected_class.replace(' ', '_')}.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)

# --- 4. HIỂN THỊ PHÂN TÍCH ---
if selected_class == "Tất cả các lớp":
    st.header("🌍 Phân tích Tổng thể Toàn trường")
    class_rank = df.groupby('Lớp').agg({'Tong_Luot_Giao_Bai': 'sum', 'Tong_Hoan_Thanh': 'sum'}).reset_index()
    class_rank['Ty_le_TB'] = (class_rank['Tong_Hoan_Thanh'] / class_rank['Tong_Luot_Giao_Bai'] * 100).round(1)
    class_rank = class_rank.sort_values('Ty_le_TB', ascending=False)

    c1, c2, c3 = st.columns(3)
    c1.metric("Hiệu suất Trung bình Trường", f"{class_rank['Ty_le_TB'].mean():.1f}%")
    c2.metric("Lớp dẫn đầu", f"{class_rank.iloc[0]['Lớp']} ({class_rank.iloc[0]['Ty_le_TB']}%)")
    c3.metric("Lớp thấp nhất", f"{class_rank.iloc[-1]['Lớp']} ({class_rank.iloc[-1]['Ty_le_TB']}%)")

    st.divider()
    st.subheader("🌡️ Bản đồ nhiệt (Heatmap) Toàn trường")
    heatmap_data = df.pivot_table(index='Lớp', columns='Môn', values='Ty_le').fillna(0)
    fig_heat = px.imshow(heatmap_data, text_auto=True, color_continuous_scale='RdYlGn', aspect="auto")
    st.plotly_chart(fig_heat, use_container_width=True)
else:
    st.header(f"📝 Phân tích chi tiết: {selected_class}")
    class_df = df[df['Lớp'] == selected_class]
    
    col_i1, col_i2 = st.columns([1, 2])
    with col_i1:
        st.subheader("💡 Nhận xét")
        avg_class = class_df['Ty_le'].mean()
        st.write(f"Hiệu suất lớp đạt **{avg_class:.1f}%**.")
        best = class_df.loc[class_df['Ty_le'].idxmax()]
        st.success(f"🌟 Tốt nhất: {best['Môn']} ({best['Ty_le']}%)")
        danger = class_df[class_df['Ty_le'] < 50]['Môn'].tolist()
        if danger: st.error(f"❗ Cần nhắc GVCN: {', '.join(danger)}")
    
    with col_i2:
        fig = px.bar(class_df, x='Môn', y='Ty_le', text='Ty_le', color='Ty_le', color_continuous_scale='RdYlGn')
        st.plotly_chart(fig, use_container_width=True)
