import streamlit as st

import hse_charts as hc
import hse_data as hd
from hse_data import RATE

c = st.session_state.hse
L, low, high = c.L, c.low, c.high
cols = ["Giáo viên", "Môn dạy", "Số lớp", "Số bài", "Lượt giao", "Hoàn thành", RATE, "Bài dưới ngưỡng"]

with st.container(border=True):
    with st.container(horizontal=True, vertical_alignment="center"):
        st.markdown("**Xếp hạng giáo viên theo tỷ lệ hoàn thành**")
        view = hc.view_toggle("gv_view")
    if view == "Biểu đồ":
        hc.show(hc.ranked_bar(c.by_teacher, "Giáo viên", low, high, ("Môn dạy", "Số bài")))
    else:
        st.dataframe(c.by_teacher[cols].sort_values(RATE, ascending=False), hide_index=True, column_config={
            RATE: hc.progress_col(),
            "Bài dưới ngưỡng": st.column_config.NumberColumn(
                f"Bài dưới {low}%", help="Số bài dạy có tỷ lệ hoàn thành dưới ngưỡng cảnh báo")})

st.subheader("Chi tiết một giáo viên", icon=":material/search:")
gv = st.selectbox("Chọn giáo viên", sorted(c.by_teacher["Giáo viên"]), key="gv_detail")
row = c.by_teacher[c.by_teacher["Giáo viên"] == gv].iloc[0]
with st.container(horizontal=True):
    st.metric("Tỷ lệ hoàn thành", f"{row[RATE]:.1f}%", f"{row[RATE] - c.overall:+.1f} điểm",
              delta_description="so với chung", border=True)
    st.metric("Môn dạy", row["Môn dạy"], border=True)
    st.metric("Số lớp / số bài", f"{int(row['Số lớp'])} / {int(row['Số bài'])}", border=True)
    st.metric(f"Bài dưới {low}%", int(row["Bài dưới ngưỡng"]), border=True)

mine = L[L["Giáo viên"] == gv]
multi = mine["Môn"].nunique() > 1
left, right = st.columns([2, 3])
with left.container(border=True, height="stretch"):
    if multi:  # GV dạy nhiều môn -> tách theo lớp × môn
        st.markdown("**Theo lớp và môn**")
        by = hd.summarize(mine, ["Lớp", "Môn"])
        by["Lớp · Môn"] = by["Lớp"] + " · " + by["Môn"]
        hc.show(hc.ranked_bar(by, "Lớp · Môn", low, high, ("Số bài",), legend=False))
    else:
        st.markdown("**Theo lớp**")
        hc.show(hc.ranked_bar(hd.summarize(mine, ["Lớp"]), "Lớp", low, high, ("Số bài",), legend=False))
with right.container(border=True, height="stretch"):
    st.markdown(f"**Danh sách bài dạy** · {len(mine)} bài")
    st.dataframe(mine[["Lớp", "Môn", "Bài dạy", "Lượt giao", "Hoàn thành", RATE]].sort_values(RATE),
                 hide_index=True, height=360, column_config={RATE: hc.progress_col()})

if c.assign is not None and not c.sel_teachers:
    st.subheader("Có phân công nhưng chưa có bài trong báo cáo", icon=":material/person_alert:")
    a = c.assign[c.assign["Môn"].isin(set(c.lessons["Môn"]))]
    if c.sel_grades:
        a = a[a["Lớp"].map(hd.grade_of).isin(c.sel_grades)]
    if c.sel_classes:
        a = a[a["Lớp"].isin(c.sel_classes)]
    if c.sel_subjects:
        a = a[a["Môn"].isin(c.sel_subjects)]
    a = a[~a["Giáo viên"].str.casefold().isin(set(c.lessons["Giáo viên"].str.casefold()))]
    if a.empty:
        st.success("Tất cả giáo viên được phân công (trong phạm vi lọc) đều đã có bài giao.",
                   icon=":material/check_circle:")
    else:
        miss = a.groupby("Giáo viên", as_index=False).agg(
            **{"Môn": ("Môn", lambda s: ", ".join(sorted(s.unique()))),
               "Số lớp phân công": ("Lớp", "nunique"),
               "Các lớp": ("Lớp", lambda s: ", ".join(sorted(s.unique(), key=hd.class_key)))})
        st.caption(f"{len(miss)} giáo viên · chỉ tính các môn có trong báo cáo HSE · đối chiếu theo tên giáo viên.")
        st.dataframe(miss.sort_values("Số lớp phân công", ascending=False), hide_index=True)
