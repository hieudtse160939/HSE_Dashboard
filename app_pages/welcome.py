import streamlit as st

st.title("HSE Dashboard", icon=":material/monitoring:")
st.caption("Phân tích tỷ lệ hoàn thành bài giao theo lớp, giáo viên, môn học và học sinh.")

with st.container(border=True):
    st.subheader("Bắt đầu", icon=":material/upload_file:")
    st.markdown(
        "1. Xuất báo cáo **Bao_Cao_HSE_Phan_Hoi_Chi_Tiet** (.xlsx) từ hệ thống HSE.\n"
        "2. Tải file lên ở ô **Báo cáo HSE** trong thanh bên trái.\n"
        "3. Dùng bộ lọc để xem theo khối, lớp, môn hoặc giáo viên; tải báo cáo Excel đã lọc khi cần."
    )
    if st.session_state.get("sample_available"):
        if st.button("Xem thử với dữ liệu mẫu", icon=":material/play_arrow:", type="primary"):
            st.session_state.use_sample = True
            st.rerun()
