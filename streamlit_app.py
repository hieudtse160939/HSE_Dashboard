import streamlit as st
import pandas as pd
import plotly.express as px
from io import BytesIO

# --- 1. CẤU HÌNH ---
st.set_page_config(page_title="HSE Master Dashboard", layout="wide")

def process_data(df, df_gv=None):
    # Chuẩn hóa tên cột file HSE (Sheet 3)
    df.columns = [str(c).strip() for c in df.columns]
    
    # Chỉ lấy các cột cần thiết từ Sheet 3, bỏ qua '% Phản hồi Chung'
    req = ['Lớp', 'Môn', 'Tong_Luot_Giao_Bai', 'Tong_Hoan_Thanh']
    
    if not all(c in df.columns for c in req):
        st.error(f"File HSE thiếu cột. Cần có ít nhất: {req}")
        st.stop()
        
    df = df[req].copy()
    df['Tong_Luot_Giao_Bai'] = pd.to_numeric(df['Tong_Luot_Giao_Bai'], errors='coerce').fillna(0)
    df['Tong_Hoan_Thanh'] = pd.to_numeric(df['Tong_Hoan_Thanh'], errors='coerce').fillna(0)
    
    # Chuẩn hóa dữ liệu để Merge
    df['Lớp'] = df['Lớp'].astype(str).str.strip().str.upper()
    df['Môn'] = df['Môn'].astype(str).str.strip()
    
    teacher_main_subject = {} 
    
    # Xử lý file GVBM (Dữ liệu từ GitHub)
    if df_gv is not None:
        df_gv.columns = [str(c).strip() for c in df_gv.columns]
        gv_col = next((col for col in df_gv.columns if 'giáo viên' in col.lower() or 'gv' in col.lower()), 'Giáo Viên')
        
        if 'Lớp' in df_gv.columns and 'Môn' in df_gv.columns and gv_col in df_gv.columns:
            df_gv = df_gv.rename(columns={gv_col: 'Giáo Viên'})
            df_gv['Lớp'] = df_gv['Lớp'].astype(str).str.strip().str.upper()
            df_gv['Môn'] = df_gv['Môn'].astype(str).str.strip()
            df_gv['Giáo Viên'] = df_gv['Giáo Viên'].astype(str).str.strip()
            
            # Tìm môn chính (không phải HĐTN)
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
        
    # Đổi tên môn trải nghiệm về môn chính của giáo viên đó
    def rename_subject(row):
        mon = str(row['Môn'])
        gv = row['Giáo Viên']
        if "trải nghiệm" in mon.lower() or "hđtn" in mon.lower():
            return teacher_main_subject.get(gv, mon)
        return mon
        
    df['Môn'] = df.apply(rename_subject, axis=1)

    # Gộp dòng
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
        # Các định dạng conditional formatting giữ nguyên như cũ...
        format_red = workbook.add_format({'bg_color': '#FFC7CE', 'font_color': '#9C0006'})
        if 'Ty_le' in df.columns:
            worksheet.conditional_format(1, df.columns.get_loc('Ty_le'), len(df), df.columns.get_loc('Ty_le'),
                                        {'type': 'cell', 'criteria': '<', 'value': 50, 'format': format_red})
    return output.getvalue()

# --- 2. LOAD DATA ---
st.title("🛡️ Hệ thống Quản lý & Phân tích HSE (Sheet 3)")
st.sidebar.header("📂 Tải Dữ Liệu")

uploaded_file = st.sidebar.file_uploader("Tải lên Sheet 3 - Tổng hợp Lớp Môn", type=["xlsx", "csv"])

GV_DATA_URL = "https://raw.githubusercontent.com/hieudtse160939/HSE_Dashboard/a521cfd39d4b59e0e7af63db9e140f61c9e84a56/BM1.xlsx"

@st.cache_data(show_spinner=False)
def load_gv_data():
    try: return pd.read_excel(GV_DATA_URL)
    except: return None

df_gv = load_gv_data()

if uploaded_file:
    # Hỗ trợ cả Excel và CSV từ export
    if uploaded_file.name.endswith('.csv'):
        raw_df = pd.read_csv(uploaded_file)
    else:
        raw_df = pd.read_excel(uploaded_file)
    df = process_data(raw_df, df_gv)
else:
    st.info("👈 Vui lòng tải file Sheet 3 để bắt đầu.")
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

# --- 4. HIỂN THỊ PHÂN TÍCH ---
if selected_class == "Tất cả các lớp" and selected_teacher == "Tất cả Giáo viên":
    st.header("🌍 Phân tích Tổng thể")
    
    # Giữ nguyên tab Lớp, GV và thêm tab Môn học (Biểu đồ bánh)
    tab_lop, tab_gv, tab_mon = st.tabs(["📊 Tổng hợp Lớp", "👩‍🏫 Tổng hợp Giáo Viên", "🍕 Thống kê Môn học"])
    
    with tab_lop:
        # Code heatmap cũ của bạn
        heatmap_data = df.pivot_table(index='Lớp', columns='Môn', values='Ty_le').fillna(0)
        st.plotly_chart(px.imshow(heatmap_data, text_auto=True, color_continuous_scale='RdYlGn'), use_container_width=True)
        
    with tab_gv:
        # Code bảng xếp hạng GV cũ
        teacher_rank = df.groupby('Giáo Viên').agg({'Tong_Luot_Giao_Bai': 'sum', 'Tong_Hoan_Thanh': 'sum'}).reset_index()
        teacher_rank['Ty_le_TB'] = (teacher_rank['Tong_Hoan_Thanh'] / teacher_rank['Tong_Luot_Giao_Bai'] * 100).round(1)
        st.dataframe(teacher_rank.sort_values('Ty_le_TB', ascending=False), use_container_width=True)

    with tab_mon:
        st.subheader("Thống kê Tỷ lệ hoàn thành theo Môn học")
        subject_stats = df.groupby('Môn').agg({
            'Tong_Luot_Giao_Bai': 'sum',
            'Tong_Hoan_Thanh': 'sum'
        }).reset_index()
        subject_stats['Ty_le'] = (subject_stats['Tong_Hoan_Thanh'] / subject_stats['Tong_Luot_Giao_Bai'] * 100).round(1)

        col1, col2 = st.columns([1, 1])
        with col1:
            st.dataframe(subject_stats.sort_values('Ty_le', ascending=False), hide_index=True)
        with col2:
            # Biểu đồ bánh cho từng môn học
            fig_pie = px.pie(
                subject_stats, 
                values='Tong_Hoan_Thanh', 
                names='Môn',
                title='Tỷ trọng Hoàn thành giữa các môn',
                hole=0.4
            )
            st.plotly_chart(fig_pie, use_container_width=True)

else:
    # Hiển thị chi tiết (giữ nguyên logic biểu đồ cột của bạn)
    st.header("📝 Phân tích Chi tiết")
    # ... (Giữ nguyên phần code px.bar và table của bạn ở đây)
    st.dataframe(filtered_df)
