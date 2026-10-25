import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from dpkit import metrics, seasonal, smoothing
from lab_common import BRAND, CAT, INK, TEST_MONTHS, add_line, clean_series, fig_base, load_all, metric_table, note, page, pick_series, shade_test

page(5, "Mùa vụ & hiệu ứng Tết âm lịch",
     "Chỉ số mùa vụ, Holt-Winters cộng/nhân, và công cụ phân bổ lại nhu cầu khi Tết rơi vào tháng khác năm trước.")
D = load_all()
cal = D["calendar"]
tab1, tab2, tab3 = st.tabs(["Chỉ số mùa vụ & phân rã", "Holt-Winters", "Tết dịch tháng"])

with tab1:
    c1, c2 = st.columns([2, 1])
    with c1:
        key = pick_series(default="B01|GT", key="s5a")
    with c2:
        ex = st.toggle("Loại sự kiện một lần trước khi tính", value=True, help="Dùng cột demand_ex_event (ví dụ S01|GT 06/2024)")
    y = clean_series(key, "demand_ex_event" if ex else "demand")
    mul = seasonal.seasonal_indices(y.values, y.index.month, model="mul")
    cma = seasonal.centered_ma(y.values)
    fig = make_subplots(rows=1, cols=2, column_widths=[0.62, 0.38], subplot_titles=("Thực tế và trung bình trượt trung tâm 2×12", "Chỉ số mùa vụ (TB = 1)"))
    fig.add_trace(go.Scatter(x=[str(v) for v in y.index], y=y.values, name="Thực tế", line=dict(color=INK)), 1, 1)
    fig.add_trace(go.Scatter(x=[str(v) for v in y.index], y=cma, name="CMA 2×12 (xu hướng-chu kỳ)", line=dict(color=CAT[0], width=3)), 1, 1)
    fig.add_trace(go.Bar(x=[f"T{k}" for k in range(1, 13)], y=mul.values, marker_color=[BRAND if v >= 1 else "#C9CCC9" for v in mul.values],
                         name="Chỉ số", text=[f"{v:.2f}" for v in mul.values], textposition="outside"), 1, 2)
    fig.update_layout(template="plotly_white", height=400, legend=dict(orientation="h", y=-0.15), margin=dict(t=50, l=10, r=10, b=10))
    st.plotly_chart(fig, use_container_width=True)
    st.write(f"Biên độ mùa vụ (max/min): **{mul.max() / mul.min():.2f}×**")
    note("Biên độ mùa vụ phình theo mức bán (mùa hè B01) → mùa vụ <b>nhân</b>. Biên độ gần như không đổi → <b>cộng</b>. "
         "Bật/tắt nút loại sự kiện với S01|GT để thấy một tin đồn tháng 6/2024 có thể 'tạo ra' một mùa vụ giả.")

with tab2:
    key = pick_series(default="B01|GT", key="s5b")
    y = clean_series(key, "demand_ex_event")
    tr, te = y.values[:-TEST_MONTHS], y.values[-TEST_MONTHS:]
    try:
        hm = smoothing.holt_winters(tr, TEST_MONTHS, 12, "mul")
        ha = smoothing.holt_winters(tr, TEST_MONTHS, 12, "add")
        sn = np.array([tr[len(tr) - 12 + i % 12] for i in range(TEST_MONTHS)])
        f = fig_base(f"{key}: Holt-Winters vs Seasonal Naive", 400)
        add_line(f, y.index, y.values, "Thực tế", INK)
        add_line(f, y.index[:len(tr)], hm.fitted, "HW nhân (khớp)", CAT[0], width=1)
        add_line(f, y.index[-TEST_MONTHS:], hm.forecast, "HW nhân", CAT[0], mode="lines+markers")
        add_line(f, y.index[-TEST_MONTHS:], ha.forecast, "HW cộng", CAT[1], mode="lines+markers")
        add_line(f, y.index[-TEST_MONTHS:], sn, "Seasonal Naive", CAT[2], dash="dot")
        shade_test(f, y.index)
        st.plotly_chart(f, use_container_width=True)
        rows = [{"Phương pháp": "HW nhân", **metrics.summary(te, hm.forecast, tr, 12)},
                {"Phương pháp": "HW cộng", **metrics.summary(te, ha.forecast, tr, 12)},
                {"Phương pháp": "Seasonal Naive", **metrics.summary(te, sn, tr, 12)}]
        st.dataframe(metric_table(rows), hide_index=True, use_container_width=True)
        st.caption("Tham số HW nhân: " + ", ".join(f"{k}={v:.3f}" for k, v in hm.params.items() if k != "m"))
        note("Excel 365: <code>FORECAST.ETS</code> là Holt-Winters tự động (Microsoft dùng biến thể AAA). Hiểu cách nó cập nhật L, T, S giúp "
             "bạn giải thích con số phần mềm đưa ra thay vì chỉ chép lại.")
    except ValueError as e:
        st.warning(str(e))

with tab3:
    st.markdown("**Ý tưởng:** cửa sổ mua sắm Tết ≈ 35 ngày trước Tết. Năm nào Tết sớm, phần lớn cửa sổ rơi vào tháng 12–1; Tết muộn thì sang tháng 2.")
    c = cal.set_index("month")
    tet = pd.DataFrame([{"Năm": y_, "Ngày Tết": d, "T12": c.loc[f"{y_-1}-12", "tet_pre_share"], "T1": c.loc[f"{y_}-01", "tet_pre_share"],
                         "T2": c.loc[f"{y_}-02", "tet_pre_share"]} for y_, d in [(2024, "10/02"), (2025, "29/01"), (2026, "17/02"), (2027, "06/02")]])
    c1, c2 = st.columns([1, 1.3])
    with c1:
        st.dataframe(tet.style.format({"T12": "{:.0%}", "T1": "{:.0%}", "T2": "{:.0%}"}), hide_index=True, use_container_width=True)
        key = pick_series("Chuỗi nhạy Tết", "S01|GT", key="s5c", options=["S01|GT", "S01|MT", "S02|GT", "S04|GT", "B04|GT", "B04|MT", "K01|MT"])
        g = st.slider("Tăng trưởng mức thường 2027 so với 2026", -0.10, 0.15, 0.03, 0.01, format="%.2f")
        dip = st.slider("Mức sụt cho phần ngày sau Tết", 0.0, 0.4, 0.15, 0.05)
    y = clean_series(key, "demand_ex_event")
    tp = seasonal.tet_part_ratio(y, cal)
    R = float(tp.phan_Tet.mean())
    normal = float(tp.muc_thuong.iloc[-1]) * (1 + g)
    fc = seasonal.tet_reallocate(normal, R, cal, ["2026-12", "2027-01", "2027-02"], dip)
    naive = {mo: float(y[pd.Period(f"{int(mo[:4]) - 1}{mo[4:]}", "M")]) * (1 + g) for mo in fc}
    with c2:
        st.dataframe(tp.rename(columns={"nam": "Năm", "T12_T1_T2": "T12+T1+T2", "muc_thuong": "Mức thường", "phan_Tet": "Phần Tết (tháng-thường)"})
                     .style.format({"T12+T1+T2": "{:,.0f}", "Mức thường": "{:,.0f}", "Phần Tết (tháng-thường)": "{:.2f}"}), hide_index=True, use_container_width=True)
        f = fig_base(f"{key}: T12/2026–T2/2027", 320)
        f.add_trace(go.Bar(x=list(fc), y=list(naive.values()), name="Cùng kỳ năm trước × (1+g)", marker_color="#C9CCC9"))
        f.add_trace(go.Bar(x=list(fc), y=list(fc.values()), name="Theo lịch Tết 2027", marker_color=CAT[0]))
        f.update_layout(barmode="group", hovermode="x")
        st.plotly_chart(f, use_container_width=True)
    diff = {k: fc[k] - naive[k] for k in fc}
    st.write("Chênh lệch (lịch Tết − cùng kỳ): " + " · ".join(f"**{k}: {v:+,.0f}**" for k, v in diff.items()))
    note(f"Phần Tết trung bình = <b>{R:.2f}</b> tháng-thường. Công thức: Dự báo = Mức thường × (1 + R × tỷ trọng trước Tết) × (1 − sụt × tỷ trọng sau Tết). "
         "Tình huống thảo luận: 'Tết sớm 3 tuần, Sales báo tháng 1 gấp đôi' — số liệu ủng hộ đến đâu?")
