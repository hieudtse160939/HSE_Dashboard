import streamlit as st

import hse_charts as hc
import hse_data as hd
from hse_data import RATE, SCORE

c = st.session_state.hse
L, low, high = c.L, c.low, c.high
cols = ["Giáo viên", "Môn dạy", "Số lớp", "Số bài", "Lượt giao", "Hoàn thành", RATE, SCORE, "Bài dưới ngưỡng"]
extra = [col for col in ("Môn phân công", "Chủ nhiệm / vai trò") if col in c.by_teacher.columns]
cols += extra

with st.container(border=True):
    with st.container(horizontal=True, vertical_alignment="center"):
        st.markdown("**Xếp hạng giáo viên**")
        view = hc.view_toggle("gv_view")
    st.caption("Xếp theo điểm tổng hợp: 50% tỷ lệ hoàn thành + 50% khối lượng giao bài "
               "(lượt giao so với giáo viên giao nhiều nhất).")
    if view == "Biểu đồ":
        hc.show(hc.ranked_bar(c.by_teacher, "Giáo viên", low, high, ("Môn dạy", "Số bài", *extra), sort_by=SCORE))
    else:
        st.dataframe(c.by_teacher[cols].sort_values(SCORE, ascending=False), hide_index=True, column_config={
            RATE: hc.progress_col(),
            SCORE: st.column_config.NumberColumn(
                SCORE, format="%.1f", help="50% tỷ lệ hoàn thành + 50% khối lượng giao bài (thang 0–100)"),
            "Bài dưới ngưỡng": st.column_config.NumberColumn(
                f"Bài dưới {low}%", help="Số bài dạy có tỷ lệ hoàn thành dưới ngưỡng cảnh báo")})

st.subheader("Chi tiết một giáo viên", icon=":material/search:")
gv = st.selectbox("Chọn giáo viên", sorted(c.by_teacher["Giáo viên"]), key="gv_detail")
row = c.by_teacher[c.by_teacher["Giáo viên"] == gv].iloc[0]
with st.container(horizontal=True):
    st.metric("Tỷ lệ hoàn thành", f"{row[RATE]:.1f}%", f"{row[RATE] - c.overall:+.1f} điểm",
              delta_description="so với chung", border=True)
    st.metric("Môn dạy", row["Môn dạy"], border=True,
              help=f"Môn phân công: {row['Môn phân công']}" if row.get("Môn phân công") else None)
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

if c.assign is not None:
    # Giáo viên trên HSE không tìm thấy trong danh sách năm học (khác tên, trùng tên chưa có trong
    # danh sách, hoặc bài gắn nhầm môn)
    listed = set(c.assign["Giáo viên"])
    unknown = c.by_teacher[~c.by_teacher["Giáo viên"].isin(listed)]
    if not unknown.empty:
        st.subheader("Giáo viên trên HSE chưa có trong danh sách", icon=":material/rule:")
        same = c.assign.groupby(c.assign["Tên"].str.casefold())["Giáo viên"].agg(lambda s: ", ".join(dict.fromkeys(s)))
        base = unknown["Giáo viên"].str.replace(r" \([^)]*\)$", "", regex=True).str.casefold()
        unknown = unknown.assign(**{"Người cùng tên trong danh sách": base.map(same).fillna("")})
        st.caption("Có thể là giáo viên trùng tên chưa có trong danh sách, tên viết khác, hoặc bài gắn nhầm môn "
                   "trên HSE. Giáo viên trùng tên được tách riêng theo môn.")
        st.dataframe(unknown[["Giáo viên", "Môn dạy", "Số bài", RATE, "Người cùng tên trong danh sách"]],
                     hide_index=True, column_config={RATE: hc.progress_col()})

if c.assign is not None and not c.sel_teachers:
    st.subheader("Có phân công nhưng chưa có bài trong báo cáo", icon=":material/person_alert:")
    roster = c.assign.attrs.get("kind") == "roster"  # danh sách GV: không có phân công theo lớp
    a = c.assign[c.assign["Môn"].isin(set(c.lessons["Môn"]))]
    if c.sel_grades and not roster:
        a = a[a["Lớp"].map(hd.grade_of).isin(c.sel_grades)]
    if c.sel_classes and not roster:
        a = a[a["Lớp"].isin(c.sel_classes)]
    if c.sel_subjects:
        a = a[a["Môn"].isin(c.sel_subjects)]
    a = a[~a["Giáo viên"].str.casefold().isin(set(c.lessons["Giáo viên"].str.casefold()))]
    if a.empty:
        st.success("Tất cả giáo viên được phân công (trong phạm vi lọc) đều đã có bài giao.",
                   icon=":material/check_circle:")
    else:
        if roster:
            mine = c.assign[c.assign["Giáo viên"].isin(set(a["Giáo viên"]))]
            miss = mine.groupby("Giáo viên", as_index=False).agg(
                **{"Môn phân công": ("Môn", lambda s: ", ".join(dict.fromkeys(s))),
                   "Chủ nhiệm / vai trò": ("Chủ nhiệm / vai trò", "first")})
            note = "khối/lớp không áp dụng vì danh sách giáo viên không ghi lớp giảng dạy"
        else:
            miss = a.groupby("Giáo viên", as_index=False).agg(
                **{"Môn": ("Môn", lambda s: ", ".join(sorted(s.unique()))),
                   "Số lớp phân công": ("Lớp", "nunique"),
                   "Các lớp": ("Lớp", lambda s: ", ".join(sorted(s.unique(), key=hd.class_key)))})
            note = "đối chiếu theo tên giáo viên"
        st.caption(f"{len(miss)} giáo viên · chỉ tính các môn có trong báo cáo HSE · {note}.")
        st.dataframe(miss.sort_values("Giáo viên"), hide_index=True)
