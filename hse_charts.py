"""Biểu đồ Altair dùng chung cho các trang."""
import altair as alt
import pandas as pd
import streamlit as st

from hse_data import RATE, tier_labels, tier_of

INK2, MUTED = "#52514e", "#898781"
BLUE = "#2a78d6"
STATUS = ["#0ca30c", "#f0a202", "#d03b3b"]  # đạt / theo dõi / cảnh báo
BLUES = ["#cde2fb", "#86b6ef", "#3987e5", "#1c5cab", "#0d366b"]
RATE_AXIS = alt.X("rate:Q", title="Tỷ lệ hoàn thành (%)", scale=alt.Scale(domain=[0, 105], nice=False),
                  axis=alt.Axis(values=list(range(0, 101, 20))))


def _tier_color(low, high, legend=True):
    return alt.Color("tier:N", scale=alt.Scale(domain=tier_labels(low, high), range=STATUS),
                     legend=alt.Legend(orient="top", title=None, symbolType="square") if legend else None)


def _threshold(low, axis="x"):
    return alt.Chart(pd.DataFrame({"v": [low]})).mark_rule(strokeDash=[4, 4], color=MUTED).encode(
        **{axis: "v:Q"})


def show(chart, key=None):
    st.altair_chart(chart, key=key)


def ranked_bar(df: pd.DataFrame, cat: str, low: int, high: int, extra=(), legend=True):
    """Thanh ngang xếp hạng theo tỷ lệ, cao nhất ở trên; màu theo mức kèm chú giải chữ."""
    d = pd.DataFrame({"cat": df[cat].values, "rate": df[RATE].values,
                      "giao": df["Lượt giao"].values, "ht": df["Hoàn thành"].values})
    d["tier"] = d["rate"].map(lambda r: tier_of(r, low, high))
    tips = [alt.Tooltip("cat:N", title=cat), alt.Tooltip("rate:Q", title=RATE, format=".1f"),
            alt.Tooltip("giao:Q", title="Lượt giao"), alt.Tooltip("ht:Q", title="Hoàn thành")]
    for i, col in enumerate(c for c in extra if c in df.columns):
        d[f"x{i}"] = df[col].values
        tips.append(alt.Tooltip(f"x{i}:N", title=col))
    order = d.sort_values(["rate", "cat"], ascending=[False, True])["cat"].tolist()
    base = alt.Chart(d).encode(
        y=alt.Y("cat:N", sort=order, title=None, axis=alt.Axis(labelLimit=240)),
        x=RATE_AXIS, tooltip=tips)
    bars = base.mark_bar(cornerRadiusEnd=4, height={"band": 0.72}).encode(color=_tier_color(low, high, legend))
    labels = base.mark_text(align="left", dx=4, color=INK2, fontSize=11).encode(text=alt.Text("rate:Q", format=".1f"))
    return (bars + labels + _threshold(low)).properties(height=max(160, 26 * len(d) + (110 if legend else 80)))


def grade_bar(df: pd.DataFrame, low: int, high: int):
    d = pd.DataFrame({"cat": df["Khối"].values, "rate": df[RATE].values,
                      "giao": df["Lượt giao"].values, "ht": df["Hoàn thành"].values, "n": df["Số bài"].values})
    d["tier"] = d["rate"].map(lambda r: tier_of(r, low, high))
    base = alt.Chart(d).encode(
        x=alt.X("cat:N", sort=list(d["cat"]), title=None, axis=alt.Axis(labelAngle=0)),
        y=alt.Y("rate:Q", title="Tỷ lệ hoàn thành (%)", scale=alt.Scale(domain=[0, 105], nice=False),
                axis=alt.Axis(values=list(range(0, 101, 20)))),
        tooltip=[alt.Tooltip("cat:N", title="Khối"), alt.Tooltip("rate:Q", title=RATE, format=".1f"),
                 alt.Tooltip("n:Q", title="Số bài"), alt.Tooltip("giao:Q", title="Lượt giao"),
                 alt.Tooltip("ht:Q", title="Hoàn thành")])
    bars = base.mark_bar(cornerRadiusEnd=4, width={"band": 0.6}).encode(color=_tier_color(low, high))
    labels = base.mark_text(dy=-8, color=INK2, fontSize=11).encode(text=alt.Text("rate:Q", format=".1f"))
    return (bars + labels + _threshold(low, "y")).properties(height=320)


def count_bar(df: pd.DataFrame, cat: str, value: str, color=BLUE, colors=None, label=None, horizontal=False):
    """Cột đếm đơn giản (một màu, hoặc thang màu theo thứ tự nếu truyền `colors`)."""
    d = pd.DataFrame({"cat": df[cat].astype(str).values, "v": df[value].values,
                      "label": (df[label] if label else df[value]).astype(str).values})
    order = list(d["cat"])
    if horizontal:
        enc = dict(y=alt.Y("cat:N", sort=order, title=None), x=alt.X("v:Q", title=value))
        text = dict(align="left", dx=4)
    else:
        enc = dict(x=alt.X("cat:N", sort=order, title=None, axis=alt.Axis(labelAngle=0)), y=alt.Y("v:Q", title=value))
        text = dict(dy=-8)
    base = alt.Chart(d).encode(**enc, tooltip=[alt.Tooltip("cat:N", title=cat), alt.Tooltip("v:Q", title=value)])
    fill = (alt.Color("cat:N", scale=alt.Scale(domain=order, range=colors), legend=None) if colors
            else alt.value(color))
    mark = dict(cornerRadiusEnd=4, height={"band": 0.72}) if horizontal else dict(cornerRadiusEnd=4, width={"band": 0.72})
    bars = base.mark_bar(**mark).encode(color=fill)
    labels = base.mark_text(color=INK2, fontSize=11, **text).encode(text="label:N")
    return (bars + labels).properties(height=26 * len(d) + 70 if horizontal else 300)


def heatmap(long: pd.DataFrame, row: str, col: str, row_order, col_order, cell=22):
    """Bản đồ nhiệt tỷ lệ hoàn thành. Ô không có dữ liệu để trống."""
    d = pd.DataFrame({"r": long[row].values, "c": long[col].values, "rate": long[RATE].values,
                      "giao": long["Lượt giao"].values})
    base = alt.Chart(d).encode(
        x=alt.X("c:N", sort=list(col_order), title=None, axis=alt.Axis(orient="top", labelAngle=0, labelLimit=90)),
        y=alt.Y("r:N", sort=list(row_order), title=None),
        tooltip=[alt.Tooltip("r:N", title=row), alt.Tooltip("c:N", title=col),
                 alt.Tooltip("rate:Q", title=RATE, format=".1f"), alt.Tooltip("giao:Q", title="Lượt giao")])
    rects = base.mark_rect(stroke="white", strokeWidth=2, cornerRadius=3).encode(
        color=alt.Color("rate:Q", title="%", scale=alt.Scale(domain=[0, 100], range=BLUES),
                        legend=alt.Legend(orient="right", gradientLength=160)))
    text = base.mark_text(fontSize=11).encode(
        text=alt.Text("rate:Q", format=".0f"),
        color=alt.condition("datum.rate >= 55", alt.value("white"), alt.value("#1f2328")))
    return (rects + text).properties(height=cell * len(row_order) + 40)


def spread(lessons: pd.DataFrame, order):
    """Hộp + điểm: độ phân tán tỷ lệ hoàn thành của từng bài theo môn."""
    d = pd.DataFrame({"cat": lessons["Môn"].values, "rate": lessons[RATE].values,
                      "cls": lessons["Lớp"].values, "gv": lessons["Giáo viên"].values,
                      "bai": lessons["Bài dạy"].values})
    y = alt.Y("cat:N", sort=list(order), title=None)
    box = alt.Chart(d).mark_boxplot(extent="min-max", size=16, color="#b7d3f6", opacity=0.9,
                                    median={"color": "#104281"}, rule={"color": MUTED}, ticks=False,
                                    outliers=False).encode(y=y, x=RATE_AXIS.copy())
    dots = alt.Chart(d).transform_calculate(j="(random() - 0.5) * 14").mark_circle(
        size=28, color=BLUE, opacity=0.55).encode(
        y=y, x=RATE_AXIS.copy(), yOffset=alt.YOffset("j:Q", scale=None),
        tooltip=[alt.Tooltip("bai:N", title="Bài dạy"), alt.Tooltip("cls:N", title="Lớp"),
                 alt.Tooltip("gv:N", title="Giáo viên"), alt.Tooltip("rate:Q", title=RATE, format=".1f")])
    return (box + dots).properties(height=32 * len(order) + 60)


def progress_col(label=RATE):
    return st.column_config.ProgressColumn(label, min_value=0, max_value=100, format="%.1f%%")


def view_toggle(key: str) -> str:
    """Chuyển giữa biểu đồ và bảng cho một khối xếp hạng."""
    return st.segmented_control("Hiển thị", ["Biểu đồ", "Bảng"], default="Biểu đồ", key=key,
                                label_visibility="collapsed", required=True)
