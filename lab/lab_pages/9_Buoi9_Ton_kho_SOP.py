import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from dpkit import baseline, inventory, smoothing
from lab_common import BRAND, CAT, INK, add_line, clean_series, fig_base, load_all, note, page, pick_series

page(9, "Từ dự báo đến tồn kho, cảnh báo sớm và S&OP",
     "Sai số dự báo biến thành tồn kho an toàn; tốc độ bán trong tháng biến thành cảnh báo sớm; nhu cầu chưa giới hạn gặp năng lực trong S&OP.")
D = load_all()
m = D["sku_master"].set_index("sku")
tab1, tab2, tab3, tab4 = st.tabs(["Safety Stock & ROP", "Cảnh báo sớm trong tháng", "Hạn sử dụng (FEFO)", "Năng lực & Volume→Value"])

with tab1:
    c1, c2, c3 = st.columns([2, 1, 1])
    with c1:
        key = pick_series(default="B01|GT")
    meth = c2.selectbox("Phương pháp dự báo", ["SES", "Holt tắt dần", "Seasonal Naive", "Holt-Winters nhân"], index=3)
    sl = c3.slider("Mức phục vụ", 0.80, 0.995, 0.95, 0.005)
    it = key.split("|")[0]
    y = clean_series(key, "demand_ex_event").values
    fn = {"SES": lambda yy, h: smoothing.ses(yy, h).forecast, "Holt tắt dần": lambda yy, h: smoothing.holt(yy, h, damped=True).forecast,
          "Seasonal Naive": lambda yy, h: baseline.seasonal_naive(yy, h), "Holt-Winters nhân": lambda yy, h: smoothing.holt_winters(yy, h, 12, "mul").forecast}[meth]
    errs = np.array([y[t] - fn(y[:t], 1)[0] for t in range(len(y) - 12, len(y))])
    sigma = float(np.sqrt(np.mean(errs ** 2)))
    sd = float(np.std(y[-12:], ddof=1))
    lt_w = st.slider("Lead time (tuần)", 1, 12, int(m.loc[it if it in m.index else "S06", "lead_time_weeks"]))
    L = lt_w / 4.33
    fc1 = float(fn(y, 1)[0])
    ss = inventory.safety_stock(sigma, L, sl)
    ss_bad = inventory.safety_stock(sd, L, sl)
    k = st.columns(5)
    k[0].metric("σ sai số (ngoài mẫu)", f"{sigma:,.0f}")
    k[1].metric("SD nhu cầu 12T", f"{sd:,.0f}")
    k[2].metric("Safety Stock (σ sai số)", f"{ss:,.0f}")
    k[3].metric("SS nếu dùng SD nhu cầu", f"{ss_bad:,.0f}", delta=f"{(ss_bad / ss - 1) * 100:+.0f}%", delta_color="inverse")
    k[4].metric("ROP", f"{fc1 * L + ss:,.0f}")
    cost = float(m.loc[it if it in m.index else "S06", "cost_k"])
    curve = inventory.service_tradeoff(sigma, L, cost, 0.20, levels=np.round(np.arange(0.80, 0.996, 0.005), 3))
    f = fig_base("Mức phục vụ ↔ vốn tồn kho an toàn", 340, "Vốn SS (triệu đ)")
    add_line(f, (curve.service_level * 100).round(1), curve.von_ton_kho_trieu, "Vốn SS", CAT[0], mode="lines")
    f.add_vline(x=sl * 100, line_dash="dash", line_color=INK)
    f.update_layout(xaxis_title="Mức phục vụ mục tiêu (%)")
    st.plotly_chart(f, use_container_width=True)
    note("SS = z × σ × √L. σ phải là sai số dự báo NGOÀI MẪU — phần kho thực sự phải đỡ. Dùng SD nhu cầu (gồm cả mùa vụ đã dự báo được) "
         "làm SS phình to, đặc biệt với hàng mùa vụ như B01. Mức phục vụ là quyết định kinh doanh (S&OP), không phải con số mặc định.")

with tab2:
    im = D["in_month_tracking"].copy()
    c1, c2 = st.columns(2)
    day = c1.slider("Đã qua bao nhiêu ngày của tháng 10", 7, 14, 14, help="Dữ liệu thực tế có đến ngày 14")
    thr = c2.slider("Ngưỡng cảnh báo ±", 0.05, 0.30, 0.15, 0.01)
    rows = []
    for r in im.itertuples():
        a = r.actual_day1_14 * day / 14
        al = inventory.run_rate_alert(a, day, 31, r.consensus_forecast_month, thr)
        rows.append({"Chuỗi": f"{r.sku}|{r.channel}", "Đồng thuận T10": r.consensus_forecast_month, "Bán đến nay": a,
                     "Tỷ lệ": al["run_rate_ratio"], "Ước cả tháng": al["projected_month"], "Cảnh báo": al["flag"]})
    t = pd.DataFrame(rows).sort_values("Tỷ lệ")
    f = fig_base("Tỷ lệ tốc độ bán / kỳ vọng", 420)
    colors = [CAT[4] if v > 1 + thr else (CAT[2] if v < 1 - thr else "#C9CCC9") for v in t["Tỷ lệ"]]
    f.add_trace(go.Bar(x=t["Chuỗi"], y=t["Tỷ lệ"], marker_color=colors))
    f.add_hrect(y0=1 - thr, y1=1 + thr, fillcolor="#EAF7EF", opacity=0.6, line_width=0)
    f.update_layout(showlegend=False, hovermode="closest")
    st.plotly_chart(f, use_container_width=True)
    st.dataframe(t[t["Cảnh báo"] != "Bình thường"].style.format({"Đồng thuận T10": "{:,.0f}", "Bán đến nay": "{:,.0f}", "Tỷ lệ": "{:.0%}", "Ước cả tháng": "{:,.0f}"}),
                 hide_index=True, use_container_width=True)
    note("Cảnh báo sớm không phải để sửa forecast ngay mà để <b>hỏi</b> trong 24 giờ: thời tiết? đối thủ? khuyến mãi chưa báo? → rồi quyết định "
         "điều chuyển kênh, đổi lệnh sản xuất, hay cập nhật forecast tháng sau. Mã nhỏ dao động ngẫu nhiên nhiều — đặt ngưỡng theo nhóm ABC.")

with tab3:
    inv = D["inventory_snapshot"]
    dc = D["demand_clean"]
    thr = st.slider("Kênh MT chỉ nhận hàng còn ≥ … hạn dùng", 0.5, 0.9, 0.67, 0.01)
    daily = (dc[dc.month >= "2026-07"].groupby("item").demand.sum() / 92).rename(index={"S06": "S06N"}).to_dict()
    risk = inventory.shelf_life_risk(inv, daily, thr)
    risk["Giá trị (tr.đ)"] = [r.qty * float(m.loc[r.sku, "cost_k"]) / 1000 for r in risk.itertuples()]
    st.metric("Giá trị tồn có rủi ro", f"{risk.loc[risk.rui_ro == 'CẢNH BÁO', 'Giá trị (tr.đ)'].sum():,.0f} triệu đ")
    st.dataframe(risk.rename(columns={"sku": "SKU", "batch": "Lô", "qty": "Số lượng", "remaining_days": "Ngày còn lại",
                                      "ngay_ban_het_luy_ke": "Ngày bán hết (lũy kế)", "ngay_con_ban_duoc": "Ngày còn bán được", "rui_ro": "Rủi ro"})
                 .style.format({"Số lượng": "{:,.0f}", "Ngày bán hết (lũy kế)": "{:,.0f}", "Ngày còn bán được": "{:,.0f}", "Giá trị (tr.đ)": "{:,.0f}"})
                 .map(lambda v: "color:#C2185B;font-weight:600" if v == "CẢNH BÁO" else "", subset=["Rủi ro"]),
                 hide_index=True, use_container_width=True, height=420)

with tab4:
    cap = D["capacity"]
    line = st.selectbox("Dây chuyền", cap.line.unique())
    members = {"Dây chuyền mì gói (N01,N02,N04,N05,N06)": ["N01", "N02", "N04", "N05"], "Dây chuyền mì ly (N03)": ["N03"],
               "Dây chuyền chiết rót nước chấm (S01,S02,S06N)": ["S01", "S02", "S06"]}[line]
    H = 6
    dem = np.zeros(H)
    for it in members:
        for ch in ("GT", "MT"):
            try:
                yy = clean_series(f"{it}|{ch}", "demand_ex_event").values
            except KeyError:
                continue
            if len(yy) == 0:
                continue
            fcst = smoothing.holt_winters(yy, H, 12, "mul").forecast if len(yy) >= 24 else smoothing.ses(yy, H).forecast
            dem += np.maximum(fcst, 0)
    cl = cap[cap.line == line].set_index("month")
    mos = [str(p) for p in pd.period_range("2026-10", periods=H, freq="M")]
    reg = cl.loc[mos, "regular_capacity"].values
    ot = cl.loc[mos, "overtime_capacity"].values
    f = fig_base(f"{line}: nhu cầu chưa giới hạn (thống kê) vs năng lực", 380)
    f.add_bar(x=mos, y=reg, name="Năng lực thường", marker_color="#C9CCC9")
    f.add_bar(x=mos, y=ot, name="Tăng ca", marker_color="#E6E8E6")
    add_line(f, mos, dem, "Nhu cầu chưa giới hạn", INK, mode="lines+markers")
    f.update_layout(barmode="stack")
    st.plotly_chart(f, use_container_width=True)
    gap = dem - reg - ot
    t = pd.DataFrame({"Tháng": mos, "Nhu cầu": dem, "Năng lực tối đa": reg + ot, "Thiếu (+)/dư (−)": gap})
    st.dataframe(t.style.format({c: "{:,.0f}" for c in t.columns if c != "Tháng"}), hide_index=True, use_container_width=True)
    price = float(m.loc[members[0], "price_k"])
    st.write(f"Doanh thu có rủi ro nếu không xử lý phần thiếu (giá {members[0]}): **{np.maximum(gap, 0).sum() * price / 1000:,.0f} triệu đ**")
    note("Chu kỳ S&OP 5 bước: thu thập dữ liệu → Demand Review → <b>Supply Review</b> (cửa sang Production Planning) → Pre-S&OP (phương án & đánh đổi) "
         "→ Executive S&OP (quyết định). Báo cáo luôn tách <b>nhu cầu chưa giới hạn</b> và <b>kế hoạch đã giới hạn</b>.")
