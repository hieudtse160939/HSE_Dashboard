import streamlit as st

import hse_charts as hc
import hse_data as hd
from hse_data import RATE

c = st.session_state.hse
L, low, high = c.L, c.low, c.high

tbl = c.by_class.copy()
if c.stu is not None:
    g = c.stu.groupby("Lớp")
    tbl["Số HS"] = tbl["Lớp"].map(g.size())
    tbl["HS chưa nộp bài nào"] = tbl["Lớp"].map(g["Đã nộp"].apply(lambda s: int((s == 0).sum())))

with st.container(border=True):
    with st.container(horizontal=True, vertical_alignment="center"):
        st.markdown("**Xếp hạng lớp theo tỷ lệ hoàn thành**")
        view = hc.view_toggle("cls_view")
    if view == "Biểu đồ":
        hc.show(hc.ranked_bar(c.by_class, "Lớp", low, high, ("Số bài",)))
    else:
        st.dataframe(tbl.sort_values(RATE, ascending=False), hide_index=True,
                     column_config={RATE: hc.progress_col(), "Bài dưới ngưỡng": f"Bài dưới {low}%"})

st.subheader("Chi tiết một lớp", icon=":material/search:")
cls = st.selectbox("Chọn lớp", sorted(c.by_class["Lớp"], key=hd.class_key), key="cls_detail")
row = c.by_class[c.by_class["Lớp"] == cls].iloc[0]
with st.container(horizontal=True):
    st.metric("Tỷ lệ hoàn thành", f"{row[RATE]:.1f}%", f"{row[RATE] - c.overall:+.1f} điểm",
              delta_description="so với chung", border=True)
    st.metric("Số bài dạy", int(row["Số bài"]), border=True)
    st.metric("Hạng", f"{int((c.by_class[RATE] > row[RATE]).sum()) + 1} / {len(c.by_class)}", border=True)
    if c.stu is not None:
        cs_all = c.stu[c.stu["Lớp"] == cls]
        st.metric("Học sinh chưa nộp bài nào", f"{int((cs_all['Đã nộp'] == 0).sum())} / {len(cs_all)}", border=True)

left, right = st.columns([3, 2])
with left.container(border=True, height="stretch"):
    st.markdown(f"**Theo môn — {cls}**")
    hc.show(hc.ranked_bar(c.by_cls_subj[c.by_cls_subj["Lớp"] == cls], "Môn", low, high, ("Giáo viên", "Số bài"), legend=False))
with right.container(border=True, height="stretch"):
    if c.stu is None:
        st.caption("File báo cáo không có dữ liệu học sinh.")
    else:
        cs = c.stu[(c.stu["Lớp"] == cls) & (c.stu[RATE] < low)].sort_values(RATE)
        st.markdown(f"**Học sinh dưới {low}%** · {len(cs)} học sinh")
        st.dataframe(cs[["Học sinh", "Bài giao", "Đã nộp", RATE, "Môn còn thiếu"]], hide_index=True,
                     height=360, column_config={RATE: hc.progress_col()})
