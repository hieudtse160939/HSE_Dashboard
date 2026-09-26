from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import streamlit as st

import hse_data as hd
from hse_data import RATE

st.set_page_config(page_title="HSE Dashboard", page_icon=":material/monitoring:", layout="wide")

SAMPLE_FILE = Path(__file__).parent / "BC_HSE.xlsx"

# -----------------------------------------------------------------------------
# Dữ liệu đầu vào
# -----------------------------------------------------------------------------
with st.sidebar:
    uploaded = st.file_uploader(
        "Báo cáo HSE (.xlsx)", type=["xlsx"],
        help="File xuất từ HSE gồm các sheet: Hiệu suất bài dạy GV, Tỉ lệ học sinh, Tổng hợp lớp–môn.")
    with st.expander("Danh sách giáo viên năm học (tuỳ chọn)", icon=":material/badge:"):
        assign_up = st.file_uploader("Danh sách giáo viên / phân công", type=["xlsx"], key="assign")
        st.caption("Không bắt buộc — giáo viên đã lấy từ cột GVBM của file HSE. Tải lên để xem môn "
                   "phân công, lớp chủ nhiệm và giáo viên chưa giao bài. Hỗ trợ file dạng "
                   "STT | Họ tên | Chủ nhiệm | Môn (ô gộp = giáo viên dạy nhiều môn).")

if uploaded is not None:
    report_bytes = uploaded.getvalue()
elif st.session_state.get("use_sample") and SAMPLE_FILE.exists():
    report_bytes = SAMPLE_FILE.read_bytes()
else:
    report_bytes = None

if report_bytes is None:
    st.session_state.sample_available = SAMPLE_FILE.exists()
    st.navigation([st.Page("app_pages/welcome.py", title="Bắt đầu", icon=":material/upload_file:")],
                  position="hidden").run()
    st.stop()

with st.spinner("Đang đọc dữ liệu…"):
    lessons, students, years = hd.load_report(report_bytes)
    assign = hd.load_assignment(assign_up.getvalue()) if assign_up is not None else None
    if assign is not None:
        assign = hd.align_names(assign, lessons["Giáo viên"])

if lessons is None:
    st.error("Không tìm thấy sheet dữ liệu bài dạy. File cần một sheet có các cột: "
             + ", ".join(sorted(hd.LESSON_COLS)), icon=":material/error:")
    st.stop()

mains = hd.main_subjects(lessons, assign)
lessons = hd.merge_generic(lessons, mains)
lessons["Khối"] = lessons["Lớp"].map(hd.grade_of)
if students is not None:
    students = hd.merge_generic(students, mains)
    students["Khối"] = students["Lớp"].map(hd.grade_of)

# -----------------------------------------------------------------------------
# Bộ lọc
# -----------------------------------------------------------------------------
with st.sidebar:
    st.subheader("Bộ lọc", icon=":material/filter_list:")
    grades = sorted(lessons["Khối"].unique(), key=hd.grade_key)
    sel_grades = st.pills("Khối", grades, selection_mode="multi", key="f_grades")
    pool = lessons[lessons["Khối"].isin(sel_grades)] if sel_grades else lessons
    sel_classes = st.multiselect("Lớp", sorted(pool["Lớp"].unique(), key=hd.class_key),
                                 placeholder="Tất cả lớp", key="f_classes")
    sel_subjects = st.multiselect("Môn", sorted(lessons["Môn"].unique()), placeholder="Tất cả môn",
                                  key="f_subjects")
    sel_teachers = st.multiselect("Giáo viên", sorted(lessons["Giáo viên"].unique()),
                                  placeholder="Tất cả giáo viên", key="f_teachers")
    low, high = st.slider("Ngưỡng cảnh báo / đạt (%)", 0, 100, (50, 80), step=5, key="f_threshold",
                          help="Dưới mức thứ nhất là cảnh báo; từ mức thứ hai trở lên là đạt.")


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
L[RATE] = hd.rate(L["Hoàn thành"], L["Lượt giao"])
L["_low"] = (L[RATE] < low).astype(int)

ctx = SimpleNamespace(
    lessons=lessons, assign=assign, mains=mains, L=L, low=low, high=high,
    filtered=any([sel_grades, sel_classes, sel_subjects, sel_teachers]),
    sel_grades=sel_grades, sel_classes=sel_classes, sel_subjects=sel_subjects, sel_teachers=sel_teachers,
)
if not L.empty:
    ctx.overall = float(hd.rate(pd.Series([L["Hoàn thành"].sum()]), pd.Series([L["Lượt giao"].sum()]))[0])
    ctx.by_class = hd.summarize(L, ["Khối", "Lớp"])
    ctx.by_teacher = hd.summarize(L, ["Giáo viên"])
    # GV dạy nhiều môn (VD: Vật lý + Công nghệ): liệt kê đủ, mỗi bài vẫn tính đúng môn của nó
    ctx.by_teacher["Môn dạy"] = ctx.by_teacher["Giáo viên"].map(
        L.groupby("Giáo viên")["Môn"].agg(lambda s: ", ".join(s.value_counts().index)))
    if assign is not None and "Chủ nhiệm / vai trò" in assign.columns:
        roles = assign.drop_duplicates("Giáo viên").set_index("Giáo viên")["Chủ nhiệm / vai trò"]
        ctx.by_teacher["Chủ nhiệm / vai trò"] = ctx.by_teacher["Giáo viên"].map(roles).fillna("")
    if assign is not None:
        assigned = assign.groupby("Giáo viên")["Môn"].agg(lambda s: ", ".join(dict.fromkeys(s)))
        ctx.by_teacher["Môn phân công"] = ctx.by_teacher["Giáo viên"].map(assigned).fillna("")
    ctx.by_teacher["Số lớp"] = ctx.by_teacher["Giáo viên"].map(L.groupby("Giáo viên")["Lớp"].nunique())
    ctx.by_subject = hd.summarize(L, ["Môn"])
    ctx.by_grade = hd.summarize(L, ["Khối"])
    ctx.by_cls_subj = hd.summarize(L, ["Khối", "Lớp", "Môn"])
    ctx.by_cls_subj["Giáo viên"] = ctx.by_cls_subj.set_index(["Lớp", "Môn"]).index.map(
        L.groupby(["Lớp", "Môn"])["Giáo viên"].agg(lambda s: ", ".join(sorted(s.unique()))))
    ctx.stu = hd.summarize_students(S) if S is not None and not S.empty else None
st.session_state.hse = ctx

# -----------------------------------------------------------------------------
# Xuất Excel
# -----------------------------------------------------------------------------
if not L.empty:
    with st.sidebar:
        tcols = ["Giáo viên", "Môn dạy", "Số lớp", "Số bài", "Lượt giao", "Hoàn thành", RATE, "Bài dưới ngưỡng"]
        tcols += [col for col in ("Môn phân công", "Chủ nhiệm / vai trò") if col in ctx.by_teacher.columns]
        export = {
            "Lop_Mon": ctx.by_cls_subj,
            "Lop": ctx.by_class.sort_values(RATE, ascending=False),
            "Giao_vien": ctx.by_teacher[tcols].sort_values(RATE, ascending=False),
            "Mon": ctx.by_subject.sort_values(RATE, ascending=False),
            "Bai_day": L.drop(columns=["_low"]).sort_values(["Khối", "Lớp", "Môn"]),
            "Hoc_sinh": ctx.stu.drop(columns=["Mã HS"]).sort_values(RATE) if ctx.stu is not None else None,
        }
        st.download_button("Tải báo cáo Excel", data=hd.to_excel(export, low, high), icon=":material/download:",
                           file_name="Bao_Cao_HSE.xlsx", width="stretch", type="primary",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        st.caption("Xuất theo bộ lọc hiện tại, gồm 6 sheet.")

# -----------------------------------------------------------------------------
# Điều hướng
# -----------------------------------------------------------------------------
page = st.navigation([
    st.Page("app_pages/overview.py", title="Tổng quan", icon=":material/dashboard:", default=True),
    st.Page("app_pages/classes.py", title="Lớp", icon=":material/meeting_room:"),
    st.Page("app_pages/teachers.py", title="Giáo viên", icon=":material/person:"),
    st.Page("app_pages/subjects.py", title="Môn học", icon=":material/menu_book:"),
    st.Page("app_pages/students.py", title="Học sinh", icon=":material/school:"),
    st.Page("app_pages/lessons.py", title="Bài dạy", icon=":material/assignment:"),
], position="top")

st.title(page.title, icon=page.icon)
scope = [f"Năm học {', '.join(years)}"] if years else []
scope.append("Phạm vi đã lọc" if ctx.filtered else "Toàn trường")
scope += [f"{L['Lớp'].nunique()} lớp", f"{L['Môn'].nunique()} môn", f"{L['Giáo viên'].nunique()} giáo viên",
          f"{len(L)} bài dạy"]
if uploaded is None:
    scope.append("dữ liệu mẫu")
st.caption(" · ".join(scope))

if L.empty:
    st.warning("Không có dữ liệu phù hợp với bộ lọc hiện tại.", icon=":material/filter_alt_off:")
    st.stop()

page.run()
