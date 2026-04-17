import streamlit as st
import pandas as pd
import plotly.express as px
from io import BytesIO

# --- 1. CẤU HÌNH ---
st.set_page_config(page_title="HSE Master Dashboard", layout="wide")

def process_data(df, df_gv=None):
    # Chuẩn hóa tên cột file HSE
    df.columns = [str(c).strip() for c in df.columns]
    req = ['Lớp', 'Môn', 'Tong_Luot_Giao_Bai', 'Tong_Hoan_Thanh']
    
    if not all(c in df.columns for c in req):
        st.error(f"File HSE thiếu cột. Cần có: {req}")
        st.stop()
        
    df['Tong_Luot_Giao_Bai'] = pd.to_numeric(df['Tong_Luot_Giao_Bai'], errors='coerce').fillna(0)
    df['Tong_Hoan_Thanh'] = pd.to_numeric(df['Tong_Hoan_Thanh'], errors='coerce').fillna(0)
    
    # CHUẨN HÓA DỮ LIỆU ĐỂ MERGE KHÔNG BỊ LỖI
    df['Lớp'] = df['Lớp'].astype(str).str.strip().str.upper()
    df['Môn'] = df['Môn'].astype(str).str.strip()
    
    teacher_main_subject = {} # Từ điển lưu môn chính của từng Giáo viên
    
    # Xử lý file GVBM và Merge
    if df_gv is not None:
        df_gv.columns = [str(c).strip() for c in df_gv.columns]
        gv_col = next((col for col in df_gv.columns if 'giáo viên' in col.lower() or 'gv' in col.lower()), 'Giáo Viên')
        
        if 'Lớp' in df_gv.columns and 'Môn' in df_gv.columns and gv_col in df_gv.columns:
            df_gv = df_gv.rename(columns={gv_col: 'Giáo Viên'})
            
            # Chuẩn hóa dữ liệu GVBM
            df_gv['Lớp'] = df_gv['Lớp'].astype(str).str.strip().str.upper()
            df_gv['Môn'] = df_gv['Môn'].astype(str).str.strip()
            df_gv['Giáo Viên'] = df_gv['Giáo Viên'].astype(str).str.strip()
            
            # --- TÌM MÔN CHÍNH CỦA TỪNG GIÁO VIÊN TỪ TOÀN BỘ FILE GVBM ---
            for gv, group in df_gv.groupby('Giáo Viên'):
                if pd.isna(gv) or gv == "nan" or gv == "": continue
                subjects = group['Môn'].dropna().unique()
                
                # Môn chính là môn KHÔNG chứa các từ khóa trải nghiệm
                main_subs = [s for s in subjects if "trải nghiệm" not in str(s).lower() and "hđtn" not in str(s).lower()]
                if main_subs:
                    teacher_main_subject[gv] = main_subs[0] # Gán môn chuyên môn làm môn chính
            # --------------------------------------------------------------
            
            # Loại bỏ các dòng trùng lặp trong GVBM trước khi merge để tránh x2 dữ liệu
            df_gv_unique = df_gv[['Lớp', 'Môn', 'Giáo Viên']].drop_duplicates()
            df = pd.merge(df, df_gv_unique, on=['Lớp', 'Môn'], how='left')
        else:
            st.warning("Dữ liệu Giáo viên từ GitHub thiếu cột. Cần có: 'Lớp', 'Môn', và 'Giáo Viên'")
            
    # Xử lý trường hợp không có tên giáo viên
    if 'Giáo Viên' not in df.columns:
        df['Giáo Viên'] = "Chưa cập nhật"
    else:
        df['Giáo Viên'] = df['Giáo Viên'].fillna("Chưa cập nhật")
        
    # --- LOGIC ĐỔI TÊN MÔN TRẢI NGHIỆM THÀNH MÔN CHÍNH ---
    def rename_subject(row):
        mon = str(row['Môn'])
        mon_lower = mon.lower()
        gv = row['Giáo Viên']
        
        # Nếu môn hiện tại là Trải nghiệm hướng nghiệp
        if "trải nghiệm" in mon_lower or "hđtn" in mon_lower:
            # Lấy tên môn chính của GV đó, nếu không tìm thấy thì đành giữ nguyên
            return teacher_main_subject.get(gv, mon)
        return mon
        
    df['Môn'] = df.apply(rename_subject, axis=1)

    # SAU KHI ĐỔI TÊN: Tiến hành gộp dòng (Trải nghiệm + Môn chính) thành 1 dòng duy nhất
    df = df.groupby(['Lớp', 'Môn', 'Giáo Viên'], as_index=False).agg({
        'Tong_Luot_Giao_Bai': 'sum',
        'Tong_Hoan_Thanh': 'sum'
    })
    
    # Tính lại tỷ lệ phần trăm chung sau khi gộp
    df['Ty_le'] = (df['Tong_Hoan_Thanh'] / df['Tong_Luot_Giao_Bai'] * 100).round(1).fillna(0)
    
    return df

def to_excel_with_style(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Bao_Cao_Chi_Tiet')
        workbook  = writer.book
        worksheet = writer.sheets['Bao_Cao_Chi_Tiet']

        format_red = workbook.add_format({'bg_color': '#FFC7CE', 'font_color': '#9C0006'})
        format_yellow = workbook.add_format({'bg_color': '#FFEB9C', 'font_color': '#9C6500'})
        format_green = workbook.add_format({'bg_color': '#C6EFCE', 'font_color': '#006100'})

        if 'Ty_le' in df.columns:
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

st.sidebar.header("📂 Tải Dữ Liệu")

# 1. Đọc file HSE chính (Do user upload)
uploaded_file = st.sidebar.file_uploader("Tải lên Báo cáo HSE (Excel)", type=["xlsx"])

# 2. Tự động đọc dữ liệu Giáo viên từ link GitHub của bạn (Chạy ngầm, không cần thao tác)
GV_DATA_URL = "https://raw.githubusercontent.com/hieudtse160939/HSE_Dashboard/a521cfd39d4b59e0e7af63db9e140f61c9e84a56/BM1.xlsx"

@st.cache_data(show_spinner=False)
def load_gv_data():
    try:
        return pd.read_excel(GV_DATA_URL)
    except Exception as e:
        return None

df_gv = load_gv_data()
if df_gv is not None:
    st.sidebar.success("✅ Đã đồng bộ dữ liệu Giáo viên từ GitHub!")
else:
    st.sidebar.error("❌ Không thể lấy dữ liệu Giáo viên từ GitHub. Kiểm tra lại đường link.")

# Xử lý gộp dữ liệu
if uploaded_file:
    with st.spinner('Đang xử lý dữ liệu...'):
        df = process_data(pd.read_excel(uploaded_file), df_gv)
else:
    st.info("👈 Vui lòng tải dữ liệu Báo cáo HSE ở thanh bên trái để bắt đầu.")
    st.stop()

# --- 3. BỘ LỌC & NÚT TẢI ---
st.sidebar.divider()
st.sidebar.header("🎯 Phạm vi báo cáo")

list_classes = ["Tất cả các lớp"] + sorted(df['Lớp'].dropna().unique().tolist())
selected_class = st.sidebar.selectbox("Lọc theo Lớp:", list_classes)

list_teachers = ["Tất cả Giáo viên"] + sorted(df['Giáo Viên'].dropna().unique().tolist())
selected_teacher = st.sidebar.selectbox("Lọc theo Giáo Viên:", list_teachers)

filtered_df = df.copy()
if selected_class != "Tất cả các lớp":
    filtered_df = filtered_df[filtered_df['Lớp'] == selected_class]
if selected_teacher != "Tất cả Giáo viên":
    filtered_df = filtered_df[filtered_df['Giáo Viên'] == selected_teacher]

st.sidebar.divider()
st.sidebar.subheader("📤 Xuất dữ liệu")
excel_data = to_excel_with_style(filtered_df)
st.sidebar.download_button(
    label="📥 Tải Báo cáo Excel đã lọc",
    data=excel_data,
    file_name="Bao_Cao_HSE_Da_Loc.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)

# --- 4. HIỂN THỊ PHÂN TÍCH ---
if selected_class == "Tất cả các lớp" and selected_teacher == "Tất cả Giáo viên":
    st.header("🌍 Phân tích Tổng thể Toàn trường")
    
    tab_lop, tab_gv = st.tabs(["📊 Tổng hợp theo Lớp", "👩‍🏫 Tổng hợp theo Giáo Viên"])
    
    with tab_lop:
        class_rank = df.groupby('Lớp').agg({'Tong_Luot_Giao_Bai': 'sum', 'Tong_Hoan_Thanh': 'sum'}).reset_index()
        class_rank['Ty_le_TB'] = (class_rank['Tong_Hoan_Thanh'] / class_rank['Tong_Luot_Giao_Bai'] * 100).round(1)
        class_rank = class_rank.sort_values('Ty_le_TB', ascending=False)

        c1, c2, c3 = st.columns(3)
        c1.metric("Hiệu suất Trung bình", f"{class_rank['Ty_le_TB'].mean():.1f}%")
        if not class_rank.empty:
            c2.metric("Lớp dẫn đầu", f"{class_rank.iloc[0]['Lớp']} ({class_rank.iloc[0]['Ty_le_TB']}%)")
            c3.metric("Lớp thấp nhất", f"{class_rank.iloc[-1]['Lớp']} ({class_rank.iloc[-1]['Ty_le_TB']}%)")

        st.divider()
        st.subheader("🌡️ Bản đồ nhiệt (Heatmap) Toàn trường")
        heatmap_data = df.pivot_table(index='Lớp', columns='Môn', values='Ty_le').fillna(0)
        fig_heat = px.imshow(heatmap_data, text_auto=True, color_continuous_scale='RdYlGn', aspect="auto")
        st.plotly_chart(fig_heat, use_container_width=True)
        
    with tab_gv:
        st.subheader("Bảng Xếp hạng Giáo viên")
        teacher_rank = df.groupby('Giáo Viên').agg({
            'Lớp': 'count', 
            'Tong_Luot_Giao_Bai': 'sum', 
            'Tong_Hoan_Thanh': 'sum'
        }).reset_index()
        teacher_rank.rename(columns={'Lớp': 'Số Lớp Giảng Dạy'}, inplace=True)
        teacher_rank['Ty_le_TB'] = (teacher_rank['Tong_Hoan_Thanh'] / teacher_rank['Tong_Luot_Giao_Bai'] * 100).round(1)
        teacher_rank = teacher_rank.sort_values('Ty_le_TB', ascending=False)
        st.dataframe(teacher_rank, use_container_width=True, hide_index=True)

else:
    st.header("📝 Phân tích Chi tiết")
    
    col_i1, col_i2 = st.columns([1, 2])
    with col_i1:
        st.subheader("💡 Nhận xét")
        if filtered_df.empty:
            st.warning("Không có dữ liệu phù hợp với bộ lọc hiện tại.")
        else:
            avg_class = filtered_df['Ty_le'].mean()
            st.write(f"Hiệu suất trung bình đạt **{avg_class:.1f}%**.")
            
            best = filtered_df.loc[filtered_df['Ty_le'].idxmax()]
            st.success(f"🌟 Tốt nhất: {best['Môn']} ({best['Giáo Viên']}) - {best['Ty_le']}%")
            
            danger = filtered_df[filtered_df['Ty_le'] < 50]
            if not danger.empty:
                danger_list = danger.apply(lambda row: f"{row['Môn']} ({row['Giáo Viên']})", axis=1).tolist()
                st.error(f"❗ Cần chú ý (Dưới 50%): {', '.join(danger_list)}")
    
    with col_i2:
        if not filtered_df.empty:
            filtered_df['Label'] = filtered_df['Môn'] + "<br>(" + filtered_df['Giáo Viên'] + ")"
            fig = px.bar(
                filtered_df, x='Label', y='Ty_le', text='Ty_le', 
                color='Ty_le', color_continuous_scale='RdYlGn',
                labels={'Label': 'Môn & Giáo viên', 'Ty_le': 'Tỷ lệ Hoàn thành (%)'}
            )
            fig.update_layout(xaxis_title="", yaxis_title="Tỷ lệ (%)")
            st.plotly_chart(fig, use_container_width=True)

    if not filtered_df.empty:
        st.subheader("Bảng Dữ liệu Thô")
        st.dataframe(filtered_df[['Lớp', 'Môn', 'Giáo Viên', 'Tong_Luot_Giao_Bai', 'Tong_Hoan_Thanh', 'Ty_le']], hide_index=True, use_container_width=True)
