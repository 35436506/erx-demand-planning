import numpy as np
import pandas as pd
import streamlit as st

from dpkit import hierarchy, metrics
from lab_common import BRAND, CAT, INK, add_line, fig_base, label, load_all, note, page, raw_series, series_keys

page(1, "Dự báo để làm gì & phân cấp dự báo",
     "Cùng một dữ liệu, nhìn ở cấp nào thì ổn định nhất? Và con người dự báo 'bằng mắt' tốt đến đâu so với cách đơn giản nhất?")
D = load_all()
tab1, tab2, tab3 = st.tabs(["CV theo cấp dự báo", "Trò chơi Forecast Challenge", "Chuỗi kế hoạch & vùng thời gian"])

with tab1:
    tbl = hierarchy.cv_by_level(D["sales_history"], "shipments", D["sku_master"])
    c1, c2 = st.columns([1, 1.4])
    with c1:
        st.dataframe(tbl.rename(columns={"cap": "Cấp", "so_chuoi": "Số chuỗi", "CV_trung_vi": "CV trung vị", "CV_trung_binh": "CV trung bình"})
                     .style.format({"CV trung vị": "{:.2f}", "CV trung bình": "{:.2f}"}), hide_index=True, use_container_width=True)
        note("CV = độ lệch chuẩn / trung bình. Gộp càng nhiều, sai lệch ngẫu nhiên càng bù trừ nhau (hiệu ứng danh mục, ≈ chia √n). "
             "→ Kế hoạch năng lực/ngân sách chốt ở cấp nhóm; MPS và giao hàng cần cấp SKU × kênh.")
    with c2:
        import plotly.graph_objects as go
        f = fig_base("CV trung vị theo cấp", 330)
        f.add_trace(go.Bar(x=tbl.cap, y=tbl.CV_trung_vi, marker_color=BRAND, text=[f"{v:.2f}" for v in tbl.CV_trung_vi], textposition="outside"))
        f.update_layout(showlegend=False, hovermode="closest")
        st.plotly_chart(f, use_container_width=True)
    h = D["sales_history"].merge(D["sku_master"][["sku", "category", "planning_item"]], on="sku")
    cats_ = sorted(h.category.unique())
    cat = st.selectbox("Xem một nhóm hàng", cats_, index=cats_.index("Mì ăn liền"))
    g = h[h.category == cat]
    f = fig_base(f"{cat}: từng SKU × kênh vs tổng nhóm (chuẩn hóa về trung bình = 1)", 380)
    for i, ((it, ch), x) in enumerate(g.groupby(["planning_item", "channel"])):
        s = x.groupby("month").shipments.sum()
        add_line(f, s.index, (s / s.mean()).values, f"{it}|{ch}", color="#C9CCC9", width=1)
    tot = g.groupby("month").shipments.sum()
    add_line(f, tot.index, (tot / tot.mean()).values, "Tổng nhóm", color=INK, width=3)
    st.plotly_chart(f, use_container_width=True)

with tab2:
    st.markdown("**Luật chơi:** nhìn 24 tháng đầu, đoán 3 tháng tiếp theo. Sau khi nộp, Lab so điểm của bạn với cách *Naive* (lấy tháng cuối).")
    opts = ["N02|GT", "S03|MT", "B02|GT", "K01|MT", "N04|GT", "S05|MT"]
    if "fc_round" not in st.session_state:
        st.session_state.fc_round = 0
    key = opts[st.session_state.fc_round % len(opts)]
    s = raw_series(key).dropna()
    hist, fut = s.iloc[:24], s.iloc[24:27]
    st.caption(f"Vòng {st.session_state.fc_round + 1}: một chuỗi ẩn danh (mở tên sau khi nộp)")
    f = fig_base("24 tháng lịch sử", 320)
    add_line(f, hist.index, hist.values, "Lịch sử", INK, mode="lines+markers")
    st.plotly_chart(f, use_container_width=True)
    with st.form(f"guess_{st.session_state.fc_round}"):
        cols = st.columns(3)
        guesses = [cols[i].number_input(f"Đoán {fut.index[i]}", min_value=0, value=int(hist.iloc[-1]), step=100) for i in range(3)]
        sub = st.form_submit_button("Nộp dự đoán")
    if sub:
        naive = np.repeat(hist.iloc[-1], 3)
        you = metrics.wmape(fut.values, np.array(guesses))
        nv = metrics.wmape(fut.values, naive)
        c1, c2, c3 = st.columns(3)
        c1.metric("WMAPE của bạn", f"{you:.1f}%")
        c2.metric("WMAPE Naive", f"{nv:.1f}%")
        c3.metric("Kết quả", "Hòa — bạn chưa thêm giá trị" if abs(you - nv) < 0.05 else ("Bạn thắng!" if you < nv else "Naive thắng"), delta=f"{nv - you:+.1f} điểm %")
        f = fig_base(f"Đáp án: {label(key)}", 320)
        add_line(f, s.index[:27], s.values[:27], "Thực tế", INK, mode="lines+markers")
        add_line(f, fut.index, guesses, "Bạn đoán", CAT[2], mode="lines+markers")
        add_line(f, fut.index, naive, "Naive", CAT[0], dash="dot")
        st.plotly_chart(f, use_container_width=True)
        note("Thường gặp: con người phản ứng quá mạnh với tháng cuối (đuổi theo nhiễu) hoặc 'thấy' xu hướng không có thật. "
             "Đó là lý do mọi phương pháp phải được so với mốc Naive — và mọi lần chỉnh tay phải đo FVA (Buổi 8).")
    if st.button("Vòng tiếp theo ▶"):
        st.session_state.fc_round += 1
        st.rerun()

with tab3:
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("#### Dự báo dùng cho quyết định nào?")
        st.dataframe(pd.DataFrame([
            ["Tuần (1–8 tuần)", "SKU × kho × tuần", "Bổ sung hàng, điều xe, lịch giao", "Kho vận, Sales Ops"],
            ["Tháng (3–18 tháng)", "SKU × kênh × tháng", "S&OP, MPS, mua NVL, tồn kho", "Demand/Supply Planning, Sản xuất, Mua hàng"],
            ["Năm (1–3 năm)", "Nhóm hàng × tháng (giá trị)", "Ngân sách, năng lực, đầu tư", "Tài chính, Ban lãnh đạo"],
        ], columns=["Tầm", "Cấp chi tiết", "Quyết định", "Người dùng"]), hide_index=True, use_container_width=True)
        st.markdown("#### Bốn khái niệm hay bị trộn lẫn")
        st.dataframe(pd.DataFrame([
            ["Nhu cầu (demand)", "Khách muốn mua bao nhiêu — kể cả phần không mua được vì hết hàng"],
            ["Dự báo (forecast)", "Ước lượng không thiên lệch về nhu cầu tương lai, kèm sai số"],
            ["Kế hoạch (plan)", "Ta QUYẾT ĐỊNH làm/mua/giao bao nhiêu (có giới hạn năng lực, tồn kho)"],
            ["Mục tiêu (target)", "Con số ta MUỐN đạt — dùng để động viên, không dùng để đặt hàng"],
        ], columns=["Khái niệm", "Nghĩa"]), hide_index=True, use_container_width=True)
    with c2:
        st.markdown("#### Vùng thời gian của kế hoạch (time fences)")
        import plotly.graph_objects as go
        f = fig_base("", 230)
        for x0, x1, nm, colr in [(0, 1, "Đóng băng (frozen) · tháng M+1", "#1F2421"), (1, 3, "Bán linh hoạt (slushy) · M+2–M+3", "#76777B"),
                                 (3, 12, "Linh hoạt (liquid) · M+4 trở đi", "#01AE42")]:
            f.add_trace(go.Bar(x=[x1 - x0], y=["Kế hoạch"], base=[x0], orientation="h", name=nm, marker_color=colr, hovertemplate=nm))
        f.update_layout(barmode="stack", xaxis=dict(title="Tháng tính từ hôm nay", dtick=1), hovermode="closest")
        st.plotly_chart(f, use_container_width=True)
        note("Chuỗi kế hoạch: <b>Dự báo nhu cầu → S&OP → MPS → MRP</b>. Buổi 10 bàn giao số nhu cầu đồng thuận CHƯA giới hạn năng lực "
             "cho module Production Planning. Sửa số trong vùng đóng băng = đổi lịch sản xuất đã chốt → phải có quy trình duyệt.")
