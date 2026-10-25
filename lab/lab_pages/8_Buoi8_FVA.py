import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from dpkit import metrics
from lab_common import CAT, INK, MUTED, add_line, fig_base, load_all, note, page

page(8, "Demand Review & Forecast Value Added",
     "Mỗi bước chỉnh số (Sales, đồng thuận) có làm dự báo tốt lên không? Đo bằng FVA trên 460 dự báo lag-1 thật của case (10/2025–09/2026).")
D = load_all()


@st.cache_data(show_spinner=False)
def fva_frame():
    fh = D["forecast_history"].copy()
    sh = D["sales_history"].copy()
    sh["item"] = sh.sku.replace({"S06N": "S06"})
    act = sh.groupby(["item", "channel", "month"]).shipments.sum().reset_index()
    act.columns = ["sku", "channel", "origin_month", "naive"]
    fh = fh.merge(act, on=["sku", "channel", "origin_month"], how="left").dropna(subset=["naive", "actual_shipments"])
    return fh[fh.actual_shipments > 0]


fh = fva_frame()
tab1, tab2, tab3 = st.tabs(["FVA thác nước", "Tracking Signal", "Mô phỏng quy tắc chỉnh số"])
with tab1:
    c1, c2 = st.columns(2)
    scope = c1.radio("Phạm vi", ["Tất cả", "Tháng CÓ khuyến mãi", "Tháng KHÔNG khuyến mãi"], horizontal=True)
    cats = c2.multiselect("Lọc kênh", ["GT", "MT"], default=["GT", "MT"])
    d = fh[fh.channel.isin(cats)]
    if scope != "Tất cả":
        d = d[d.promo_flag == (1 if scope.startswith("Tháng CÓ") else 0)]
    rows = metrics.fva(d.actual_shipments.values, {"Thống kê": d.stat_forecast.values, "Sales": d.sales_input.values,
                                                   "Đồng thuận": d.consensus.values}, naive=d.naive.values)
    t = pd.DataFrame(rows)
    t["vs"] = t["vs"].fillna("–")
    f = fig_base(f"WMAPE từng bước — {scope.lower()} ({len(d)} dự báo)", 380, "WMAPE %")
    colors = [MUTED, CAT[0], CAT[2], CAT[1]]
    f.add_trace(go.Bar(x=t.step, y=t["WMAPE%"], marker_color=colors, text=[f"{v:.1f}%" for v in t["WMAPE%"]], textposition="outside"))
    f.update_layout(showlegend=False, hovermode="closest")
    st.plotly_chart(f, use_container_width=True)
    st.dataframe(t.rename(columns={"step": "Bước", "FVA_vs_prev_pp": "FVA so bước trước (điểm %)", "vs": "So với"})
                 .style.format({"WMAPE%": "{:.1f}", "Bias%": "{:+.1f}", "FVA so bước trước (điểm %)": "{:+.1f}"}, na_rep="–"),
                 hide_index=True, use_container_width=True)
    note("Đọc cùng nhau: (1) thống kê có thắng Naive? (2) số Sales có bias dương (lạc quan) không? (3) ở tháng CÓ khuyến mãi bước đồng thuận "
         "thêm nhiều giá trị — vì có thông tin thật; ở tháng KHÔNG khuyến mãi chỉnh tay thường làm xấu đi. → Quy tắc: chỉ chỉnh khi có thông tin mới, ghi lý do, đo lại.")
with tab2:
    keys = (fh.sku + "|" + fh.channel).drop_duplicates().tolist()
    key = st.selectbox("Chuỗi", keys, index=keys.index("N01|GT") if "N01|GT" in keys else 0)
    it, ch = key.split("|")
    d = fh[(fh.sku == it) & (fh.channel == ch)].sort_values("target_month")
    thr = st.slider("Ngưỡng cảnh báo |TS|", 2.0, 6.0, 4.0, 0.5)
    f = fig_base(f"Tracking Signal — {key}", 360)
    for col_, nm, colr in [("sales_input", "Sales", CAT[2]), ("stat_forecast", "Thống kê", CAT[0]), ("consensus", "Đồng thuận", CAT[1])]:
        add_line(f, d.target_month, metrics.tracking_signal(d.actual_shipments, d[col_]), nm, colr, mode="lines+markers")
    f.add_hline(y=thr, line_dash="dash", line_color=INK)
    f.add_hline(y=-thr, line_dash="dash", line_color=INK)
    st.plotly_chart(f, use_container_width=True)
    note("TS = tổng sai số cộng dồn / MAD. TS âm dần = dự báo liên tục CAO hơn thực tế. Vượt ngưỡng → mở cuộc điều tra: nguồn lạc quan ở đâu, "
         "mô hình có bỏ sót xu hướng không?")
with tab3:
    st.write("Giả sử công ty áp dụng quy tắc: **chỉ chấp nhận điều chỉnh của Sales khi có khuyến mãi**, các tháng khác giữ số thống kê. Kết quả sẽ ra sao?")
    w = st.slider("Ở tháng khuyến mãi, lấy bao nhiêu % phần chênh Sales − Thống kê", 0, 100, 60, 10)
    sim = np.where(fh.promo_flag == 1, fh.stat_forecast + w / 100 * (fh.sales_input - fh.stat_forecast), fh.stat_forecast)
    a = fh.actual_shipments.values
    res = pd.DataFrame([{"Phiên bản": "Thống kê", "WMAPE%": metrics.wmape(a, fh.stat_forecast), "Bias%": metrics.bias_pct(a, fh.stat_forecast) * 100},
                        {"Phiên bản": "Sales", "WMAPE%": metrics.wmape(a, fh.sales_input), "Bias%": metrics.bias_pct(a, fh.sales_input) * 100},
                        {"Phiên bản": "Đồng thuận (thực tế đã làm)", "WMAPE%": metrics.wmape(a, fh.consensus), "Bias%": metrics.bias_pct(a, fh.consensus) * 100},
                        {"Phiên bản": f"Quy tắc mô phỏng ({w}%)", "WMAPE%": metrics.wmape(a, sim), "Bias%": metrics.bias_pct(a, sim) * 100}])
    st.dataframe(res.style.format({"WMAPE%": "{:.1f}", "Bias%": "{:+.1f}"}), hide_index=True, use_container_width=True)
    note("Đây là 'thí nghiệm' trên dữ liệu quá khứ — kết luận dùng để đề xuất quy tắc cho Demand Review, rồi phải theo dõi FVA vài tháng mới chốt.")
