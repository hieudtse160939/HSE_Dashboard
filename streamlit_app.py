import re
import unicodedata
from io import BytesIO
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio
import streamlit as st

# =============================================================================
# 1. CẤU HÌNH
# =============================================================================
st.set_page_config(page_title="HSE Dashboard", page_icon="📊", layout="wide")

APP_DIR = Path(__file__).parent
SAMPLE_FILE = APP_DIR / "BC_HSE.xlsx"

# Bảng màu (mực chữ, lưới, trạng thái, thang tuần tự một màu xanh)
INK, INK2, MUTED, GRID, AXIS = "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7"
BLUE = "#2a78d6"
GOOD, WARN, CRIT = "#0ca30c", "#fab219", "#d03b3b"
SEQ_BLUE = [[0, "#cde2fb"], [0.25, "#86b6ef"], [0.5, "#3987e5"], [0.75, "#1c5cab"], [1, "#0d366b"]]

pio.templates["hse"] = go.layout.Template(layout=dict(
    font=dict(family="system-ui, -apple-system, 'Segoe UI', sans-serif", color=INK2, size=13),
    paper_bgcolor="#fcfcfb", plot_bgcolor="#fcfcfb",
    colorway=["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948"],
    xaxis=dict(gridcolor=GRID, linecolor=AXIS, zeroline=False, tickfont=dict(color=MUTED), title_font=dict(color=INK2)),
    yaxis=dict(gridcolor=GRID, linecolor=AXIS, zeroline=False, tickfont=dict(color=MUTED), title_font=dict(color=INK2)),
    margin=dict(l=8, r=16, t=76, b=8), barcornerradius=4, bargap=0.25,
    hoverlabel=dict(bgcolor="white", bordercolor=GRID, font=dict(color=INK)),
    legend=dict(orientation="h", x=0, xanchor="left", y=1.02, yanchor="bottom", title_text="",
                font=dict(size=12), itemwidth=30),
    title=dict(font=dict(size=15, color=INK), x=0, xref="container", xanchor="left", pad=dict(l=8),
               y=1, yref="container", yanchor="top"),
))
pio.templates.default = "plotly_white+hse"

st.markdown("""
<style>
.block-container {padding-top: 2rem; padding-bottom: 3rem;}
[data-testid="stMetricValue"] {font-size: 1.7rem;}
[data-testid="stMetricLabel"] p {color: #52514e;}
.stTabs [data-baseweb="tab-list"] {gap: 4px;}
.stTabs [data-baseweb="tab"] {padding: 8px 14px;}
.hse-sub {color: #52514e; margin-top: -0.6rem;}
.legend-dot {display:inline-block;width:10px;height:10px;border-radius:2px;margin:0 4px 0 12px;}
</style>
""", unsafe_allow_html=True)

RATE = "Tỷ lệ (%)"
SUBJECT_ALIASES = {
    "sinh": "Sinh học", "sinh học": "Sinh học",
    "hóa": "Hóa học", "hóa học": "Hóa học", "hoá học": "Hóa học",
    "lý": "Vật lý", "vật lý": "Vật lý", "vật lí": "Vật lý",
    "địa": "Địa lý", "địa lý": "Địa lý", "địa lí": "Địa lý",
    "sử": "Lịch sử", "lịch sử": "Lịch sử",
    "văn": "Ngữ văn", "ngữ văn": "Ngữ văn",
    "anh": "Tiếng Anh", "tiếng anh": "Tiếng Anh",
    "toán": "Toán",
    "khtn": "KHTN", "khoa học tự nhiên": "KHTN",
    "ktpl": "KTPL", "giáo dục kinh tế và pháp luật": "KTPL",
    "gdcd": "GDCD", "qpan": "QPAN", "gdqp": "QPAN",
    "công nghệ": "Công nghệ", "tin học": "Tin học",
    "giáo dục địa phương": "GDĐP", "gdđp": "GDĐP",
    "môn khác": "Môn khác", "khác": "Môn khác",
    "trải nghiệm hướng nghiệp": "HĐTN", "hoạt động trải nghiệm": "HĐTN",
    "hoạt động trải nghiệm, hướng nghiệp": "HĐTN", "hđtn": "HĐTN",
}
GENERIC_SUBJECTS = {"HĐTN", "Môn khác"}

# =============================================================================
# 2. XỬ LÝ DỮ LIỆU
# =============================================================================
def clean(s) -> str:
    return " ".join(unicodedata.normalize("NFC", str(s)).split())


def norm_subject(s) -> str:
    name = clean(s)
    key = name.lower()
    key = key if key in SUBJECT_ALIASES else re.sub(r"^môn\s+", "", key)
    return SUBJECT_ALIASES.get(key, name[:1].upper() + name[1:])


YEAR_RE = re.compile(r"\s*N[ăa]m\s*H[ọo]c\s*(\d{4})\s*-\s*(\d{4}).*$", re.IGNORECASE)


def clean_class(s) -> str:
    """'10DA1 Nam Hoc 2026 - 2027' -> '10DA1'"""
    name = YEAR_RE.sub("", clean(s)).upper()
    return name.replace("LỚP", "Lớp")


def school_years(values) -> list:
    found = {f"{m.group(1)}–{m.group(2)}" for m in (YEAR_RE.search(clean(v)) for v in values) if m}
    return sorted(found)


def grade_of(cls: str) -> str:
    m = re.match(r"(\d{1,2})", cls)
    return f"Khối {int(m.group(1))}" if m else "Khác"


def grade_sort_key(g: str):
    m = re.search(r"\d+", g)
    return int(m.group()) if m else 99


def rate(done, total):
    return (done / total.where(total > 0) * 100).round(1).fillna(0)


def find_sheet(xls: pd.ExcelFile, required: set):
    for name in xls.sheet_names:
        cols = {clean(c) for c in pd.read_excel(xls, sheet_name=name, nrows=0).columns}
        if required <= cols:
            return name
    return None


LESSON_COLS = {"GVBM", "Môn", "Lớp", "Tên bài dạy", "Si_So_HS", "SL_Hoan_Thanh"}
STUDENT_COLS = {"Lớp", "Học sinh", "Môn", "GVBM", "Tong_Bai_Giao", "Da_Nop"}


@st.cache_data(show_spinner=False)
def load_report(data: bytes):
    xls = pd.ExcelFile(BytesIO(data))
    lesson_sheet = find_sheet(xls, LESSON_COLS)
    if lesson_sheet is None:
        return None, None, []
    les = pd.read_excel(xls, sheet_name=lesson_sheet)
    les.columns = [clean(c) for c in les.columns]
    les = pd.DataFrame({
        "Giáo viên": les["GVBM"].map(clean),
        "Môn": les["Môn"].map(norm_subject),
        "Lớp": les["Lớp"].map(clean_class),
        "Bài dạy": les["Tên bài dạy"].map(clean),
        "Lượt giao": pd.to_numeric(les["Si_So_HS"], errors="coerce").fillna(0).astype(int),
        "Hoàn thành": pd.to_numeric(les["SL_Hoan_Thanh"], errors="coerce").fillna(0).astype(int),
    })

    stu = None
    student_sheet = find_sheet(xls, STUDENT_COLS)
    if student_sheet is not None:
        raw = pd.read_excel(xls, sheet_name=student_sheet)
        raw.columns = [clean(c) for c in raw.columns]
        stu = pd.DataFrame({
            "Lớp": raw["Lớp"].map(clean_class),
            # File cũ: "Hoàng Hiểu Minh - 10DA1" -> "Hoàng Hiểu Minh"
            "Học sinh": raw["Học sinh"].map(clean).str.replace(r"\s+-\s+\w+$", "", regex=True),
            "Môn": raw["Môn"].map(norm_subject),
            "Giáo viên": raw["GVBM"].map(clean),
            "Bài giao": pd.to_numeric(raw["Tong_Bai_Giao"], errors="coerce").fillna(0).astype(int),
            "Đã nộp": pd.to_numeric(raw["Da_Nop"], errors="coerce").fillna(0).astype(int),
        })
        # Nhiều học sinh trùng tên -> nhận diện theo (Lớp, Tên)
        stu["Mã HS"] = stu["Lớp"] + " · " + stu["Học sinh"]
    years = school_years(pd.read_excel(xls, sheet_name=lesson_sheet, usecols=["Lớp"])["Lớp"])
    return les, stu, years


@st.cache_data(show_spinner=False)
def load_assignment(data: bytes):
    """File phân công (Lớp / Giáo viên / Môn) do người dùng tự tải lên — phân công thay đổi theo năm học."""
    try:
        df = pd.read_excel(BytesIO(data))
    except Exception:
        return None
    df.columns = [clean(c) for c in df.columns]
    gv_col = next((c for c in df.columns if "giáo viên" in c.lower() or c.lower() in ("gv", "gvbm")), None)
    if gv_col is None or "Lớp" not in df.columns or "Môn" not in df.columns:
        return None
    df = df[["Lớp", gv_col, "Môn"]].dropna()
    return pd.DataFrame({
        "Lớp": df["Lớp"].map(clean_class),
        "Giáo viên": df[gv_col].map(clean),
        "Môn": df["Môn"].map(norm_subject),
    }).drop_duplicates()


def main_subjects(les: pd.DataFrame, assign: pd.DataFrame | None) -> dict:
    """Môn chuyên môn của mỗi GV (không tính HĐTN / Môn khác) — dùng để gộp các môn đó vào môn chính.
    Lấy từ chính file HSE; file phân công (nếu có) chỉ bổ sung cho GV chỉ dạy HĐTN trong báo cáo."""
    def most_common(src):
        src = src[~src["Môn"].isin(GENERIC_SUBJECTS)]
        return src.groupby("Giáo viên")["Môn"].agg(lambda s: s.value_counts().index[0]).to_dict()

    mains = most_common(les)
    if assign is not None:
        mains = most_common(assign) | mains
    return mains


def merge_hdtn(df: pd.DataFrame, mains: dict) -> pd.DataFrame:
    """Gộp HĐTN / 'Môn khác' vào môn chính của giáo viên (nếu biết)."""
    generic = df["Môn"].isin(GENERIC_SUBJECTS)
    if generic.any():
        df = df.copy()
        df.loc[generic, "Môn"] = df.loc[generic, "Giáo viên"].map(mains).fillna(df.loc[generic, "Môn"])
    return df


def summarize(df: pd.DataFrame, by) -> pd.DataFrame:
    g = df.groupby(by, as_index=False).agg(
        **{"Số bài": ("Bài dạy", "count"),
           "Lượt giao": ("Lượt giao", "sum"),
           "Hoàn thành": ("Hoàn thành", "sum"),
           "Bài dưới ngưỡng": ("_low", "sum")})
    g[RATE] = rate(g["Hoàn thành"], g["Lượt giao"])
    return g


def tier_labels(low: int, high: int) -> dict:
    return {"good": f"Đạt (≥{high}%)", "warn": f"Theo dõi ({low}–{high}%)", "crit": f"Cảnh báo (<{low}%)"}


def add_tier(df: pd.DataFrame, low: int, high: int) -> pd.DataFrame:
    lab = tier_labels(low, high)
    df = df.copy()
    df["Mức"] = df[RATE].map(lambda r: lab["good"] if r >= high else lab["warn"] if r >= low else lab["crit"])
    return df


def tier_colors(low: int, high: int) -> dict:
    lab = tier_labels(low, high)
    return {lab["good"]: GOOD, lab["warn"]: WARN, lab["crit"]: CRIT}


# =============================================================================
# 3. BIỂU ĐỒ
# =============================================================================
def show(fig, key=None):
    fig.update_layout(legend_title_text="")
    st.plotly_chart(fig, width="stretch", theme=None, key=key,
                    config={"displayModeBar": False, "displaylogo": False})


def ranked_bar(df, cat, low, high, title, hover_extra=()):
    """Thanh ngang xếp hạng theo tỷ lệ, tô màu theo mức (có chú giải chữ, không chỉ dựa vào màu)."""
    d = add_tier(df, low, high).sort_values(RATE)
    fig = px.bar(
        d, x=RATE, y=cat, orientation="h", color="Mức", text=RATE,
        color_discrete_map=tier_colors(low, high),
        category_orders={"Mức": list(tier_labels(low, high).values()), cat: d[cat].tolist()},
        hover_data={c: True for c in ("Lượt giao", "Hoàn thành", *hover_extra) if c in d.columns} | {"Mức": False},
        title=title,
    )
    fig.update_traces(texttemplate="%{x:.1f}", textposition="outside", textfont_color=INK2, cliponaxis=False)
    fig.update_layout(height=max(260, 26 * len(d) + 90), yaxis_title=None, xaxis_title="Tỷ lệ hoàn thành (%)",
                      xaxis_range=[0, 108], bargap=0.3)
    fig.add_vline(x=low, line_dash="dot", line_color=MUTED, line_width=1)
    return fig


def heatmap(pivot: pd.DataFrame, title: str, height=None):
    fig = go.Figure(go.Heatmap(
        z=pivot.values, x=pivot.columns.tolist(), y=pivot.index.tolist(),
        colorscale=SEQ_BLUE, zmin=0, zmax=100, xgap=2, ygap=2,
        texttemplate="%{z:.0f}", textfont=dict(size=11),
        hovertemplate="%{y} · %{x}<br>Tỷ lệ hoàn thành: <b>%{z:.1f}%</b><extra></extra>",
        colorbar=dict(title="%", thickness=10, outlinewidth=0),
    ))
    fig.update_layout(title=title, height=height or max(320, 24 * len(pivot) + 120),
                      xaxis=dict(side="top", showgrid=False), yaxis=dict(autorange="reversed", showgrid=False),
                      margin=dict(t=70))
    return fig


def progress_col(label=RATE):
    return st.column_config.ProgressColumn(label, min_value=0, max_value=100, format="%.1f%%")


# =============================================================================
# 4. XUẤT EXCEL
# =============================================================================
def to_excel(sheets: dict, low: int, high: int) -> bytes:
    out = BytesIO()
    with pd.ExcelWriter(out, engine="xlsxwriter") as writer:
        wb = writer.book
        red = wb.add_format({"bg_color": "#FFC7CE", "font_color": "#9C0006"})
        yellow = wb.add_format({"bg_color": "#FFEB9C", "font_color": "#9C6500"})
        green = wb.add_format({"bg_color": "#C6EFCE", "font_color": "#006100"})
        header = wb.add_format({"bold": True, "bg_color": "#EEF3FB", "border": 1, "border_color": "#C3C2B7"})
        for name, df in sheets.items():
            if df is None or df.empty:
                continue
            df.to_excel(writer, index=False, sheet_name=name)
            ws = writer.sheets[name]
            for i, col in enumerate(df.columns):
                ws.write(0, i, col, header)
                width = max(len(str(col)), df[col].astype(str).str.len().quantile(0.9) if len(df) else 0)
                ws.set_column(i, i, min(max(10, width + 2), 60))
            ws.freeze_panes(1, 0)
            ws.autofilter(0, 0, len(df), len(df.columns) - 1)
            for col in [c for c in df.columns if "Tỷ lệ" in c]:
                j, n = df.columns.get_loc(col), len(df)
                ws.conditional_format(1, j, n, j, {"type": "cell", "criteria": "<", "value": low, "format": red})
                ws.conditional_format(1, j, n, j, {"type": "cell", "criteria": "between",
                                                   "minimum": low, "maximum": high - 0.01, "format": yellow})
                ws.conditional_format(1, j, n, j, {"type": "cell", "criteria": ">=", "value": high, "format": green})
    return out.getvalue()


# =============================================================================
# 5. SIDEBAR — DỮ LIỆU
# =============================================================================
with st.sidebar:
    st.subheader("📂 Dữ liệu")
    uploaded = st.file_uploader("Báo cáo HSE (.xlsx)", type=["xlsx"],
                                help="File xuất từ HSE gồm các sheet: Hiệu suất bài dạy GV, Tỉ lệ học sinh, Tổng hợp lớp–môn.")
    with st.expander("Phân công giáo viên (tuỳ chọn)"):
        assign_up = st.file_uploader("File phân công năm học hiện tại", type=["xlsx"], key="assign")
        st.caption("Không bắt buộc — giáo viên đã lấy từ cột GVBM của file HSE. Chỉ tải lên nếu muốn xem "
                   "danh sách GV có phân công nhưng chưa giao bài. Cần các cột: Lớp, Giáo viên, Môn.")

if uploaded is not None:
    report_bytes = uploaded.getvalue()
elif st.session_state.get("use_sample") and SAMPLE_FILE.exists():
    report_bytes = SAMPLE_FILE.read_bytes()
else:
    report_bytes = None

if report_bytes is None:
    st.title("📊 HSE Dashboard")
    st.markdown('<p class="hse-sub">Phân tích tỷ lệ hoàn thành bài giao theo lớp, giáo viên, môn học và học sinh.</p>',
                unsafe_allow_html=True)
    st.info("👈 Tải file báo cáo HSE (.xlsx) ở thanh bên trái để bắt đầu.")
    if SAMPLE_FILE.exists() and st.button("Xem thử với dữ liệu mẫu (BC_HSE.xlsx)", type="primary"):
        st.session_state["use_sample"] = True
        st.rerun()
    st.stop()

with st.spinner("Đang đọc dữ liệu…"):
    lessons, students, years = load_report(report_bytes)
    assign = load_assignment(assign_up.getvalue()) if assign_up is not None else None

if lessons is None:
    st.error("Không tìm thấy sheet dữ liệu bài dạy. File cần có một sheet với các cột: "
             + ", ".join(sorted(LESSON_COLS)))
    st.stop()

mains = main_subjects(lessons, assign)
lessons = merge_hdtn(lessons, mains)
lessons["Khối"] = lessons["Lớp"].map(grade_of)
if students is not None:
    students = merge_hdtn(students, mains)
    students["Khối"] = students["Lớp"].map(grade_of)

# =============================================================================
# 6. SIDEBAR — BỘ LỌC
# =============================================================================
with st.sidebar:
    st.divider()
    st.subheader("🎯 Bộ lọc")
    grades = sorted(lessons["Khối"].unique(), key=grade_sort_key)
    sel_grades = st.multiselect("Khối", grades, placeholder="Tất cả khối")
    pool = lessons[lessons["Khối"].isin(sel_grades)] if sel_grades else lessons
    sel_classes = st.multiselect("Lớp", sorted(pool["Lớp"].unique(), key=lambda c: (grade_sort_key(grade_of(c)), c)),
                                 placeholder="Tất cả lớp")
    sel_subjects = st.multiselect("Môn", sorted(lessons["Môn"].unique()), placeholder="Tất cả môn")
    sel_teachers = st.multiselect("Giáo viên", sorted(lessons["Giáo viên"].unique()), placeholder="Tất cả giáo viên")

    st.subheader("⚙️ Ngưỡng đánh giá")
    low, high = st.slider("Cảnh báo dưới / Đạt từ (%)", 0, 100, (50, 80), step=5)


def apply_filters(df):
    if df is None:
        return None
    m = pd.Series(True, index=df.index)
    if sel_grades:
        m &= df["Khối"].isin(sel_grades)
    if sel_classes:
        m &= df["Lớp"].isin(sel_classes)
    if sel_subjects:
        m &= df["Môn"].isin(sel_subjects)
    if sel_teachers:
        m &= df["Giáo viên"].isin(sel_teachers)
    return df[m]


L = apply_filters(lessons).copy()
S = apply_filters(students)
if L.empty:
    st.warning("Không có dữ liệu phù hợp với bộ lọc hiện tại.")
    st.stop()

L[RATE] = rate(L["Hoàn thành"], L["Lượt giao"])
L["_low"] = (L[RATE] < low).astype(int)

by_class = summarize(L, ["Khối", "Lớp"])
by_teacher = summarize(L, ["Giáo viên"])
by_teacher["Môn chính"] = by_teacher["Giáo viên"].map(mains).fillna("—")
by_teacher["Số lớp"] = by_teacher["Giáo viên"].map(L.groupby("Giáo viên")["Lớp"].nunique())
by_subject = summarize(L, ["Môn"])
by_grade = summarize(L, ["Khối"])
by_cls_subj = summarize(L, ["Khối", "Lớp", "Môn"])
by_cls_subj["Giáo viên"] = by_cls_subj.set_index(["Lớp", "Môn"]).index.map(
    L.groupby(["Lớp", "Môn"])["Giáo viên"].agg(lambda s: ", ".join(sorted(s.unique()))))

stu_sum = None
if S is not None and not S.empty:
    stu_sum = S.groupby(["Mã HS", "Học sinh", "Khối", "Lớp"], as_index=False).agg(
        **{"Số môn": ("Môn", "nunique"), "Bài giao": ("Bài giao", "sum"), "Đã nộp": ("Đã nộp", "sum")})
    stu_sum[RATE] = rate(stu_sum["Đã nộp"], stu_sum["Bài giao"])
    missing = S[S["Đã nộp"] < S["Bài giao"]].groupby("Mã HS")["Môn"].agg(lambda s: ", ".join(sorted(s.unique())))
    stu_sum["Môn còn thiếu"] = stu_sum["Mã HS"].map(missing).fillna("")

overall = rate(pd.Series([L["Hoàn thành"].sum()]), pd.Series([L["Lượt giao"].sum()]))[0]

# Nút tải báo cáo
with st.sidebar:
    st.divider()
    lesson_export = L.drop(columns=["_low"]).sort_values(["Khối", "Lớp", "Môn"])
    export = {
        "Lop_Mon": by_cls_subj.drop(columns=["Bài dưới ngưỡng"]),
        "Lop": by_class.sort_values(RATE, ascending=False),
        "Giao_vien": by_teacher[["Giáo viên", "Môn chính", "Số lớp", "Số bài", "Lượt giao", "Hoàn thành",
                                 RATE, "Bài dưới ngưỡng"]].sort_values(RATE, ascending=False),
        "Mon": by_subject.sort_values(RATE, ascending=False),
        "Bai_day": lesson_export,
        "Hoc_sinh": stu_sum.drop(columns=["Mã HS"]).sort_values(RATE) if stu_sum is not None else None,
    }
    st.download_button("📥 Tải báo cáo Excel (theo bộ lọc)", data=to_excel(export, low, high),
                       file_name="Bao_Cao_HSE.xlsx", width="stretch",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# =============================================================================
# 7. TIÊU ĐỀ + KPI
# =============================================================================
st.title("📊 HSE Dashboard")
scope = [f"{L['Lớp'].nunique()} lớp", f"{L['Môn'].nunique()} môn", f"{L['Giáo viên'].nunique()} giáo viên",
         f"{len(L)} bài dạy"]
filtered = any([sel_grades, sel_classes, sel_subjects, sel_teachers])
year_txt = f"Năm học {', '.join(years)} · " if years else ""
st.markdown(f'<p class="hse-sub">{year_txt}{"Phạm vi đã lọc" if filtered else "Toàn trường"} · {" · ".join(scope)}'
            + (" · <i>dữ liệu mẫu</i>" if uploaded is None else "") + "</p>", unsafe_allow_html=True)

k = st.columns(4)
k[0].metric("Tỷ lệ hoàn thành chung", f"{overall:.1f}%", border=True,
            help="Tổng lượt hoàn thành ÷ tổng lượt giao bài (có trọng số theo sĩ số).")
k[1].metric("Lượt giao bài", f"{L['Lượt giao'].sum():,}".replace(",", "."), border=True,
            help="Tổng (sĩ số × số bài) được giao.")
k[2].metric("Lượt hoàn thành", f"{L['Hoàn thành'].sum():,}".replace(",", "."), border=True)
k[3].metric(f"Bài dạy dưới {low}%", f"{int(L['_low'].sum())} / {len(L)}", border=True,
            help="Số bài dạy có tỷ lệ hoàn thành thấp hơn ngưỡng cảnh báo.")
if stu_sum is not None:
    k2 = st.columns(4)
    n = len(stu_sum)
    zero, full = (stu_sum["Đã nộp"] == 0).sum(), (stu_sum[RATE] >= 100).sum()
    k2[0].metric("Học sinh", f"{n:,}".replace(",", "."), border=True)
    k2[1].metric("Tỷ lệ nộp TB mỗi học sinh", f"{stu_sum[RATE].mean():.1f}%", border=True,
                 help="Trung bình tỷ lệ nộp bài của từng học sinh (mỗi HS có trọng số như nhau).")
    k2[2].metric("HS hoàn thành 100%", f"{full} ({full / n * 100:.0f}%)", border=True)
    k2[3].metric("HS chưa nộp bài nào", f"{zero} ({zero / n * 100:.0f}%)", border=True)

tabs = st.tabs(["🌍 Tổng quan", "🏫 Lớp", "👩‍🏫 Giáo viên", "📚 Môn học", "🎓 Học sinh", "📝 Bài dạy"])

# =============================================================================
# 8. TAB TỔNG QUAN
# =============================================================================
with tabs[0]:
    lab = tier_labels(low, high)

    def top_bottom(df, cat, n=3):
        d = df[df["Lượt giao"] > 0].sort_values(RATE, ascending=False)
        fmt = lambda x: "  \n".join(f"**{r[cat]}** — {r[RATE]:.1f}%" for _, r in x.iterrows())
        return fmt(d.head(n)), fmt(d.tail(n).iloc[::-1])

    c1, c2, c3 = st.columns(3)
    for col, (df, cat, label) in zip((c1, c2, c3), ((by_class, "Lớp", "Lớp"), (by_teacher, "Giáo viên", "Giáo viên"),
                                                    (by_subject, "Môn", "Môn"))):
        top, bottom = top_bottom(df, cat)
        with col.container(border=True):
            st.markdown(f"**{label}**")
            st.caption("🏆 Cao nhất")
            st.markdown(top)
            st.caption("⚠️ Thấp nhất")
            st.markdown(bottom)

    g1, g2 = st.columns(2)
    with g1:
        d = add_tier(by_grade, low, high)
        d = d.sort_values("Khối", key=lambda s: s.map(grade_sort_key))
        fig = px.bar(d, x="Khối", y=RATE, color="Mức", text=RATE, color_discrete_map=tier_colors(low, high),
                     category_orders={"Mức": list(lab.values()), "Khối": d["Khối"].tolist()},
                     hover_data={"Lượt giao": True, "Hoàn thành": True, "Số bài": True, "Mức": False},
                     title="Tỷ lệ hoàn thành theo khối")
        fig.update_traces(texttemplate="%{y:.1f}", textposition="outside", textfont_color=INK2, cliponaxis=False)
        fig.update_layout(height=360, xaxis_title=None, yaxis_title="%", yaxis_range=[0, 105])
        fig.add_hline(y=low, line_dash="dot", line_color=MUTED, line_width=1)
        show(fig)
    with g2:
        bins = pd.cut(L[RATE], bins=[-0.1, 10, 20, 30, 40, 50, 60, 70, 80, 90, 99.9, 100],
                      labels=["0–10", "10–20", "20–30", "30–40", "40–50", "50–60", "60–70",
                              "70–80", "80–90", "90–<100", "100"])
        dist = bins.value_counts(sort=False).rename_axis("Khoảng (%)").reset_index(name="Số bài")
        fig = px.bar(dist, x="Khoảng (%)", y="Số bài", text="Số bài", title="Phân bố tỷ lệ hoàn thành của các bài dạy")
        fig.update_traces(marker_color=BLUE, textposition="outside", textfont_color=INK2, cliponaxis=False)
        fig.update_layout(height=360, xaxis_title="Tỷ lệ hoàn thành (%)", yaxis_title="Số bài dạy", bargap=0.15)
        show(fig)

    pv = by_cls_subj.pivot_table(index="Lớp", columns="Môn", values=RATE)
    pv = pv.loc[sorted(pv.index, key=lambda c: (grade_sort_key(grade_of(c)), c))]
    pv = pv[pv.notna().sum().sort_values(ascending=False).index]
    show(heatmap(pv, "Bản đồ nhiệt Lớp × Môn (ô trống = không có bài giao)"))

# =============================================================================
# 9. TAB LỚP
# =============================================================================
with tabs[1]:
    show(ranked_bar(by_class, "Lớp", low, high, "Xếp hạng lớp theo tỷ lệ hoàn thành", ("Số bài",)))

    st.subheader("Bảng tổng hợp lớp")
    tbl = by_class.copy()
    if stu_sum is not None:
        g = stu_sum.groupby("Lớp")
        tbl["Số HS"] = tbl["Lớp"].map(g.size())
        tbl["HS chưa nộp bài nào"] = tbl["Lớp"].map(g["Đã nộp"].apply(lambda s: (s == 0).sum()))
    st.dataframe(tbl.sort_values(RATE, ascending=False), hide_index=True, width="stretch",
                 column_config={RATE: progress_col()})

    st.subheader("🔎 Chi tiết một lớp")
    cls = st.selectbox("Chọn lớp", by_class.sort_values("Lớp", key=lambda s: s.map(
        lambda c: (grade_sort_key(grade_of(c)), c)))["Lớp"], key="cls_detail")
    row = by_class[by_class["Lớp"] == cls].iloc[0]
    m1, m2, m3 = st.columns(3)
    m1.metric("Tỷ lệ hoàn thành", f"{row[RATE]:.1f}%", f"{row[RATE] - overall:+.1f} điểm so với chung", border=True)
    m2.metric("Số bài dạy", int(row["Số bài"]), border=True)
    m3.metric("Hạng", f"{int((by_class[RATE] > row[RATE]).sum()) + 1} / {len(by_class)}", border=True)
    d1, d2 = st.columns([3, 2])
    with d1:
        show(ranked_bar(by_cls_subj[by_cls_subj["Lớp"] == cls], "Môn", low, high, f"Theo môn — {cls}",
                        ("Giáo viên", "Số bài")), key="cls_subj")
    with d2:
        if stu_sum is not None:
            cs = stu_sum[(stu_sum["Lớp"] == cls) & (stu_sum[RATE] < low)].sort_values(RATE)
            st.markdown(f"**Học sinh dưới {low}%** ({len(cs)} HS)")
            st.dataframe(cs[["Học sinh", "Bài giao", "Đã nộp", RATE, "Môn còn thiếu"]], hide_index=True,
                         width="stretch", height=380, column_config={RATE: progress_col()})

# =============================================================================
# 10. TAB GIÁO VIÊN
# =============================================================================
with tabs[2]:
    show(ranked_bar(by_teacher, "Giáo viên", low, high, "Xếp hạng giáo viên theo tỷ lệ hoàn thành",
                    ("Môn chính", "Số bài")))

    st.subheader("Bảng tổng hợp giáo viên")
    st.dataframe(by_teacher[["Giáo viên", "Môn chính", "Số lớp", "Số bài", "Lượt giao", "Hoàn thành", RATE,
                             "Bài dưới ngưỡng"]].sort_values(RATE, ascending=False),
                 hide_index=True, width="stretch", column_config={
                     RATE: progress_col(), "Bài dưới ngưỡng": st.column_config.NumberColumn(
                         f"Bài dưới {low}%", help="Số bài dạy có tỷ lệ hoàn thành dưới ngưỡng cảnh báo")})

    st.subheader("🔎 Chi tiết một giáo viên")
    gv = st.selectbox("Chọn giáo viên", sorted(by_teacher["Giáo viên"]), key="gv_detail")
    trow = by_teacher[by_teacher["Giáo viên"] == gv].iloc[0]
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Tỷ lệ hoàn thành", f"{trow[RATE]:.1f}%", f"{trow[RATE] - overall:+.1f} điểm so với chung", border=True)
    m2.metric("Môn chính", trow["Môn chính"], border=True)
    m3.metric("Số lớp / bài", f"{int(trow['Số lớp'])} / {int(trow['Số bài'])}", border=True)
    m4.metric(f"Bài dưới {low}%", int(trow["Bài dưới ngưỡng"]), border=True)
    t1, t2 = st.columns([2, 3])
    with t1:
        show(ranked_bar(summarize(L[L["Giáo viên"] == gv], ["Lớp"]), "Lớp", low, high, "Theo lớp",
                        ("Số bài",)), key="gv_cls")
    with t2:
        st.markdown("**Danh sách bài dạy**")
        st.dataframe(L[L["Giáo viên"] == gv][["Lớp", "Môn", "Bài dạy", "Lượt giao", "Hoàn thành", RATE]]
                     .sort_values(RATE), hide_index=True, width="stretch", height=380,
                     column_config={RATE: progress_col()})

    if assign is not None and not sel_teachers:
        st.subheader("🕳️ Giáo viên có phân công nhưng chưa có bài trong báo cáo")
        a = assign[assign["Môn"].isin(set(lessons["Môn"]))]
        if sel_grades:
            a = a[a["Lớp"].map(grade_of).isin(sel_grades)]
        if sel_classes:
            a = a[a["Lớp"].isin(sel_classes)]
        if sel_subjects:
            a = a[a["Môn"].isin(sel_subjects)]
        a = a[~a["Giáo viên"].isin(set(lessons["Giáo viên"]))]
        if a.empty:
            st.success("Tất cả giáo viên được phân công (trong phạm vi lọc) đều đã có bài giao.")
        else:
            miss = a.groupby("Giáo viên", as_index=False).agg(
                **{"Môn": ("Môn", lambda s: ", ".join(sorted(s.unique()))),
                   "Số lớp phân công": ("Lớp", "nunique"),
                   "Các lớp": ("Lớp", lambda s: ", ".join(sorted(s.unique(), key=lambda c: (grade_sort_key(grade_of(c)), c))))})
            st.caption(f"{len(miss)} giáo viên · chỉ tính các môn có trong báo cáo HSE · đối chiếu theo tên giáo viên.")
            st.dataframe(miss.sort_values("Số lớp phân công", ascending=False), hide_index=True, width="stretch")

# =============================================================================
# 11. TAB MÔN HỌC
# =============================================================================
with tabs[3]:
    s1, s2 = st.columns(2)
    with s1:
        show(ranked_bar(by_subject, "Môn", low, high, "Tỷ lệ hoàn thành theo môn", ("Số bài",)), key="subj_rank")
    with s2:
        order = by_subject.sort_values(RATE, ascending=False)["Môn"].tolist()
        fig = px.box(L, x=RATE, y="Môn", points="all", category_orders={"Môn": order[::-1]},
                     hover_data={"Lớp": True, "Giáo viên": True, "Bài dạy": True},
                     title="Độ phân tán tỷ lệ hoàn thành của từng bài, theo môn")
        fig.update_traces(marker=dict(color=BLUE, size=6, opacity=0.55), line=dict(color="#1c5cab", width=1.5),
                          fillcolor="rgba(42,120,214,0.12)", jitter=0.4, pointpos=0, orientation="h")
        fig.update_layout(height=max(260, 26 * len(order) + 90), yaxis_title=None,
                          xaxis_title="Tỷ lệ hoàn thành (%)", xaxis_range=[-3, 103])
        show(fig, key="subj_box")

    pv = by_cls_subj.groupby(["Khối", "Môn"]).agg({"Hoàn thành": "sum", "Lượt giao": "sum"})
    pv = rate(pv["Hoàn thành"], pv["Lượt giao"]).unstack()
    pv = pv.loc[sorted(pv.index, key=grade_sort_key)]
    show(heatmap(pv, "Khối × Môn", height=max(300, 40 * len(pv) + 140)), key="grade_subj")

    st.dataframe(by_subject.sort_values(RATE, ascending=False), hide_index=True, width="stretch",
                 column_config={RATE: progress_col(), "Bài dưới ngưỡng": f"Bài dưới {low}%"})

# =============================================================================
# 12. TAB HỌC SINH
# =============================================================================
with tabs[4]:
    if stu_sum is None:
        st.info("File báo cáo không có sheet dữ liệu học sinh (cần các cột: " + ", ".join(sorted(STUDENT_COLS)) + ").")
    else:
        h1, h2 = st.columns(2)
        with h1:
            buckets = pd.cut(stu_sum[RATE], bins=[-0.1, 0, 49.99, 79.99, 99.99, 100],
                             labels=["0%", "1–49%", "50–79%", "80–99%", "100%"])
            bd = buckets.value_counts(sort=False).rename_axis("Mức nộp bài").reset_index(name="Số HS")
            bd["Tỷ trọng"] = (bd["Số HS"] / bd["Số HS"].sum() * 100).round(1)
            fig = px.bar(bd, x="Mức nộp bài", y="Số HS", text=bd.apply(lambda r: f"{r['Số HS']} ({r['Tỷ trọng']:.0f}%)", axis=1),
                         title="Phân bố học sinh theo tỷ lệ nộp bài")
            fig.update_traces(marker_color=["#184f95", "#256abf", "#3987e5", "#6da7ec", "#86b6ef"][::-1],
                              textposition="outside", textfont_color=INK2, cliponaxis=False)
            fig.update_layout(height=360, xaxis_title=None, yaxis_title="Số học sinh")
            show(fig, key="stu_bucket")
        with h2:
            z = stu_sum.groupby("Lớp").agg(n=("Mã HS", "count"), zero=("Đã nộp", lambda s: (s == 0).sum())).reset_index()
            z["Tỷ lệ HS chưa nộp (%)"] = (z["zero"] / z["n"] * 100).round(1)
            z = z.sort_values("Tỷ lệ HS chưa nộp (%)", ascending=False).head(12).iloc[::-1]
            fig = px.bar(z, x="Tỷ lệ HS chưa nộp (%)", y="Lớp", orientation="h", text="Tỷ lệ HS chưa nộp (%)",
                         hover_data={"n": ":d", "zero": ":d"}, labels={"n": "Sĩ số", "zero": "HS chưa nộp"},
                         title="12 lớp có tỷ lệ học sinh chưa nộp bài nào cao nhất")
            fig.update_traces(marker_color=CRIT, texttemplate="%{x:.0f}%", textposition="outside",
                              textfont_color=INK2, cliponaxis=False)
            fig.update_layout(height=360, yaxis_title=None, xaxis_range=[0, max(10, z["Tỷ lệ HS chưa nộp (%)"].max() * 1.15)])
            show(fig, key="stu_zero")

        st.subheader("Tra cứu học sinh")
        f1, f2 = st.columns([2, 1])
        q = f1.text_input("Tìm theo tên học sinh", placeholder="Nhập tên…")
        only_low = f2.toggle(f"Chỉ HS dưới {low}%", value=True)
        view = stu_sum
        if q:
            view = view[view["Học sinh"].str.contains(clean(q), case=False, regex=False)]
        if only_low:
            view = view[view[RATE] < low]
        st.caption(f"{len(view)} học sinh")
        st.dataframe(view.sort_values([RATE, "Lớp"])[["Học sinh", "Lớp", "Số môn", "Bài giao", "Đã nộp", RATE,
                                                       "Môn còn thiếu"]],
                     hide_index=True, width="stretch", height=460, column_config={RATE: progress_col()})

# =============================================================================
# 13. TAB BÀI DẠY
# =============================================================================
with tabs[5]:
    b1, b2 = st.columns([2, 1])
    q = b1.text_input("Tìm theo tên bài dạy", placeholder="VD: ôn tập, giữa kỳ…", key="lesson_q")
    only_low_l = b2.toggle(f"Chỉ bài dưới {low}%", value=False)
    view = L
    if q:
        view = view[view["Bài dạy"].str.contains(clean(q), case=False, regex=False)]
    if only_low_l:
        view = view[view[RATE] < low]
    st.caption(f"{len(view)} bài dạy · sắp xếp từ thấp đến cao")
    st.dataframe(view.sort_values(RATE)[["Bài dạy", "Lớp", "Môn", "Giáo viên", "Lượt giao", "Hoàn thành", RATE]],
                 hide_index=True, width="stretch", height=560, column_config={RATE: progress_col()})
