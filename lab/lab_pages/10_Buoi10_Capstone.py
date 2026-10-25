import io

import numpy as np
import pandas as pd
import streamlit as st

from dpkit import baseline, evaluation, intermittent, inventory, seasonal, smoothing
from lab_common import CAT, INK, TEST_MONTHS, add_line, clean_series, fig_base, load_all, metric_table, note, page, shade_test

page(10, "Capstone workbench — chạy trọn một chu kỳ dự báo tháng",
     "Chọn portfolio (P1–P6) hoặc tải dữ liệu của bạn → chọn mô hình ngoài mẫu → điều chỉnh có giả định → Safety Stock → xuất file bàn giao cho Production Planning.")
D = load_all()
cal = D["calendar"]
PORT = {
    "P0 (bài mẫu)": ["N01|GT", "N03|GT", "S01|GT", "B01|GT", "S05|GT", "K01|MT"],
    "P1": ["N01|GT", "N03|MT", "S01|GT", "B01|MT", "K01|MT", "H01|GT"],
    "P2": ["N02|GT", "N03|GT", "S02|GT", "B02|GT", "K02|MT", "H02|GT"],
    "P3": ["N01|MT", "N04|GT", "S04|GT", "B03|MT", "S03|MT", "K04|MT"],
    "P4": ["N02|MT", "S01|MT", "S06|GT", "B01|GT", "B05|MT", "H03|GT"],
    "P5": ["N03|GT", "S04|MT", "S05|GT", "B02|MT", "K03|GT", "K02|GT"],
    "P6": ["N05|GT", "N01|GT", "S02|MT", "B04|GT", "S03|GT", "H01|GT"],
}
FUT = pd.period_range("2026-10", "2027-09", freq="M")

src = st.radio("Nguồn dữ liệu", ["Portfolio của lớp", "Dữ liệu của tôi (CSV)"], horizontal=True)
series = {}
if src == "Portfolio của lớp":
    p = st.selectbox("Portfolio", list(PORT), index=1)
    for k in PORT[p]:
        series[k] = clean_series(k, "demand_ex_event")
else:
    st.markdown("CSV gồm 3 cột: `month` (YYYY-MM), `series` (tên chuỗi), `demand` (số). Tối thiểu 24 tháng. "
                "**Chỉ tải dữ liệu đã ẩn danh** (đổi tên thành mã, nhân hệ số bí mật) — đúng quy tắc bảo mật của khóa.")
    up = st.file_uploader("Tải CSV", type="csv")
    if up is None:
        st.stop()
    u = pd.read_csv(up)
    for k, g in u.groupby("series"):
        s = g.set_index("month").demand.astype(float)
        s.index = pd.PeriodIndex(s.index, freq="M")
        series[str(k)] = s.sort_index()
    FUT = pd.period_range(max(s.index.max() for s in series.values()) + 1, periods=12, freq="M")


def lib_for(y):
    lib = evaluation.method_library(12)
    if np.mean(y == 0) > 0.25:
        lib = {"SBA": lambda yy, h: intermittent.croston(yy, h, 0.1, "sba")["forecast"],
               "Croston": lambda yy, h: intermittent.croston(yy, h, 0.1, "croston")["forecast"],
               "SES (α=0,1)": lambda yy, h: smoothing.ses(yy, h, alpha=0.1).forecast,
               "Naive": lambda yy, h: baseline.naive(yy, h)}
    if len(y) < 24:
        lib = {k: v for k, v in lib.items() if "Winters" not in k and "Seasonal" not in k}
    return lib


st.subheader("Bước 1–2 · Chọn mô hình bằng sai số ngoài mẫu")
choice, sel_rows, tables = {}, [], {}
for k, s in series.items():
    y = s.values
    lib = lib_for(y)
    best, tbl = evaluation.best_fit(y, TEST_MONTHS, 12, lib)
    tables[k] = tbl
    sel_rows.append({"Chuỗi": k, "Gợi ý (WMAPE test nhỏ nhất)": best, "WMAPE test": tbl.iloc[0]["WMAPE%"],
                     "WMAPE Naive": float(tbl.set_index("method").loc["Naive", "WMAPE%"]) if "Naive" in set(tbl.method) else np.nan})
st.dataframe(pd.DataFrame(sel_rows).style.format({"WMAPE test": "{:.1f}", "WMAPE Naive": "{:.1f}"}, na_rep="–"), hide_index=True, use_container_width=True)
cols = st.columns(3)
for i, k in enumerate(series):
    opts = list(tables[k].method)
    choice[k] = cols[i % 3].selectbox(f"Phương pháp cho {k}", opts, index=0, key=f"m_{k}")

st.subheader("Bước 3–4 · Dự báo 12 tháng và điều chỉnh có giả định")
k_view = st.selectbox("Xem / điều chỉnh chuỗi", list(series))
y = series[k_view].values
fn = lib_for(y)[choice[k_view]]
stat = np.maximum(fn(y, 12), 0)
c1, c2, c3 = st.columns(3)
use_tet = c1.toggle("Phân bổ lại T12–T2 theo Tết 2027", value=src == "Portfolio của lớp")
growth = c2.slider("Điều chỉnh mức chung (%)", -30, 30, 0, 1) / 100
promo_m = c3.multiselect("Tháng có KM đã duyệt", [str(f) for f in FUT])
up = st.slider("Uplift áp dụng cho tháng KM (%)", 0, 150, 30, 5) / 100 if promo_m else 0.0
adj = np.zeros(12)
why = [""] * 12
idx = {str(f): i for i, f in enumerate(FUT)}
if use_tet and {"2026-11", "2027-03"} <= set(idx):
    tp = seasonal.tet_part_ratio(series[k_view], cal)
    R = float(tp.phan_Tet.mean()) if len(tp) else 0.0
    if R > 0.15:
        normal = (stat[idx["2026-11"]] + stat[idx["2027-03"]]) / 2
        for mo, v in seasonal.tet_reallocate(normal, R, cal, ["2026-12", "2027-01", "2027-02"]).items():
            adj[idx[mo]] += v - stat[idx[mo]]
            why[idx[mo]] = f"Tết 2027: R={R:.2f}"
    else:
        st.caption(f"Phần Tết lịch sử = {R:.2f} tháng-thường (< 0,15) → không phân bổ lại.")
adj += (stat + adj) * growth
for mo in promo_m:
    adj[idx[mo]] += stat[idx[mo]] * up
    why[idx[mo]] = (why[idx[mo]] + "; " if why[idx[mo]] else "") + f"KM +{up:.0%}"
cons = stat + adj
f = fig_base(f"{k_view} — lịch sử, thống kê và đồng thuận", 400)
add_line(f, series[k_view].index, y, "Lịch sử", INK)
add_line(f, FUT, stat, f"Thống kê ({choice[k_view]})", CAT[0], dash="dot", mode="lines+markers")
add_line(f, FUT, cons, "Đồng thuận (sau điều chỉnh)", CAT[2], mode="lines+markers")
st.plotly_chart(f, use_container_width=True)

st.subheader("Bước 5–6 · Safety Stock và file bàn giao")
c1, c2 = st.columns(2)
sl = c1.slider("Mức phục vụ", 0.80, 0.99, 0.95, 0.01)
lt = c2.slider("Lead time (tuần) — áp dụng chung nếu không có trong sku_master", 1, 12, 3)
m = D["sku_master"].drop_duplicates("planning_item").set_index("planning_item")
out = []
for k, s in series.items():
    yy = s.values
    f_ = lib_for(yy)[choice[k]]
    errs = [yy[t] - f_(yy[:t], 1)[0] for t in range(len(yy) - 12, len(yy))]
    sigma = float(np.sqrt(np.mean(np.square(errs))))
    it = k.split("|")[0]
    L = (float(m.loc[it, "lead_time_weeks"]) if it in m.index else lt) / 4.33
    ss = inventory.safety_stock(sigma, L, sl)
    st_ = np.maximum(f_(yy, 12), 0)
    cc = cons if k == k_view else st_
    for i, mo in enumerate(FUT):
        out.append({"Chuỗi": k, "Tháng": str(mo), "Thống kê": round(st_[i]), "Nhu cầu đồng thuận (chưa giới hạn)": round(cc[i]),
                    "σ sai số": round(sigma), "Safety Stock": round(ss), "Phương pháp": choice[k],
                    "Giả định": why[i] if k == k_view else ""})
ho = pd.DataFrame(out)
st.dataframe(ho.pivot_table(index="Tháng", columns="Chuỗi", values="Nhu cầu đồng thuận (chưa giới hạn)").style.format("{:,.0f}"), use_container_width=True)
st.caption("Điều chỉnh ở Bước 4 chỉ áp cho chuỗi đang xem; các chuỗi khác dùng số thống kê. Ghi mọi giả định vào Capstone_Template.xlsx (sheet 05).")
buf = io.BytesIO()
with pd.ExcelWriter(buf, engine="openpyxl") as w:
    pd.DataFrame(sel_rows).to_excel(w, sheet_name="Chon_mo_hinh", index=False)
    ho.to_excel(w, sheet_name="Ban_giao_PP", index=False)
st.download_button("⬇ Tải file bàn giao (Excel)", buf.getvalue(), file_name="Ban_giao_Production_Planning.xlsx",
                   mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
note("Số bàn giao là nhu cầu đồng thuận <b>CHƯA giới hạn năng lực</b>, kèm σ và Safety Stock. Module Production Planning sẽ dùng file này để lập MPS/MRP "
     "và trả lời câu hỏi 'làm được bao nhiêu'.")
