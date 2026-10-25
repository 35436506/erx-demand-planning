import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from dpkit import baseline, evaluation, metrics, smoothing
from lab_common import CAT, INK, TEST_MONTHS, add_line, clean_series, fig_base, metric_table, note, page, pick_series, shade_test

page(4, "Exponential Smoothing & dự báo cuốn chiếu",
     "Dự báo mới = dự báo cũ + α × sai số. Kéo α để cảm nhận; so với α tối ưu (≈ Solver) chọn trên TRAIN; rồi đo sai số theo độ trễ.")
c1, c2 = st.columns([2, 1])
with c1:
    key = pick_series(default="N03|GT")
with c2:
    method = st.radio("Phương pháp", ["SES", "Holt", "Holt tắt dần"], horizontal=True)
y = clean_series(key)
tr, te = y.values[:-TEST_MONTHS], y.values[-TEST_MONTHS:]
opt = {"SES": smoothing.ses(tr, TEST_MONTHS), "Holt": smoothing.holt(tr, TEST_MONTHS),
       "Holt tắt dần": smoothing.holt(tr, TEST_MONTHS, damped=True)}[method]

tab1, tab2 = st.tabs(["Tham số & kết quả trên test", "Cuốn chiếu theo độ trễ (lag)"])
with tab1:
    c1, c2, c3 = st.columns(3)
    a = c1.slider("α (mức)", 0.0, 1.0, float(round(opt.params["alpha"], 2)), 0.01)
    bval = c2.slider("β (xu hướng)", 0.0, 0.5, float(round(opt.params.get("beta", 0.1), 2)), 0.01, disabled=method == "SES")
    ph = c3.slider("φ (tắt dần)", 0.80, 1.0, float(round(opt.params.get("phi", 1.0), 2)), 0.01, disabled=method != "Holt tắt dần")
    if method == "SES":
        man = smoothing.ses(tr, TEST_MONTHS, alpha=a)
    else:
        man = smoothing.holt(tr, TEST_MONTHS, alpha=a, beta=bval, damped=method == "Holt tắt dần", phi=ph if method == "Holt tắt dần" else None)
    f = fig_base(f"{key} — {method}", 420)
    add_line(f, y.index, y.values, "Thực tế", INK)
    add_line(f, y.index[:len(tr)], man.fitted, "Khớp 1 bước (tham số của bạn)", CAT[2], width=1.5)
    add_line(f, y.index[-TEST_MONTHS:], man.forecast, "Dự báo test (của bạn)", CAT[2], mode="lines+markers")
    add_line(f, y.index[-TEST_MONTHS:], opt.forecast, "Dự báo test (tối ưu trên train)", CAT[0], dash="dot", mode="lines+markers")
    add_line(f, y.index[-TEST_MONTHS:], baseline.naive(tr, TEST_MONTHS), "Naive", CAT[1], dash="dash")
    shade_test(f, y.index)
    st.plotly_chart(f, use_container_width=True)
    rows = [{"Phiên bản": "Tham số của bạn", "SSE train": man.sse, **metrics.summary(te, man.forecast, tr)},
            {"Phiên bản": "Tối ưu trên train", "SSE train": opt.sse, **metrics.summary(te, opt.forecast, tr)},
            {"Phiên bản": "Naive (mốc)", "SSE train": np.nan, **metrics.summary(te, baseline.naive(tr, TEST_MONTHS), tr)}]
    st.dataframe(metric_table(rows, {"SSE train": "{:,.0f}"}), hide_index=True, use_container_width=True)
    st.caption("Tham số tối ưu: " + ", ".join(f"{k} = {v:.3f}" for k, v in opt.params.items()))
    note("α nhỏ → mượt, chậm phản ứng; α lớn → bám sát, dễ đuổi theo nhiễu. SSE train nhỏ nhất KHÔNG bảo đảm WMAPE test nhỏ nhất — "
         "đó là lý do luôn chấm ngoài mẫu.")

with tab2:
    c1, c2 = st.columns(2)
    n_orig = c1.slider("Số tháng đánh giá cuốn chiếu", 6, 18, 12)
    hmax = c2.slider("Độ trễ tối đa (lag)", 1, 6, 3)
    yv = y.values
    fn = {"SES": lambda yy, h: smoothing.ses(yy, h, alpha=opt.params["alpha"]).forecast,
          "Holt": lambda yy, h: smoothing.holt(yy, h, alpha=opt.params["alpha"], beta=opt.params["beta"]).forecast,
          "Holt tắt dần": lambda yy, h: smoothing.holt(yy, h, alpha=opt.params["alpha"], beta=opt.params["beta"], damped=True, phi=opt.params["phi"]).forecast}[method]
    ro = evaluation.rolling_origin(yv, len(yv) - n_orig - hmax + 1, hmax, fn)
    ro = ro[ro.target >= len(yv) - n_orig]
    lag = evaluation.accuracy_by_lag(ro)
    f = fig_base("WMAPE theo độ trễ", 320)
    f.add_trace(go.Bar(x=[f"Lag-{int(v)}" for v in lag.lag], y=lag["WMAPE%"], marker_color=CAT[0],
                       text=[f"{v:.1f}%" for v in lag["WMAPE%"]], textposition="outside"))
    f.update_layout(showlegend=False, hovermode="closest")
    st.plotly_chart(f, use_container_width=True)
    st.dataframe(lag.style.format({"WMAPE%": "{:.1f}", "Bias%": "{:+.1f}", "n": "{:.0f}"}), hide_index=True, use_container_width=True)
    note("<b>Đo KPI ở đúng độ trễ.</b> Nếu nhà máy khóa lịch trước 3 tháng (vùng đóng băng), độ chính xác có ý nghĩa vận hành là lag-3, "
         "không phải lag-1. Sales muốn sửa số trong vùng đóng băng? → hỏi: sửa để làm gì, ai chịu chi phí đổi lịch.")
