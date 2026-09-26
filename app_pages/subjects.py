import streamlit as st

import hse_charts as hc
import hse_data as hd
from hse_data import RATE

c = st.session_state.hse
L, low, high = c.L, c.low, c.high
order = c.by_subject.sort_values(RATE, ascending=False)["Môn"].tolist()

left, right = st.columns(2)
with left.container(border=True, height="stretch"):
    with st.container(horizontal=True, vertical_alignment="center"):
        st.markdown("**Tỷ lệ hoàn thành theo môn**")
        view = hc.view_toggle("subj_view")
    if view == "Biểu đồ":
        hc.show(hc.ranked_bar(c.by_subject, "Môn", low, high, ("Số bài",)))
    else:
        st.dataframe(c.by_subject.sort_values(RATE, ascending=False), hide_index=True,
                     column_config={RATE: hc.progress_col(), "Bài dưới ngưỡng": f"Bài dưới {low}%"})
with right.container(border=True, height="stretch"):
    st.markdown("**Độ phân tán giữa các bài dạy**")
    st.caption("Mỗi chấm là một bài dạy; hộp là khoảng giữa 50% số bài, vạch đậm là trung vị.")
    hc.show(hc.spread(L, order))

with st.container(border=True):
    st.markdown("**Khối × môn**")
    d = c.by_cls_subj.groupby(["Khối", "Môn"], as_index=False)[["Hoàn thành", "Lượt giao"]].sum()
    d[RATE] = hd.rate(d["Hoàn thành"], d["Lượt giao"])
    rows = sorted(d["Khối"].unique(), key=hd.grade_key)
    hc.show(hc.heatmap(d, "Khối", "Môn", rows, order, cell=34))
