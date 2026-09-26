import streamlit as st

import hse_charts as hc
from hse_data import RATE, clean

c = st.session_state.hse
L, low = c.L, c.low

with st.container(horizontal=True, vertical_alignment="bottom"):
    q = st.text_input("Tìm theo tên bài dạy", type="search", placeholder="VD: ôn tập, giữa kỳ…", key="lesson_q")
    only_low = st.toggle(f"Chỉ bài dưới {low}%", value=False, key="lesson_low")
view = L
if q:
    view = view[view["Bài dạy"].str.contains(clean(q), case=False, regex=False)]
if only_low:
    view = view[view[RATE] < low]
st.caption(f"{len(view)} bài dạy · sắp xếp từ thấp đến cao")
st.dataframe(view.sort_values(RATE)[["Bài dạy", "Lớp", "Môn", "Giáo viên", "Lượt giao", "Hoàn thành", RATE]],
             hide_index=True, height=600,
             column_config={RATE: hc.progress_col(), "Bài dạy": st.column_config.TextColumn(pinned=True)})
