import warnings

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from dpkit import classify, evaluation, intermittent, metrics, smoothing
from lab_common import CAT, INK, MUTED, TEST_MONTHS, add_line, clean_series, fig_base, load_all, metric_table, note, page, pick_series, shade_test

warnings.filterwarnings("ignore")
page(7, "Chọn mô hình theo nhóm sản phẩm",
     "Lập chính sách cho CẢ danh mục: ABC-XYZ, hình dạng nhu cầu, Croston cho mã rời rạc, 'best-fit' ngoài mẫu — và một mở rộng học thuật với SARIMA.")
D = load_all()
dc = D["demand_clean"]
m = D["sku_master"].drop_duplicates("planning_item").set_index("planning_item")


@st.cache_data(show_spinner=False)
def portfolio(ax, ay, xx, xy):
    series = {}
    for (it, ch), g in dc[dc["item"] != "N06"].groupby(["item", "channel"]):
        s = g.set_index("month").demand
        s.index = pd.PeriodIndex(s.index, freq="M")
        series[f"{it}|{ch}"] = s
    port = classify.item_portfolio(series, m.price_k.to_dict(), 12)
    v = port.set_index("series").value_12m_trieu
    port["ABC"] = classify.abc(v, ax, ay).values
    port["XYZ"] = port.CV.map(lambda c: classify.xyz(c, xx, xy))
    port["XYZ_khu_mua_vu"] = port.CV_khu_mua_vu.map(lambda c: classify.xyz(c, xx, xy))
    port["Nhóm"] = port.ABC + port.XYZ_khu_mua_vu
    port["Phương pháp"] = np.where(port.ADI >= 1.32, "Croston / SBA / TSB (rời rạc)", port["Nhóm"].map(classify.METHOD_MATRIX))
    ser_port = classify.portfolio_table(series, m.price_k.to_dict(), 12)
    return port, ser_port


tab1, tab2, tab3, tab4 = st.tabs(["Ma trận ABC × XYZ", "Bản đồ hình dạng & Croston", "Best-fit trong vs ngoài mẫu", "Mở rộng: SARIMA"])
with tab1:
    c = st.columns(4)
    ax = c[0].slider("Ngưỡng A (lũy kế)", 0.6, 0.9, 0.80, 0.05)
    ay = c[1].slider("Ngưỡng B (lũy kế)", 0.85, 0.99, 0.95, 0.01)
    xx = c[2].slider("Ngưỡng X (CV ≤)", 0.05, 0.30, 0.15, 0.01)
    xy = c[3].slider("Ngưỡng Y (CV ≤)", 0.20, 0.80, 0.35, 0.05)
    port, ser_port = portfolio(ax, ay, xx, xy)
    mat = pd.crosstab(port.ABC, port.XYZ_khu_mua_vu).reindex(index=list("ABC"), columns=list("XYZ"), fill_value=0)
    c1, c2 = st.columns([1, 1.6])
    with c1:
        f = px.imshow(mat, text_auto=True, color_continuous_scale=["#FFFFFF", "#01AE42"], aspect="auto")
        f.update_layout(height=320, coloraxis_showscale=False, margin=dict(t=30, l=10, r=10, b=10), title="Số SKU (XYZ sau khử mùa vụ)")
        st.plotly_chart(f, use_container_width=True)
    with c2:
        show = port[["item", "value_12m_trieu", "ABC", "CV", "XYZ", "CV_khu_mua_vu", "XYZ_khu_mua_vu", "ADI", "Nhóm", "Phương pháp"]].rename(
            columns={"item": "SKU", "value_12m_trieu": "Giá trị 12T (tr.đ)", "CV": "CV thô", "XYZ": "XYZ thô", "CV_khu_mua_vu": "CV khử MV", "XYZ_khu_mua_vu": "XYZ khử MV"})
        st.dataframe(show.style.format({"Giá trị 12T (tr.đ)": "{:,.0f}", "CV thô": "{:.2f}", "CV khử MV": "{:.2f}", "ADI": "{:.2f}"}),
                     hide_index=True, use_container_width=True, height=330)
    note("K02 và B01 có CV thô cao vì MÙA VỤ, không phải vì khó dự báo — sau khử mùa vụ chúng sang nhóm dễ hơn. "
         "Câu hỏi cho phần mềm APS: phân nhóm XYZ dựa trên CV thô hay CV của sai số dự báo?")

with tab2:
    port, ser_port = portfolio(0.8, 0.95, 0.15, 0.35)
    f = px.scatter(ser_port, x=ser_port.ADI.clip(upper=6), y=ser_port.CV2.clip(upper=2.5), color="SBC", hover_name="series",
                   color_discrete_sequence=CAT, labels={"x": "ADI (tháng)", "y": "CV² cỡ đơn"})
    f.add_vline(x=1.32, line_color=INK, line_width=1)
    f.add_hline(y=0.49, line_color=INK, line_width=1)
    f.update_layout(template="plotly_white", height=380, title="Syntetos–Boylan: smooth · erratic · intermittent · lumpy (SKU × kênh, 12 tháng)")
    st.plotly_chart(f, use_container_width=True)
    key = pick_series("Chuỗi rời rạc", "H02|GT", options=["H01|GT", "H02|GT", "H03|GT", "K04|MT"], key="s7b")
    alpha = st.slider("α", 0.05, 0.5, 0.10, 0.05)
    y = clean_series(key).values
    per = clean_series(key).index
    res = {v: intermittent.croston(y, 6, alpha, v) for v in ("croston", "sba", "tsb")}
    f = fig_base(f"{key}: Croston / SBA / TSB (dự báo 1 bước)", 360)
    f.add_bar(x=[str(p) for p in per], y=y, name="Thực tế", marker_color="#C9CCC9")
    for (k, r), colr in zip(res.items(), CAT):
        add_line(f, per, r["fitted"], k.upper() if k != "croston" else "Croston", colr)
    st.plotly_chart(f, use_container_width=True)
    start = len(y) - 18
    rows = []
    for nm, fn in {"Croston": lambda yy: intermittent.croston(yy, 1, alpha, "croston")["forecast"][0],
                   "SBA": lambda yy: intermittent.croston(yy, 1, alpha, "sba")["forecast"][0],
                   "TSB": lambda yy: intermittent.croston(yy, 1, alpha, "tsb")["forecast"][0],
                   "SES": lambda yy: smoothing.ses(yy, 1, alpha=alpha).forecast[0], "Naive": lambda yy: yy[-1]}.items():
        fcs = np.array([fn(y[:t]) for t in range(start, len(y))])
        rows.append({"Phương pháp": nm, "MAE": metrics.mae(y[start:], fcs), "Bias%": metrics.bias_pct(y[start:], fcs) * 100,
                     "TB dự báo": fcs.mean(), "TB thực tế": y[start:].mean()})
    st.dataframe(pd.DataFrame(rows).style.format({"MAE": "{:,.1f}", "Bias%": "{:+.1f}", "TB dự báo": "{:,.1f}", "TB thực tế": "{:,.1f}"}),
                 hide_index=True, use_container_width=True)
    note("Croston dự báo <i>tốc độ nhu cầu trung bình</i>, không dự báo tháng nào có đơn. Croston gốc thiên lệch cao → SBA nhân (1 − α/2). "
         "TSB hạ dự báo dần khi lâu không có đơn — hợp với mã sắp lỗi thời. K04 (giỏ quà Tết) rời rạc NHƯNG theo mùa: Croston bỏ qua mùa vụ!")

with tab3:
    st.write("Phần mềm APS thường chọn 'best-fit' theo sai số trong mẫu. Bảng dưới so lựa chọn đó với lựa chọn theo 6 tháng test.")

    @st.cache_data(show_spinner=False)
    def bestfit_table():
        rows = []
        for key in ser_port.sort_values("value_12m_trieu", ascending=False).series.head(10):
            s = clean_series(key).values
            tr = s[:-TEST_MONTHS]
            _, tbl = evaluation.best_fit(s, TEST_MONTHS)
            ins = {}
            for nm, fn in {"SES": lambda yy: smoothing.ses(yy, 6), "Holt": lambda yy: smoothing.holt(yy, 6),
                           "Holt-Winters nhân": lambda yy: smoothing.holt_winters(yy, 6, 12, "mul")}.items():
                r = fn(tr)
                ins[nm] = metrics.wmape(tr[12:], r.fitted[12:])
            bi = min(ins, key=ins.get)
            out_of_bi = tbl.set_index("method").loc[bi, "WMAPE%"]
            rows.append({"Chuỗi": key, "Best-fit TRONG mẫu": bi, "WMAPE trong mẫu": ins[bi], "→ WMAPE test của nó": out_of_bi,
                         "Best-fit NGOÀI mẫu": tbl.iloc[0]["method"], "WMAPE test": tbl.iloc[0]["WMAPE%"]})
        return pd.DataFrame(rows)

    _, ser_port = portfolio(0.8, 0.95, 0.15, 0.35)
    bt = bestfit_table()
    st.dataframe(bt.style.format({c: "{:.1f}" for c in bt.columns if "WMAPE" in c}), hide_index=True, use_container_width=True)
    note("Khi phần mềm báo 'best-fit', hãy hỏi: (1) chọn theo sai số trong hay ngoài mẫu? (2) ở horizon/lag nào? (3) có so với Naive không? "
         "(4) bao lâu chọn lại mô hình một lần — chọn lại mỗi tháng dễ làm forecast 'nhảy' (nervousness).")

with tab4:
    st.write("Mở rộng học thuật — ARIMA mùa vụ (SARIMA) trên log(nhu cầu), chọn bậc bằng AIC **chỉ trên train**, so với Holt-Winters.")
    key = pick_series(default="B01|GT", key="s7d")
    if st.button("Chạy lưới SARIMA (≈ 10–20 giây)"):
        from statsmodels.tsa.statespace.sarimax import SARIMAX
        y = clean_series(key, "demand_ex_event")
        tr, te = y.values[:-TEST_MONTHS], y.values[-TEST_MONTHS:]
        grid = []
        for o in [(0, 1, 1), (1, 1, 0), (1, 1, 1), (0, 1, 2)]:
            for so in [(0, 1, 1, 12), (1, 1, 0, 12)]:
                try:
                    fit = SARIMAX(np.log(np.maximum(tr, 1)), order=o, seasonal_order=so).fit(disp=False)
                    grid.append((o, so, fit.aic, fit))
                except Exception:
                    pass
        grid.sort(key=lambda g: g[2])
        best = grid[0]
        sar = np.exp(best[3].forecast(TEST_MONTHS))
        hw = smoothing.holt_winters(tr, TEST_MONTHS, 12, "mul").forecast
        st.dataframe(pd.DataFrame([{"order": str(g[0]), "seasonal": str(g[1]), "AIC": g[2]} for g in grid]).style.format({"AIC": "{:.1f}"}),
                     hide_index=True, use_container_width=True)
        f = fig_base(f"{key}: SARIMA{best[0]}{best[1]} vs Holt-Winters", 360)
        add_line(f, y.index, y.values, "Thực tế", INK)
        add_line(f, y.index[-TEST_MONTHS:], sar, "SARIMA", CAT[3], mode="lines+markers")
        add_line(f, y.index[-TEST_MONTHS:], hw, "Holt-Winters nhân", CAT[0], mode="lines+markers")
        shade_test(f, y.index)
        st.plotly_chart(f, use_container_width=True)
        st.dataframe(metric_table([{"Phương pháp": "SARIMA", **metrics.summary(te, sar, tr, 12)},
                                   {"Phương pháp": "Holt-Winters nhân", **metrics.summary(te, hw, tr, 12)}]), hide_index=True, use_container_width=True)
        note("Với 30 tháng dữ liệu, mô hình nhiều tham số hơn không tự động thắng (bài học của các cuộc thi M-Competitions). "
             "Bẫy rò rỉ dữ liệu: chọn bậc ARIMA bằng AIC trên TOÀN BỘ dữ liệu rồi mới chia test.")
