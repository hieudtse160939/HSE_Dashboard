import pandas as pd
import streamlit as st

import hse_charts as hc
import hse_data as hd
from hse_data import RATE

c = st.session_state.hse
L, low, high = c.L, c.low, c.high


def fmt(n) -> str:
    return f"{int(n):,}".replace(",", ".")


with st.container(horizontal=True):
    st.metric("Tỷ lệ hoàn thành chung", f"{c.overall:.1f}%", border=True, icon=":material/task_alt:",
              help="Tổng lượt hoàn thành ÷ tổng lượt giao bài (có trọng số theo sĩ số).")
    st.metric("Lượt giao bài", fmt(L["Lượt giao"].sum()), border=True, icon=":material/assignment:",
              help="Tổng (sĩ số × số bài) được giao.")
    st.metric("Lượt hoàn thành", fmt(L["Hoàn thành"].sum()), border=True, icon=":material/done_all:")
    st.metric(f"Bài dạy dưới {low}%", f"{int(L['_low'].sum())} / {len(L)}", border=True,
              icon=":material/warning:", help="Số bài dạy có tỷ lệ hoàn thành thấp hơn ngưỡng cảnh báo.")

if c.stu is not None:
    n = len(c.stu)
    zero, full = int((c.stu["Đã nộp"] == 0).sum()), int((c.stu[RATE] >= 100).sum())
    with st.container(horizontal=True):
        st.metric("Học sinh", fmt(n), border=True, icon=":material/groups:")
        st.metric("Tỷ lệ nộp TB mỗi học sinh", f"{c.stu[RATE].mean():.1f}%", border=True,
                  icon=":material/person_check:",
                  help="Trung bình tỷ lệ nộp bài của từng học sinh (mỗi học sinh có trọng số như nhau).")
        st.metric("Hoàn thành 100%", f"{full} ({full / n * 100:.0f}%)", border=True, icon=":material/star:")
        st.metric("Chưa nộp bài nào", f"{zero} ({zero / n * 100:.0f}%)", border=True,
                  icon=":material/person_off:")


def ranking(df: pd.DataFrame, cat: str, n=3):
    d = df[df["Lượt giao"] > 0].sort_values(RATE, ascending=False)
    top = "\n".join(f"- {r[cat]} :green-badge[{r[RATE]:.1f}%]" for _, r in d.head(n).iterrows())
    bottom = "\n".join(f"- {r[cat]} :red-badge[{r[RATE]:.1f}%]" for _, r in d.tail(n).iloc[::-1].iterrows())
    return top, bottom


st.subheader("Nổi bật", icon=":material/insights:")
for col, (df, cat, icon) in zip(st.columns(3), ((c.by_class, "Lớp", ":material/meeting_room:"),
                                                (c.by_teacher, "Giáo viên", ":material/person:"),
                                                (c.by_subject, "Môn", ":material/menu_book:"))):
    top, bottom = ranking(df, cat)
    with col.container(border=True, height="stretch"):
        st.markdown(f"**{icon} {cat}**")
        st.caption("Cao nhất")
        st.markdown(top)
        st.caption("Thấp nhất")
        st.markdown(bottom)

left, right = st.columns(2)
with left.container(border=True, height="stretch"):
    st.markdown("**Tỷ lệ hoàn thành theo khối**")
    hc.show(hc.grade_bar(c.by_grade.sort_values("Khối", key=lambda s: s.map(hd.grade_key)), low, high))
with right.container(border=True, height="stretch"):
    st.markdown("**Phân bố tỷ lệ hoàn thành của các bài dạy**")
    labels = ["0–10", "10–20", "20–30", "30–40", "40–50", "50–60", "60–70", "70–80", "80–90", "90–99", "100"]
    bins = pd.cut(L[RATE], bins=[-0.1, 10, 20, 30, 40, 50, 60, 70, 80, 90, 99.9, 100], labels=labels)
    dist = bins.value_counts(sort=False).rename_axis("Khoảng (%)").reset_index(name="Số bài dạy")
    hc.show(hc.count_bar(dist, "Khoảng (%)", "Số bài dạy"))

with st.container(border=True):
    st.markdown("**Bản đồ nhiệt lớp × môn**")
    st.caption("Tỷ lệ hoàn thành (%) của từng lớp theo môn. Ô trống: không có bài giao.")
    d = c.by_cls_subj
    rows = sorted(d["Lớp"].unique(), key=hd.class_key)
    cols = d.groupby("Môn").size().sort_values(ascending=False).index
    hc.show(hc.heatmap(d, "Lớp", "Môn", rows, cols))
