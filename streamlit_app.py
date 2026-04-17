import streamlit as st
import pandas as pd
import plotly.express as px
from io import BytesIO

# --- 1. CẤU HÌNH TRANG ---
st.set_page_config(page_title="HSE Master Dashboard", layout="wide")

def process_data(df, df_gv=None):
    # Chuẩn hóa tên cột
    df.columns = [str(c).strip() for c in df.columns]
    
    # Yêu cầu các cột cần thiết từ Sheet 3, bỏ qua cột '% Phản hồi Chung'
    req = ['Lớp', 'Môn', 'Tong_Luot_Giao_Bai', 'Tong_Hoan_Thanh']
    
    if not all(c in df.columns for c in req):
        st.error(f"File HSE (Sheet 3) thiếu cột. Cần có: {req}")
        st.stop()
        
    # Lọc lấy dữ liệu cần và chuyển kiểu số
    df = df[req].copy()
    df['Tong_Luot_Giao_Bai'] = pd.to_numeric(df['Tong_Luot_Giao_Bai'], errors='coerce').fillna(0)
    df['Tong_Hoan_Thanh'] = pd.to_numeric(df['Tong_Hoan_Thanh'], errors='coerce').fillna(0)
    
    # Chuẩn hóa văn bản
    df['Lớp'] = df['Lớp'].astype(str).str.strip().str.upper()
    df['Môn'] = df['Môn'].astype(str).str.strip()
    
    teacher_main_subject = {} 
    
    # Xử lý file GVBM từ GitHub và Merge (Giữ nguyên cấu hình cũ)
    if df_gv is not None:
        df_gv.columns = [str(c).strip() for c in df_gv.columns]
        gv_col = next((col for col in df_gv.columns if 'giáo viên' in col.lower() or 'gv' in col.lower()), 'Giáo Viên')
        
        if 'Lớp' in df_gv.columns and 'Môn' in df_gv.columns and gv_col in df_gv.columns:
            df_gv = df_gv.rename(columns={gv_col: 'Giáo Viên'})
            df_gv['Lớp'] = df_gv['Lớp'].astype(str).str.strip().str.upper()
            df_gv['Môn'] = df_gv['Môn'].astype(str).str.strip()
            df_gv['Giáo Viên'] = df_gv['Giáo Viên'].astype(str).str.strip()
            
            # Tìm môn chính của giáo viên (loại bỏ HĐTN)
            for gv, group in df_gv.groupby('Giáo Viên'):
                if pd.isna(gv) or gv == "nan" or gv == "": continue
                subjects = group['Môn'].dropna().unique()
                main_subs = [s for s in subjects if "trải nghiệm" not in str(s).lower() and "hđtn" not in str(s).lower()]
                if main_subs:
                    teacher_main_subject[gv] = main_subs[0]
            
            df_gv_unique = df_gv[['Lớp', 'Môn', 'Giáo Viên']].drop_duplicates()
            df = pd.merge(df, df_gv_unique, on=['Lớp', 'Môn'], how='left')

    if 'Giáo Viên' not in df.columns:
        df['Giáo Viên'] = "Chưa cập nhật"
    else:
        df['Giáo Viên'] = df['Giáo Viên'].fillna("Chưa cập nhật")
        
    # Logic đổi tên môn trải nghiệm thành môn chính
    def rename_subject(row):
        mon = str(row['Môn'])
        gv = row['Giáo Viên']
        if "trải nghiệm" in mon.lower() or "hđtn" in mon.lower():
            return teacher_main_subject.get(gv, mon)
        return mon
        
    df['Môn'] = df.apply(rename_subject, axis=1)

    # Gộp dòng (Trải nghiệm + Môn chính)
    df = df.groupby(['Lớp', 'Môn', 'Giáo Viên'], as_index=False).agg({
        'Tong_Luot_Giao_Bai': 'sum',
        'Tong_Hoan_Thanh': 'sum'
    })
    
    df['Ty_le'] = (df['Tong_Hoan_Thanh'] / df['Tong_Luot_Giao_Bai'] * 100).round(1).fillna(0)
    return df

def to_excel_with_style(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Bao_Cao_Chi_Tiet')
        workbook  = writer.book
        worksheet = writer.sheets['Bao_Cao_Chi_Tiet']
        format_red = workbook.add_format({'bg_color': '#FFC7CE', 'font_color': '#9C0006'})
        if 'Ty_le' in df.columns:
            worksheet.conditional_format(1, df.columns.get_loc('Ty_le'), len(df), df.columns.get_loc('Ty_le'),
                                        {'type': 'cell', 'criteria': '<', 'value': 50, 'format': format_red})
    return output.getvalue()

# --- 2. TẢI DỮ LIỆU ---
st.title("🛡️ HSE Master Dashboard - Phân tích Sheet 3")

st.sidebar.header("📂 Tải Dữ Liệu")
uploaded_file = st.sidebar.file_uploader("Tải lên file Excel HSE (Có 3 sheet)", type=["xlsx"])

# Link dữ liệu Giáo viên GitHub
GV_DATA_URL = "https://raw.githubusercontent.com/hieudtse160939/HSE_Dashboard/a521cfd39d4b59e0e7af63db9e140f61c9e84a56/BM1.xlsx"

@st.cache_data(show_spinner=False)
def load_gv_data():
    try: return pd.read_excel(GV_DATA_URL)
    except: return None

df_gv = load_gv_data()
if df_gv is not None:
    st.sidebar.success("✅ Đã đồng bộ Giáo viên từ GitHub!")

if uploaded_file:
    with st.spinner('Đang đọc dữ liệu từ Sheet 3...'):
        # Đọc cụ thể Sheet 3 (sheet_name=2)
        raw_df = pd.read_excel(uploaded_file, sheet_name=2)
        df = process_data(raw_df, df_gv)
else:
    st.info("👈 Vui lòng tải file Excel HSE để xem báo cáo.")
    st.stop()

# --- 3. BỘ LỌC ---
st.sidebar.divider()
st.sidebar.header("🎯 Phạm vi báo cáo")
list_classes = ["Tất cả các lớp"] + sorted(df['Lớp'].unique().tolist())
selected_class = st.sidebar.selectbox("Lọc theo Lớp:", list_classes)

list_teachers = ["Tất cả Giáo viên"] + sorted(df['Giáo Viên'].unique().tolist())
selected_teacher = st.sidebar.selectbox("Lọc theo Giáo Viên:", list_teachers)

filtered_df = df.copy()
if selected_class != "Tất cả các lớp":
    filtered_df = filtered_df[filtered_df['Lớp'] == selected_class]
if selected_teacher != "Tất cả Giáo viên":
    filtered_df = filtered_df[filtered_df['Giáo Viên'] == selected_teacher]

st.sidebar.download_button(
    label="📥 Tải Báo cáo Excel đã lọc",
    data=to_excel_with_style(filtered_df),
    file_name="Bao_Cao_HSE_Sheet3.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)

# --- 4. HIỂN THỊ PHÂN TÍCH ---
if selected_class == "Tất cả các lớp" and selected_teacher == "Tất cả Giáo viên":
    st.header("🌍 Phân tích Tổng thể Toàn trường")
    
    tab_lop, tab_gv, tab_mon = st.tabs(["📊 Tổng hợp Lớp", "👩‍🏫 Tổng hợp Giáo Viên", "🍕 Thống kê Môn học"])
    
    with tab_lop:
        # Heatmap như cấu hình cũ
        heatmap_data = df.pivot_table(index='Lớp', columns='Môn', values='Ty_le').fillna(0)
        fig_heat = px.imshow(heatmap_data, text_auto=True, color_continuous_scale='RdYlGn', aspect="auto")
        st.plotly_chart(fig_heat, use_container_width=True)
        
    with tab_gv:
        teacher_rank = df.groupby('Giáo Viên').agg({
            'Lớp': 'count', 'Tong_Luot_Giao_Bai': 'sum', 'Tong_Hoan_Thanh': 'sum'
        }).reset_index()
        teacher_rank['Ty_le_TB'] = (teacher_rank['Tong_Hoan_Thanh'] / teacher_rank['Tong_Luot_Giao_Bai'] * 100).round(1)
        st.dataframe(teacher_rank.sort_values('Ty_le_TB', ascending=False), use_container_width=True, hide_index=True)

    with tab_mon:
        st.subheader("Tỷ lệ hoàn thành theo Môn học")
        # Thống kê theo môn học
        subject_stats = df.groupby('Môn').agg({
            'Tong_Luot_Giao_Bai': 'sum',
            'Tong_Hoan_Thanh': 'sum'
        }).reset_index()
        subject_stats['Ty_le_Hoan_Thanh'] = (subject_stats['Tong_Hoan_Thanh'] / subject_stats['Tong_Luot_Giao_Bai'] * 100).round(1)
        
        col_m1, col_m2 = st.columns([1, 1])
        with col_m1:
            st.write("**Bảng thống kê tỷ lệ môn học**")
            st.dataframe(subject_stats.sort_values('Ty_le_Hoan_Thanh', ascending=False), hide_index=True, use_container_width=True)
        
        with col_m2:
            st.write("**Biểu đồ Bánh: Tỷ trọng hoàn thành giữa các môn**")
            fig_pie = px.pie(
                subject_stats, 
                values='Tong_Hoan_Thanh', 
                names='Môn', 
                hole=0.4,
                color_discrete_sequence=px.colors.qualitative.Set3
            )
            fig_pie.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig_pie, use_container_width=True)

else:
    # PHẦN CHI TIẾT (KHI CHỌN LỌC)
    st.header(f"📝 Chi tiết: {selected_class} / {selected_teacher}")
    if not filtered_df.empty:
        fig = px.bar(
            filtered_df, x='Môn', y='Ty_le', text='Ty_le', color='Ty_le',
            color_continuous_scale='RdYlGn', title="Tỷ lệ hoàn thành (%) theo từng môn"
        )
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(filtered_df[['Lớp', 'Môn', 'Giáo Viên', 'Tong_Luot_Giao_Bai', 'Tong_Hoan_Thanh', 'Ty_le']], use_container_width=True, hide_index=True)
