import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from io import BytesIO

# ─────────────────────────────────────────────
# 1. CẤU HÌNH TRANG & CUSTOM CSS
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="HSE Dashboard",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
/* ── Google Font ── */
@import url('https://fonts.googleapis.com/css2?family=Be+Vietnam+Pro:wght@300;400;500;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Be Vietnam Pro', sans-serif;
}

/* ── Ẩn decoration mặc định ── */
#MainMenu, footer, header { visibility: hidden; }

/* ── Nút toggle sidebar tùy chỉnh ── */
#sidebar-toggle-btn {
    position: fixed;
    top: 14px;
    left: 14px;
    z-index: 99999;
    width: 38px;
    height: 38px;
    background: #1A2E5A;
    border: 1px solid #2a4a8a;
    border-radius: 8px;
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    box-shadow: 0 2px 8px rgba(0,0,0,0.25);
    transition: background 0.2s, transform 0.15s;
}
#sidebar-toggle-btn:hover {
    background: #C8102E;
    transform: scale(1.07);
}
#sidebar-toggle-btn svg {
    width: 18px; height: 18px;
    stroke: #f1f5f9; fill: none;
    stroke-width: 2; stroke-linecap: round; stroke-linejoin: round;
}

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: #1A2E5A;
    border-right: 1px solid #142247;
}
[data-testid="stSidebar"] * {
    color: #cbd5e1 !important;
}
[data-testid="stSidebar"] .stSelectbox label,
[data-testid="stSidebar"] .stFileUploader label {
    color: #94a3b8 !important;
    font-size: 0.78rem !important;
    font-weight: 600 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.08em !important;
}
[data-testid="stSidebar"] [data-baseweb="select"] > div {
    background: #142247 !important;
    border: 1px solid #2a4a8a !important;
    border-radius: 8px !important;
    color: #f1f5f9 !important;
}
[data-testid="stSidebar"] .stDownloadButton button {
    background: #C8102E !important;
    color: white !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
    width: 100% !important;
    padding: 0.6rem 1rem !important;
    transition: background 0.2s;
}
[data-testid="stSidebar"] .stDownloadButton button:hover {
    background: #a00d24 !important;
}

/* ── Main area ── */
.main .block-container {
    padding: 2rem 2.5rem 3rem;
    max-width: 1400px;
}

/* ── Page title ── */
.page-title {
    font-size: 1.6rem;
    font-weight: 700;
    color: #1A2E5A;
    margin-bottom: 0.15rem;
}
.page-subtitle {
    font-size: 0.88rem;
    color: #64748b;
    margin-bottom: 1.8rem;
}

/* ── Metric cards ── */
.metric-card {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 14px;
    padding: 1.2rem 1.4rem;
    position: relative;
    overflow: hidden;
    box-shadow: 0 1px 3px rgba(0,0,0,0.06);
    transition: box-shadow 0.2s;
}
.metric-card:hover { box-shadow: 0 4px 12px rgba(0,0,0,0.1); }
.metric-card .accent {
    position: absolute;
    top: 0; left: 0;
    width: 4px; height: 100%;
    border-radius: 14px 0 0 14px;
}
.metric-card .label {
    font-size: 0.72rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: #94a3b8;
    margin-bottom: 0.35rem;
}
.metric-card .value {
    font-size: 1.75rem;
    font-weight: 700;
    color: #1A2E5A;
    line-height: 1.1;
}
.metric-card .sub {
    font-size: 0.78rem;
    color: #64748b;
    margin-top: 0.3rem;
}

/* ── Section header ── */
.section-title {
    font-size: 1rem;
    font-weight: 700;
    color: #1A2E5A;
    margin: 1.6rem 0 0.8rem;
    display: flex;
    align-items: center;
    gap: 0.5rem;
}
.section-title::after {
    content: '';
    flex: 1;
    height: 1px;
    background: #e2e8f0;
    margin-left: 0.5rem;
}

/* ── Alert boxes ── */
.alert-success {
    background: #f0fdf4;
    border: 1px solid #bbf7d0;
    border-left: 4px solid #22c55e;
    border-radius: 8px;
    padding: 0.8rem 1rem;
    color: #166534;
    font-size: 0.88rem;
    margin-bottom: 0.6rem;
}
.alert-danger {
    background: #fff1f2;
    border: 1px solid #fecdd3;
    border-left: 4px solid #f43f5e;
    border-radius: 8px;
    padding: 0.8rem 1rem;
    color: #9f1239;
    font-size: 0.88rem;
    margin-bottom: 0.6rem;
}
.alert-info {
    background: #eef2ff;
    border: 1px solid #c7d2fe;
    border-left: 4px solid #1A2E5A;
    border-radius: 8px;
    padding: 0.8rem 1rem;
    color: #1A2E5A;
    font-size: 0.88rem;
    margin-bottom: 0.6rem;
}

/* ── Tabs ── */
[data-baseweb="tab-list"] {
    background: #f8fafc !important;
    border-radius: 10px !important;
    padding: 4px !important;
    border: 1px solid #e2e8f0 !important;
    gap: 4px !important;
}
[data-baseweb="tab"] {
    border-radius: 7px !important;
    font-weight: 600 !important;
    font-size: 0.84rem !important;
    color: #64748b !important;
}
[aria-selected="true"][data-baseweb="tab"] {
    background: #ffffff !important;
    color: #0f172a !important;
    box-shadow: 0 1px 3px rgba(0,0,0,0.1) !important;
}

/* ── Dataframe ── */
[data-testid="stDataFrame"] {
    border-radius: 10px !important;
    overflow: hidden !important;
    border: 1px solid #e2e8f0 !important;
}

/* ── Divider ── */
hr { border: none; border-top: 1px solid #e2e8f0; margin: 1.2rem 0; }

/* ── Spinner ── */
.stSpinner > div { border-top-color: #3b82f6 !important; }

/* ── Upload area ── */
[data-testid="stFileUploaderDropzone"] {
    background: #142247 !important;
    border: 1px dashed #334155 !important;
    border-radius: 10px !important;
}
</style>
""", unsafe_allow_html=True)


# ── Inject nút toggle sidebar bằng JavaScript ──
st.markdown("""
<div id="sidebar-toggle-btn" title="Mở/đóng menu" onclick="toggleSidebar()">
    <svg viewBox="0 0 24 24">
        <line x1="3" y1="6" x2="21" y2="6"/>
        <line x1="3" y1="12" x2="21" y2="12"/>
        <line x1="3" y1="18" x2="21" y2="18"/>
    </svg>
</div>
<script>
function toggleSidebar() {
    const candidates = [
        '[data-testid="collapsedControl"] button',
        'button[aria-label="Close sidebar"]',
        'button[aria-label="Open sidebar"]',
        '[data-testid="stSidebarNav"] + div button',
    ];
    for (const sel of candidates) {
        const btn = window.parent.document.querySelector(sel);
        if (btn) { btn.click(); return; }
    }
    // Hard fallback: toggle sidebar visibility
    const sidebar = window.parent.document.querySelector('[data-testid="stSidebar"]');
    if (sidebar) {
        const isCollapsed = sidebar.offsetWidth < 10;
        sidebar.style.marginLeft = isCollapsed ? '0' : '-400px';
    }
}
</script>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# 2. MÀU SẮC PLOTLY NHẤT QUÁN
# ─────────────────────────────────────────────
PLOT_TEMPLATE = "plotly_white"
COLOR_SCALE   = [[0, "#C8102E"], [0.5, "#F5A623"], [1, "#1A7A3F"]]
ACCENT_MAIN   = "#C8102E"   # Đỏ Hoa Sen
ACCENT_NAVY   = "#1A2E5A"   # Xanh navy Hoa Sen
ACCENT_GOLD   = "#F5A623"   # Vàng Hoa Sen

def themed_fig(fig):
    fig.update_layout(
        template=PLOT_TEMPLATE,
        font_family="Be Vietnam Pro",
        font_color="#1e293b",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(t=40, b=20, l=10, r=10),
    )
    fig.update_xaxes(showgrid=False, linecolor="#e2e8f0", tickfont_size=11)
    fig.update_yaxes(gridcolor="#f1f5f9", linecolor="#e2e8f0", tickfont_size=11)
    return fig

# ─────────────────────────────────────────────
# 3. XỬ LÝ DỮ LIỆU
# ─────────────────────────────────────────────
def process_data(df, df_gv=None):
    df.columns = [str(c).strip() for c in df.columns]
    req = ['Lớp', 'Môn', 'Tong_Luot_Giao_Bai', 'Tong_Hoan_Thanh']
    if not all(c in df.columns for c in req):
        st.error(f"File HSE thiếu cột. Cần có: {req}")
        st.stop()

    df['Tong_Luot_Giao_Bai'] = pd.to_numeric(df['Tong_Luot_Giao_Bai'], errors='coerce').fillna(0)
    df['Tong_Hoan_Thanh']    = pd.to_numeric(df['Tong_Hoan_Thanh'],    errors='coerce').fillna(0)
    df['Lớp'] = df['Lớp'].astype(str).str.strip().str.upper()
    df['Môn'] = df['Môn'].astype(str).str.strip()

    teacher_main_subject = {}

    if df_gv is not None:
        df_gv.columns = [str(c).strip() for c in df_gv.columns]
        gv_col = next((col for col in df_gv.columns
                       if 'giáo viên' in col.lower() or 'gv' in col.lower()), 'Giáo Viên')

        if all(c in df_gv.columns for c in ['Lớp', 'Môn', gv_col]):
            df_gv = df_gv.rename(columns={gv_col: 'Giáo Viên'})
            df_gv['Lớp']      = df_gv['Lớp'].astype(str).str.strip().str.upper()
            df_gv['Môn']      = df_gv['Môn'].astype(str).str.strip()
            df_gv['Giáo Viên'] = df_gv['Giáo Viên'].astype(str).str.strip()

            for gv, grp in df_gv.groupby('Giáo Viên'):
                if pd.isna(gv) or gv in ("nan", ""): continue
                main_subs = [s for s in grp['Môn'].dropna().unique()
                             if "trải nghiệm" not in str(s).lower()
                             and "hđtn" not in str(s).lower()]
                if main_subs:
                    teacher_main_subject[gv] = main_subs[0]

            df = pd.merge(df,
                          df_gv[['Lớp', 'Môn', 'Giáo Viên']].drop_duplicates(),
                          on=['Lớp', 'Môn'], how='left')
        else:
            st.warning("Dữ liệu Giáo viên thiếu cột: 'Lớp', 'Môn', 'Giáo Viên'.")

    if 'Giáo Viên' not in df.columns:
        df['Giáo Viên'] = "Chưa cập nhật"
    else:
        df['Giáo Viên'] = df['Giáo Viên'].fillna("Chưa cập nhật")

    def rename_subject(row):
        mon = str(row['Môn'])
        if "trải nghiệm" in mon.lower() or "hđtn" in mon.lower():
            return teacher_main_subject.get(row['Giáo Viên'], mon)
        return mon

    df['Môn'] = df.apply(rename_subject, axis=1)
    df = df.groupby(['Lớp', 'Môn', 'Giáo Viên'], as_index=False).agg(
        Tong_Luot_Giao_Bai=('Tong_Luot_Giao_Bai', 'sum'),
        Tong_Hoan_Thanh=('Tong_Hoan_Thanh', 'sum')
    )
    df['Ty_le'] = (df['Tong_Hoan_Thanh'] / df['Tong_Luot_Giao_Bai'] * 100).round(1).fillna(0)
    return df

def to_excel_with_style(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Bao_Cao_Chi_Tiet')
        wb  = writer.book
        ws  = writer.sheets['Bao_Cao_Chi_Tiet']
        fmt_red    = wb.add_format({'bg_color': '#FFC7CE', 'font_color': '#9C0006'})
        fmt_yellow = wb.add_format({'bg_color': '#FFEB9C', 'font_color': '#9C6500'})
        fmt_green  = wb.add_format({'bg_color': '#C6EFCE', 'font_color': '#006100'})
        if 'Ty_le' in df.columns:
            ci = df.columns.get_loc('Ty_le')
            n  = len(df)
            ws.conditional_format(1, ci, n, ci, {'type': 'cell', 'criteria': '<',       'value': 50,  'format': fmt_red})
            ws.conditional_format(1, ci, n, ci, {'type': 'cell', 'criteria': 'between', 'minimum': 50, 'maximum': 80, 'format': fmt_yellow})
            ws.conditional_format(1, ci, n, ci, {'type': 'cell', 'criteria': '>',       'value': 80,  'format': fmt_green})
    return output.getvalue()

# ─────────────────────────────────────────────
# 4. SIDEBAR
# ─────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style="padding:1.2rem 0 1rem;">
        <div style="font-size:1rem;font-weight:700;color:#ffffff;letter-spacing:-0.01em;line-height:1.3;">
            TRƯỜNG TH–THCS–THPT
        </div>
        <div style="font-size:1.5rem;font-weight:800;color:#C8102E;letter-spacing:0.04em;">
            HOA SEN
        </div>
        <div style="font-size:0.65rem;color:#93acd4;margin-top:0.1rem;letter-spacing:0.04em;">
            HỆ THỐNG GIÁO DỤC HỘI NHẬP QUỐC TẾ
        </div>
        <div style="height:2px;background:linear-gradient(90deg,#C8102E,#F5A623,transparent);
                    border-radius:2px;margin-top:0.7rem;"></div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<p style="font-size:0.72rem;font-weight:600;text-transform:uppercase;letter-spacing:0.08em;color:#475569;margin-bottom:0.4rem;">Báo cáo HSE</p>', unsafe_allow_html=True)
    uploaded_file = st.file_uploader("", type=["xlsx"], label_visibility="collapsed")

    GV_DATA_URL = "https://raw.githubusercontent.com/hieudtse160939/HSE_Dashboard/a521cfd39d4b59e0e7af63db9e140f61c9e84a56/BM1.xlsx"

    @st.cache_data(show_spinner=False)
    def load_gv_data():
        try:
            return pd.read_excel(GV_DATA_URL)
        except:
            return None

    df_gv = load_gv_data()
    if df_gv is not None:
        st.markdown('<div class="alert-success">✅ Đã đồng bộ dữ liệu giáo viên</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="alert-danger">❌ Không thể kết nối GitHub</div>', unsafe_allow_html=True)

# ─────────────────────────────────────────────
# 5. LOAD & XỬ LÝ DATA
# ─────────────────────────────────────────────
if not uploaded_file:
    st.markdown("""
    <div style="display:flex;flex-direction:column;align-items:center;justify-content:center;
                min-height:60vh;text-align:center;color:#94a3b8;">
        <div style="font-size:3.5rem;margin-bottom:1rem;">📂</div>
        <div style="font-size:1.2rem;font-weight:600;color:#475569;margin-bottom:0.5rem;">
            Chưa có dữ liệu
        </div>
        <div style="font-size:0.9rem;">
            Tải lên file Báo cáo HSE (.xlsx) ở thanh bên trái để bắt đầu
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

with st.spinner("Đang xử lý dữ liệu…"):
    df = process_data(pd.read_excel(uploaded_file), df_gv)

# ─────────────────────────────────────────────
# 6. BỘ LỌC
# ─────────────────────────────────────────────
with st.sidebar:
    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown('<p style="font-size:0.72rem;font-weight:600;text-transform:uppercase;letter-spacing:0.08em;color:#475569;margin-bottom:0.4rem;">Bộ lọc</p>', unsafe_allow_html=True)

    list_classes  = ["Tất cả các lớp"]  + sorted(df['Lớp'].dropna().unique().tolist())
    list_teachers = ["Tất cả Giáo viên"] + sorted(df['Giáo Viên'].dropna().unique().tolist())

    selected_class   = st.selectbox("Lớp", list_classes)
    selected_teacher = st.selectbox("Giáo viên", list_teachers)

    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown('<p style="font-size:0.72rem;font-weight:600;text-transform:uppercase;letter-spacing:0.08em;color:#475569;margin-bottom:0.4rem;">Xuất báo cáo</p>', unsafe_allow_html=True)

filtered_df = df.copy()
if selected_class   != "Tất cả các lớp":   filtered_df = filtered_df[filtered_df['Lớp']       == selected_class]
if selected_teacher != "Tất cả Giáo viên": filtered_df = filtered_df[filtered_df['Giáo Viên'] == selected_teacher]

with st.sidebar:
    excel_data = to_excel_with_style(filtered_df)
    st.download_button(
        label="📥 Tải xuống Excel",
        data=excel_data,
        file_name="Bao_Cao_HSE_Da_Loc.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )

# ─────────────────────────────────────────────
# 7. NỘI DUNG CHÍNH
# ─────────────────────────────────────────────

is_overview = (selected_class == "Tất cả các lớp" and selected_teacher == "Tất cả Giáo viên")

if is_overview:
    st.markdown('<div class="page-title">🌍 Tổng quan Toàn trường</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-subtitle">Hiệu suất hoàn thành bài tập theo lớp và giáo viên</div>', unsafe_allow_html=True)

    # ── Metric cards ──
    class_rank = df.groupby('Lớp').agg(
        Tong_Luot_Giao_Bai=('Tong_Luot_Giao_Bai', 'sum'),
        Tong_Hoan_Thanh=('Tong_Hoan_Thanh', 'sum')
    ).reset_index()
    class_rank['Ty_le_TB'] = (class_rank['Tong_Hoan_Thanh'] / class_rank['Tong_Luot_Giao_Bai'] * 100).round(1)
    class_rank = class_rank.sort_values('Ty_le_TB', ascending=False)

    avg  = class_rank['Ty_le_TB'].mean()
    best = class_rank.iloc[0]  if not class_rank.empty else None
    worst= class_rank.iloc[-1] if not class_rank.empty else None

    c1, c2, c3, c4 = st.columns(4)
    cards = [
        (c1, "#3b82f6", "Hiệu suất TB",       f"{avg:.1f}%",   f"{len(class_rank)} lớp"),
        (c2, "#22c55e", "Lớp dẫn đầu",
         f"{best['Lớp']}" if best is not None else "—",
         f"{best['Ty_le_TB']}%" if best is not None else ""),
        (c3, "#f43f5e", "Lớp thấp nhất",
         f"{worst['Lớp']}" if worst is not None else "—",
         f"{worst['Ty_le_TB']}%" if worst is not None else ""),
        (c4, "#f59e0b", "Tổng lượt giao",
         f"{int(df['Tong_Luot_Giao_Bai'].sum()):,}",
         f"Hoàn thành: {int(df['Tong_Hoan_Thanh'].sum()):,}"),
    ]
    for col, color, label, value, sub in cards:
        with col:
            st.markdown(f"""
            <div class="metric-card">
                <div class="accent" style="background:{color};"></div>
                <div class="label">{label}</div>
                <div class="value">{value}</div>
                <div class="sub">{sub}</div>
            </div>
            """, unsafe_allow_html=True)

    # ── Tabs ──
    tab_lop, tab_gv = st.tabs(["  📊 Theo Lớp  ", "  👩‍🏫 Theo Giáo Viên  "])

    with tab_lop:
        st.markdown('<div class="section-title">Xếp hạng hiệu suất theo Lớp</div>', unsafe_allow_html=True)

        # Bar chart lớp
        fig_bar = px.bar(
            class_rank,
            x='Lớp', y='Ty_le_TB',
            text='Ty_le_TB',
            color='Ty_le_TB',
            color_continuous_scale=COLOR_SCALE,
            labels={'Ty_le_TB': 'Tỷ lệ (%)', 'Lớp': ''},
        )
        fig_bar.update_traces(texttemplate='%{text}%', textposition='outside', marker_line_width=0)
        fig_bar.update_coloraxes(showscale=False)
        st.plotly_chart(themed_fig(fig_bar), use_container_width=True)

        st.markdown('<div class="section-title">Bản đồ nhiệt — Lớp × Môn</div>', unsafe_allow_html=True)
        heatmap_data = df.pivot_table(index='Lớp', columns='Môn', values='Ty_le').fillna(0)
        fig_heat = px.imshow(
            heatmap_data,
            text_auto=".1f",
            color_continuous_scale=COLOR_SCALE,
            aspect="auto",
            labels=dict(color="Tỷ lệ (%)"),
        )
        fig_heat.update_layout(
            xaxis_title="", yaxis_title="",
            coloraxis_colorbar=dict(title="", ticksuffix="%"),
            font_family="Be Vietnam Pro",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(t=20, b=10, l=10, r=10),
        )
        st.plotly_chart(fig_heat, use_container_width=True)

    with tab_gv:
        teacher_rank = df.groupby('Giáo Viên').agg(
            So_Lop=('Lớp', 'count'),
            Tong_Luot_Giao_Bai=('Tong_Luot_Giao_Bai', 'sum'),
            Tong_Hoan_Thanh=('Tong_Hoan_Thanh', 'sum')
        ).reset_index()
        teacher_rank['Ty_le_TB'] = (
            teacher_rank['Tong_Hoan_Thanh'] / teacher_rank['Tong_Luot_Giao_Bai'] * 100
        ).round(1)
        teacher_rank = teacher_rank.sort_values('Ty_le_TB', ascending=False).reset_index(drop=True)
        teacher_rank.index += 1  # rank bắt đầu từ 1

        st.markdown('<div class="section-title">Bảng xếp hạng Giáo viên</div>', unsafe_allow_html=True)

        fig_gv = px.bar(
            teacher_rank,
            x='Giáo Viên', y='Ty_le_TB',
            text='Ty_le_TB',
            color='Ty_le_TB',
            color_continuous_scale=COLOR_SCALE,
            labels={'Ty_le_TB': 'Tỷ lệ (%)', 'Giáo Viên': ''},
        )
        fig_gv.update_traces(texttemplate='%{text}%', textposition='outside', marker_line_width=0)
        fig_gv.update_coloraxes(showscale=False)
        st.plotly_chart(themed_fig(fig_gv), use_container_width=True)

        teacher_rank_display = teacher_rank.rename(columns={
            'So_Lop': 'Số lớp',
            'Tong_Luot_Giao_Bai': 'Lượt giao',
            'Tong_Hoan_Thanh': 'Hoàn thành',
            'Ty_le_TB': 'Tỷ lệ (%)'
        })
        st.dataframe(teacher_rank_display, use_container_width=True)

# ─────────────────────────────────────────────
# CHI TIẾT
# ─────────────────────────────────────────────
else:
    title_parts = []
    if selected_class   != "Tất cả các lớp":   title_parts.append(f"Lớp {selected_class}")
    if selected_teacher != "Tất cả Giáo viên": title_parts.append(selected_teacher)

    st.markdown(f'<div class="page-title">📝 Chi tiết: {" · ".join(title_parts)}</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-subtitle">Phân tích hiệu suất hoàn thành theo môn học</div>', unsafe_allow_html=True)

    if filtered_df.empty:
        st.markdown('<div class="alert-info">ℹ️ Không có dữ liệu phù hợp với bộ lọc hiện tại.</div>', unsafe_allow_html=True)
        st.stop()

    # ── Metric cards ──
    avg_rate = filtered_df['Ty_le'].mean()
    best_row = filtered_df.loc[filtered_df['Ty_le'].idxmax()]
    danger   = filtered_df[filtered_df['Ty_le'] < 50]

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="accent" style="background:#C8102E;"></div>
            <div class="label">Hiệu suất trung bình</div>
            <div class="value">{avg_rate:.1f}%</div>
            <div class="sub">{len(filtered_df)} môn học</div>
        </div>""", unsafe_allow_html=True)
    with c2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="accent" style="background:#1A7A3F;"></div>
            <div class="label">Môn tốt nhất</div>
            <div class="value">{best_row['Ty_le']}%</div>
            <div class="sub">{best_row['Môn']}</div>
        </div>""", unsafe_allow_html=True)
    with c3:
        color = "#C8102E" if len(danger) > 0 else "#1A7A3F"
        val   = f"{len(danger)} môn" if len(danger) > 0 else "Không có"
        st.markdown(f"""
        <div class="metric-card">
            <div class="accent" style="background:{color};"></div>
            <div class="label">Cần chú ý (&lt; 50%)</div>
            <div class="value">{val}</div>
            <div class="sub">{"Dưới ngưỡng an toàn" if len(danger) > 0 else "Tất cả đạt ngưỡng"}</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("")

    # ── Alerts ──
    st.markdown(f'<div class="alert-success">🌟 <b>Tốt nhất:</b> {best_row["Môn"]} ({best_row["Giáo Viên"]}) — {best_row["Ty_le"]}%</div>', unsafe_allow_html=True)
    if not danger.empty:
        items = ", ".join(danger.apply(lambda r: f"{r['Môn']} ({r['Giáo Viên']})", axis=1))
        st.markdown(f'<div class="alert-danger">❗ <b>Cần chú ý (dưới 50%):</b> {items}</div>', unsafe_allow_html=True)

    # ── Bar chart ──
    st.markdown('<div class="section-title">Biểu đồ Hiệu suất theo Môn</div>', unsafe_allow_html=True)

    fdf = filtered_df.copy()
    fdf['Label'] = fdf['Môn'] + "<br><span style='font-size:10px'>" + fdf['Giáo Viên'] + "</span>"
    fig = px.bar(
        fdf.sort_values('Ty_le', ascending=False),
        x='Môn', y='Ty_le',
        text='Ty_le',
        color='Ty_le',
        color_continuous_scale=COLOR_SCALE,
        hover_data={'Giáo Viên': True, 'Tong_Luot_Giao_Bai': True, 'Tong_Hoan_Thanh': True},
        labels={'Ty_le': 'Tỷ lệ (%)', 'Môn': ''},
    )
    fig.update_traces(texttemplate='%{text}%', textposition='outside', marker_line_width=0)
    fig.update_coloraxes(showscale=False)
    fig.add_hline(y=80, line_dash="dot", line_color="#1A7A3F",
                  annotation_text="Mục tiêu 80%", annotation_position="bottom right",
                  annotation_font_color="#1A7A3F")
    fig.add_hline(y=50, line_dash="dot", line_color="#C8102E",
                  annotation_text="Ngưỡng 50%", annotation_position="bottom right",
                  annotation_font_color="#C8102E")
    st.plotly_chart(themed_fig(fig), use_container_width=True)

    # ── Bảng dữ liệu ──
    st.markdown('<div class="section-title">Dữ liệu chi tiết</div>', unsafe_allow_html=True)
    display_cols = ['Lớp', 'Môn', 'Giáo Viên', 'Tong_Luot_Giao_Bai', 'Tong_Hoan_Thanh', 'Ty_le']
    st.dataframe(
        filtered_df[display_cols].sort_values('Ty_le', ascending=False),
        hide_index=True,
        use_container_width=True,
        column_config={
            'Tong_Luot_Giao_Bai': st.column_config.NumberColumn('Lượt giao', format="%d"),
            'Tong_Hoan_Thanh':    st.column_config.NumberColumn('Hoàn thành', format="%d"),
            'Ty_le':              st.column_config.ProgressColumn('Tỷ lệ (%)', format="%.1f%%", min_value=0, max_value=100),
        }
    )
