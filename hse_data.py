"""Đọc, chuẩn hoá và tổng hợp dữ liệu báo cáo HSE."""
import re
import unicodedata
from io import BytesIO

import pandas as pd
import streamlit as st

RATE = "Tỷ lệ (%)"
LESSON_COLS = {"GVBM", "Môn", "Lớp", "Tên bài dạy", "Si_So_HS", "SL_Hoan_Thanh"}
STUDENT_COLS = {"Lớp", "Học sinh", "Môn", "GVBM", "Tong_Bai_Giao", "Da_Nop"}

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
    "công nghệ": "Công nghệ", "cn": "Công nghệ", "tin học": "Tin học",
    "giáo dục địa phương": "GDĐP", "gdđp": "GDĐP",
    "môn khác": "Môn khác", "khác": "Môn khác",
    "trải nghiệm hướng nghiệp": "HĐTN", "hoạt động trải nghiệm": "HĐTN",
    "hoạt động trải nghiệm, hướng nghiệp": "HĐTN", "hđtn": "HĐTN",
}
# Các "môn" không phải chuyên môn -> gộp vào môn chính của giáo viên
GENERIC_SUBJECTS = {"HĐTN", "Môn khác"}

YEAR_RE = re.compile(r"\s*N[ăa]m\s*H[ọo]c\s*(\d{4})\s*-\s*(\d{4}).*$", re.IGNORECASE)


# -----------------------------------------------------------------------------
# Chuẩn hoá
# -----------------------------------------------------------------------------
def clean(s) -> str:
    return " ".join(unicodedata.normalize("NFC", str(s)).split())


def norm_subject(s) -> str:
    name = clean(s)
    key = name.lower()
    key = key if key in SUBJECT_ALIASES else re.sub(r"^môn\s+", "", key)
    return SUBJECT_ALIASES.get(key, name[:1].upper() + name[1:])


def clean_name(s) -> str:
    """Tên người: 'HÀ THỊ KIM NGÂN' -> 'Hà Thị Kim Ngân'."""
    name = clean(s)
    return name.title() if name.isupper() else name


def clean_class(s) -> str:
    """'10DA1 Nam Hoc 2026 - 2027' -> '10DA1'"""
    return YEAR_RE.sub("", clean(s)).upper().replace("LỚP", "Lớp")


def school_years(values) -> list:
    found = {f"{m.group(1)}–{m.group(2)}" for m in (YEAR_RE.search(clean(v)) for v in values) if m}
    return sorted(found)


def grade_of(cls: str) -> str:
    m = re.match(r"(\d{1,2})", cls)
    return f"Khối {int(m.group(1))}" if m else "Khác"


def grade_key(g: str) -> int:
    m = re.search(r"\d+", g)
    return int(m.group()) if m else 99


def class_key(c: str):
    return grade_key(grade_of(c)), c


def rate(done, total):
    return (done / total.where(total > 0) * 100).round(1).fillna(0)


# -----------------------------------------------------------------------------
# Đọc file
# -----------------------------------------------------------------------------
def _find_sheet(xls: pd.ExcelFile, required: set):
    for name in xls.sheet_names:
        cols = {clean(c) for c in pd.read_excel(xls, sheet_name=name, nrows=0).columns}
        if required <= cols:
            return name
    return None


@st.cache_data(show_spinner=False, max_entries=10)
def load_report(data: bytes):
    """Trả về (bài dạy, học sinh | None, năm học). Bài dạy = None nếu file không đúng định dạng."""
    xls = pd.ExcelFile(BytesIO(data))
    lesson_sheet = _find_sheet(xls, LESSON_COLS)
    if lesson_sheet is None:
        return None, None, []
    raw = pd.read_excel(xls, sheet_name=lesson_sheet)
    raw.columns = [clean(c) for c in raw.columns]
    lessons = pd.DataFrame({
        "Giáo viên": raw["GVBM"].map(clean_name),
        "Môn": raw["Môn"].map(norm_subject),
        "Lớp": raw["Lớp"].map(clean_class),
        "Bài dạy": raw["Tên bài dạy"].map(clean),
        "Lượt giao": pd.to_numeric(raw["Si_So_HS"], errors="coerce").fillna(0).astype(int),
        "Hoàn thành": pd.to_numeric(raw["SL_Hoan_Thanh"], errors="coerce").fillna(0).astype(int),
    })
    years = school_years(raw["Lớp"])

    students = None
    student_sheet = _find_sheet(xls, STUDENT_COLS)
    if student_sheet is not None:
        raw = pd.read_excel(xls, sheet_name=student_sheet)
        raw.columns = [clean(c) for c in raw.columns]
        students = pd.DataFrame({
            "Lớp": raw["Lớp"].map(clean_class),
            # File cũ: "Hoàng Hiểu Minh - 10DA1" -> "Hoàng Hiểu Minh"
            "Học sinh": raw["Học sinh"].map(clean).str.replace(r"\s+-\s+\w+$", "", regex=True),
            "Môn": raw["Môn"].map(norm_subject),
            "Giáo viên": raw["GVBM"].map(clean_name),
            "Bài giao": pd.to_numeric(raw["Tong_Bai_Giao"], errors="coerce").fillna(0).astype(int),
            "Đã nộp": pd.to_numeric(raw["Da_Nop"], errors="coerce").fillna(0).astype(int),
        })
        # Nhiều học sinh trùng tên -> nhận diện theo (Lớp, Tên)
        students["Mã HS"] = students["Lớp"] + " · " + students["Học sinh"]
    return lessons, students, years


def _is_teacher_col(c: str) -> bool:
    c = c.lower()
    return "giáo viên" in c or c in ("gv", "gvbm") or ("họ" in c and "tên" in c)


@st.cache_data(show_spinner=False, max_entries=5)
def load_assignment(data: bytes):
    """File phân công do người dùng tải lên (phân công thay đổi theo năm học).
    Hỗ trợ cả bảng phẳng lẫn bảng có ô gộp (tên GV / lớp gộp qua nhiều dòng môn),
    tên viết HOA và dòng tiêu đề không nằm ở dòng đầu."""
    try:
        raw = pd.read_excel(BytesIO(data), header=None, dtype=str)
    except Exception:
        return None
    for i in range(min(20, len(raw))):
        cells = [clean(x) for x in raw.iloc[i].fillna("")]
        low = [c.lower() for c in cells]
        if any(c.startswith("lớp") for c in low) and any("môn" in c for c in low) and any(map(_is_teacher_col, cells)):
            break
    else:
        return None
    lop = next(j for j, c in enumerate(low) if c.startswith("lớp"))
    mon = next(j for j, c in enumerate(low) if "môn" in c)
    gv = next(j for j, c in enumerate(cells) if _is_teacher_col(c))
    df = raw.iloc[i + 1:, [lop, gv, mon]].copy()
    df.columns = ["Lớp", "Giáo viên", "Môn"]
    df[["Lớp", "Giáo viên"]] = df[["Lớp", "Giáo viên"]].ffill()  # ô gộp -> điền xuống
    df = df.dropna()
    return pd.DataFrame({
        "Lớp": df["Lớp"].map(clean_class),
        "Giáo viên": df["Giáo viên"].map(clean_name),
        "Môn": df["Môn"].map(norm_subject),
    }).query("`Giáo viên` != '' and Môn != ''").drop_duplicates()


def main_subjects(lessons: pd.DataFrame, assign: pd.DataFrame | None) -> dict:
    """Môn chuyên môn của mỗi GV (không tính HĐTN / Môn khác).
    Lấy từ chính file HSE; file phân công (nếu có) chỉ bổ sung cho GV thiếu."""
    def most_common(src):
        src = src[~src["Môn"].isin(GENERIC_SUBJECTS)]
        return src.groupby("Giáo viên")["Môn"].agg(lambda s: s.value_counts().index[0]).to_dict()

    mains = most_common(lessons)
    if assign is not None:
        mains = most_common(assign) | mains
    return mains


def merge_generic(df: pd.DataFrame, mains: dict) -> pd.DataFrame:
    """Gộp HĐTN / 'Môn khác' vào môn chính của giáo viên (nếu biết)."""
    generic = df["Môn"].isin(GENERIC_SUBJECTS)
    if generic.any():
        df = df.copy()
        df.loc[generic, "Môn"] = df.loc[generic, "Giáo viên"].map(mains).fillna(df.loc[generic, "Môn"])
    return df


# -----------------------------------------------------------------------------
# Tổng hợp
# -----------------------------------------------------------------------------
def summarize(df: pd.DataFrame, by) -> pd.DataFrame:
    g = df.groupby(by, as_index=False).agg(
        **{"Số bài": ("Bài dạy", "count"),
           "Lượt giao": ("Lượt giao", "sum"),
           "Hoàn thành": ("Hoàn thành", "sum"),
           "Bài dưới ngưỡng": ("_low", "sum")})
    g[RATE] = rate(g["Hoàn thành"], g["Lượt giao"])
    return g


def summarize_students(S: pd.DataFrame) -> pd.DataFrame:
    stu = S.groupby(["Mã HS", "Học sinh", "Khối", "Lớp"], as_index=False).agg(
        **{"Số môn": ("Môn", "nunique"), "Bài giao": ("Bài giao", "sum"), "Đã nộp": ("Đã nộp", "sum")})
    stu[RATE] = rate(stu["Đã nộp"], stu["Bài giao"])
    missing = S[S["Đã nộp"] < S["Bài giao"]].groupby("Mã HS")["Môn"].agg(lambda s: ", ".join(sorted(s.unique())))
    stu["Môn còn thiếu"] = stu["Mã HS"].map(missing).fillna("")
    return stu


def tier_labels(low: int, high: int) -> list:
    return [f"Đạt (≥{high}%)", f"Theo dõi ({low}–{high}%)", f"Cảnh báo (<{low}%)"]


def tier_of(r: float, low: int, high: int) -> str:
    good, warn, crit = tier_labels(low, high)
    return good if r >= high else warn if r >= low else crit


# -----------------------------------------------------------------------------
# Xuất Excel
# -----------------------------------------------------------------------------
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
                width = max(len(str(col)), df[col].astype(str).str.len().quantile(0.9))
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
