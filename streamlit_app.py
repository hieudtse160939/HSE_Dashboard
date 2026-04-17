import streamlit as st
import pandas as pd
import plotly.express as px
from io import BytesIO

# --- 1. CẤU HÌNH ---
st.set_page_config(page_title="HSE Master Dashboard", layout="wide")

def process_data(df, df_gv=None):
    # Chuẩn hóa tên cột
    df.columns = [str(c).strip() for c in df.columns]
    
    # Chỉ lấy các cột cần thiết, bỏ qua '% Phản hồi Chung'
    req = ['Lớp', 'Môn', 'Tong_Luot_Giao_Bai', 'Tong_Hoan_Thanh']
    df = df[req].copy()
    
    df['Tong_Luot_Giao_Bai'] = pd.to_numeric(df['Tong_Luot_Giao_Bai'], errors='coerce').fillna(0)
    df['Tong_Hoan_Thanh'] = pd.to_numeric(df['Tong_Hoan_Thanh'], errors='coerce').fillna(0)
    
    df['Lớp'] = df['Lớp'].astype(str).str.strip().str.upper()
    df['Môn'] = df['Môn'].astype(str).str.strip()
    
    teacher_main_subject = {} 
    
    if df_gv is not None:
        df_gv.columns = [str(c).strip() for c in df_gv.columns]
        gv_col = next((col for col in df_gv.columns if 'giáo viên' in col.lower() or 'gv' in col.lower()), 'Giáo Viên')
        
        if 'Lớp' in df_gv.columns and 'Môn' in df_gv.columns and gv_col in df_gv.columns:
            df_gv = df_gv.rename(columns={gv_col: 'Giáo Viên'})
            df_gv['Lớp'] = df_gv['Lớp'].astype(str).str.strip().str.upper()
            df_gv['Môn'] = df_gv['Môn'].astype(str).str.strip()
            df_gv['Giáo Viên'] = df_gv['Giáo Viên'].astype(str).str.strip()
            
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
        
    def rename_subject(row):
        mon = str(row['Môn'])
        gv = row['Giáo Viên']
        if "trải nghiệm" in mon.lower() or "hđtn" in mon.lower():
            return teacher_main_subject.get(gv, mon)
        return mon
        
    df['Môn'] = df.apply(rename_subject, axis=1)

    # Gộp dữ liệu sau khi đổi tên môn
    df = df.groupby(['Lớp', 'Môn', 'Giáo Viên'], as_index=False).agg({
        'Tong_Luot_Giao_Bai': 'sum',
        'Tong_Hoan_Thanh': 'sum'
    })
    
    df['Ty_le'] = (df['Tong_Hoan_Thanh'] / df['Tong_Luot_Giao_Bai'] * 100).round(1).fillna(0)
    return df

# --- 2. LOAD DATA ---
st.title("🛡️ Hệ thống Quản lý & Phân tích HSE")
st.sidebar.header("📂 Tải Dữ Liệu")

uploaded_file = st.sidebar.file_uploader("Tải lên Sheet 3 - Tổng hợp Lớp Môn (Excel/CSV)", type=["xlsx", "csv"])

# (Giả định URL dữ liệu giáo viên của bạn)
GV_DATA_URL = "https://raw.githubusercontent.com/hieudtse160939/HSE_Dashboard/a521cfd39d4b59e0e7af63db9e140f61c9e84a56/BM1.xlsx"

@st.cache_data
def load_gv_data():
    try: return pd.read_excel(GV_DATA_URL)
    except: return None

df_gv = load_gv_data()

if uploaded_file:
    file_ext = uploaded_file.name.split('.')[-1]
    raw_df = pd.read_excel(uploaded_file) if file_ext == 'xlsx' else pd.read_csv(uploaded_file)
    df = process_data(raw_df, df_gv)
else:
    st.info("👈 Vui lòng tải file dữ liệu ở thanh bên trái.")
    st.stop()

# --- 3. BỘ LỌC ---
st.sidebar.divider()
list_classes = ["Tất cả"] + sorted(df['Lớp'].unique().tolist())
selected_class = st.sidebar.selectbox("Lọc theo Lớp:", list_classes)

filtered_df = df.copy()
if selected_class != "Tất cả":
    filtered_df = filtered_df[filtered_df['Lớp'] == selected_class]

# --- 4. HIỂN THỊ PHÂN TÍCH ---
tab_lop, tab_gv, tab_mon = st.tabs(["📊 Theo Lớp", "👩‍🏫 Theo Giáo Viên", "🍕 Theo Môn Học"])

with tab_lop:
    st.subheader("Hiệu suất theo Lớp")
    class_stats = filtered_df.groupby('Lớp').agg({'Tong_Luot_Giao_Bai': 'sum', 'Tong_Hoan_Thanh': 'sum'}).reset_index()
    class_stats['Ty_le'] = (class_stats['Tong_Hoan_Thanh'] / class_stats['Tong_Luot_Giao_Bai'] * 100).round(1)
    st.dataframe(class_stats.sort_values('Ty_le', ascending=False), use_container_width=True)

with tab_gv:
    st.subheader("Hiệu suất theo Giáo viên")
    gv_stats = filtered_df.groupby('Giáo Viên').agg({'Tong_Luot_Giao_Bai': 'sum', 'Tong_Hoan_Thanh': 'sum'}).reset_index()
    gv_stats['Ty_le'] = (gv_stats['Tong_Hoan_Thanh'] / gv_stats['Tong_Luot_Giao_Bai'] * 100).round(1)
    st.dataframe(gv_stats.sort_values('Ty_le', ascending=False), use_container_width=True)

with tab_mon:
    st.subheader("Thống kê chi tiết theo Môn học")
    
    # 1. Thống kê bảng
    subject_stats = filtered_df.groupby('Môn').agg({
        'Tong_Luot_Giao_Bai': 'sum',
        'Tong_Hoan_Thanh': 'sum'
    }).reset_index()
    subject_stats['Ty_le_Hoan_Thanh'] = (subject_stats['Tong_Hoan_Thanh'] / subject_stats['Tong_Luot_Giao_Bai'] * 100).round(1)
    
    col_table, col_pie = st.columns([1, 1])
    
    with col_table:
        st.write("**Bảng tổng hợp tỷ lệ %**")
        st.dataframe(subject_stats.sort_values('Ty_le_Hoan_Thanh', ascending=False), hide_index=True)

    with col_pie:
        st.write("**Tỷ trọng Hoàn thành giữa các môn**")
        fig_pie = px.pie(
            subject_stats, 
            values='Tong_Hoan_Thanh', 
            names='Môn',
            hole=0.4,
            title="Phân bổ SL Hoàn thành theo Môn",
            color_discrete_sequence=px.colors.qualitative.Pastel
        )
        fig_pie.update_traces(textposition='inside', textinfo='percent+label')
        st.plotly_chart(fig_pie, use_container_width=True)

    # Biểu đồ cột thể hiện tỷ lệ % để bổ trợ
    st.divider()
    st.write("**Biểu đồ Tỷ lệ % Hoàn thành theo Môn**")
    fig_bar = px.bar(
        subject_stats, x='Môn', y='Ty_le_Hoan_Thanh', 
        text='Ty_le_Hoan_Thanh', color='Ty_le_Hoan_Thanh',
        color_continuous_scale='RdYlGn'
    )
    st.plotly_chart(fig_bar, use_container_width=True)
