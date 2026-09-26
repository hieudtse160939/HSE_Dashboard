import pandas as pd
import streamlit as st

import hse_charts as hc
from hse_data import RATE, clean

c = st.session_state.hse
low = c.low

if c.stu is None:
    st.info("File báo cáo không có sheet dữ liệu học sinh (cần các cột Lớp, Học sinh, Môn, GVBM, "
            "Tong_Bai_Giao, Da_Nop).", icon=":material/info:")
    st.stop()

stu = c.stu
left, right = st.columns(2)
with left.container(border=True, height="stretch"):
    st.markdown("**Phân bố học sinh theo tỷ lệ nộp bài**")
    buckets = pd.cut(stu[RATE], bins=[-0.1, 0, 49.99, 79.99, 99.99, 100],
                     labels=["0%", "1–49%", "50–79%", "80–99%", "100%"])
    bd = buckets.value_counts(sort=False).rename_axis("Mức nộp bài").reset_index(name="Số học sinh")
    bd["Nhãn"] = bd["Số học sinh"].astype(str) + " (" + (bd["Số học sinh"] / len(stu) * 100).round(0).astype(int).astype(str) + "%)"
    hc.show(hc.count_bar(bd, "Mức nộp bài", "Số học sinh", label="Nhãn",
                         colors=["#86b6ef", "#5598e7", "#2a78d6", "#1c5cab", "#0d366b"]))
with right.container(border=True, height="stretch"):
    st.markdown("**Lớp có nhiều học sinh chưa nộp bài nào nhất**")
    z = stu.groupby("Lớp").agg(n=("Mã HS", "count"), zero=("Đã nộp", lambda s: int((s == 0).sum()))).reset_index()
    z["Tỷ lệ chưa nộp (%)"] = (z["zero"] / z["n"] * 100).round(1)
    z = z[z["zero"] > 0].sort_values("Tỷ lệ chưa nộp (%)", ascending=False).head(12)
    if z.empty:
        st.success("Không có học sinh nào chưa nộp bài.", icon=":material/check_circle:")
    else:
        z["Nhãn"] = z["Tỷ lệ chưa nộp (%)"].round(0).astype(int).astype(str) + "% · " + z["zero"].astype(str) + "/" + z["n"].astype(str)
        hc.show(hc.count_bar(z, "Lớp", "Tỷ lệ chưa nộp (%)", color=hc.STATUS[2], label="Nhãn", horizontal=True))

st.subheader("Tra cứu học sinh", icon=":material/person_search:")
with st.container(horizontal=True, vertical_alignment="bottom"):
    q = st.text_input("Tìm theo tên học sinh", type="search", placeholder="Nhập tên…", key="stu_q")
    only_low = st.toggle(f"Chỉ học sinh dưới {low}%", value=True, key="stu_low")
view = stu
if q:
    view = view[view["Học sinh"].str.contains(clean(q), case=False, regex=False)]
if only_low:
    view = view[view[RATE] < low]
st.caption(f"{len(view)} học sinh")
st.dataframe(view.sort_values([RATE, "Lớp"])[["Học sinh", "Lớp", "Số môn", "Bài giao", "Đã nộp", RATE, "Môn còn thiếu"]],
             hide_index=True, height=480, column_config={RATE: hc.progress_col()})
