import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from dpkit_en import baseline, evaluation, metrics, smoothing
from lab_common_en import CAT, INK, TEST_MONTHS, add_line, clean_series, fig_base, metric_table, note, page, pick_series, shade_test

page(4, "Exponential Smoothing & rolling forecasts",
     "New forecast = old forecast + α × error. Drag α to get a feel; compare with the optimal α (≈ Solver) chosen on TRAIN; then measure error by lag.")
c1, c2 = st.columns([2, 1])
with c1:
    key = pick_series(default="N03|GT")
with c2:
    method = st.radio("Method", ["SES", "Holt", "Damped Holt"], horizontal=True)
y = clean_series(key)
tr, te = y.values[:-TEST_MONTHS], y.values[-TEST_MONTHS:]
opt = {"SES": smoothing.ses(tr, TEST_MONTHS), "Holt": smoothing.holt(tr, TEST_MONTHS),
       "Damped Holt": smoothing.holt(tr, TEST_MONTHS, damped=True)}[method]

tab1, tab2 = st.tabs(["Parameters & test results", "Rolling forecasts by lag)"])
with tab1:
    c1, c2, c3 = st.columns(3)
    a = c1.slider("α (level)", 0.0, 1.0, float(round(opt.params["alpha"], 2)), 0.01)
    bval = c2.slider("β (trend)", 0.0, 0.5, float(round(opt.params.get("beta", 0.1), 2)), 0.01, disabled=method == "SES")
    ph = c3.slider("φ (damping)", 0.80, 1.0, float(round(opt.params.get("phi", 1.0), 2)), 0.01, disabled=method != "Damped Holt")
    if method == "SES":
        man = smoothing.ses(tr, TEST_MONTHS, alpha=a)
    else:
        man = smoothing.holt(tr, TEST_MONTHS, alpha=a, beta=bval, damped=method == "Damped Holt", phi=ph if method == "Damped Holt" else None)
    f = fig_base(f"{key} — {method}", 420)
    add_line(f, y.index, y.values, "Actual", INK)
    add_line(f, y.index[:len(tr)], man.fitted, "1-step fit (your parameters)", CAT[2], width=1.5)
    add_line(f, y.index[-TEST_MONTHS:], man.forecast, "Test forecast (yours)", CAT[2], mode="lines+markers")
    add_line(f, y.index[-TEST_MONTHS:], opt.forecast, "Test forecast (optimised on train)", CAT[0], dash="dot", mode="lines+markers")
    add_line(f, y.index[-TEST_MONTHS:], baseline.naive(tr, TEST_MONTHS), "Naive", CAT[1], dash="dash")
    shade_test(f, y.index)
    st.plotly_chart(f, use_container_width=True)
    rows = [{"Version": "Your parameters", "SSE train": man.sse, **metrics.summary(te, man.forecast, tr)},
            {"Version": "Optimised on train", "SSE train": opt.sse, **metrics.summary(te, opt.forecast, tr)},
            {"Version": "Naive (benchmark)", "SSE train": np.nan, **metrics.summary(te, baseline.naive(tr, TEST_MONTHS), tr)}]
    st.dataframe(metric_table(rows, {"SSE train": "{:,.0f}"}), hide_index=True, use_container_width=True)
    st.caption("Optimal parameters:  " + ", ".join(f"{k} = {v:.3f}" for k, v in opt.params.items()))
    note("Small α → smooth, slow to react; large α → tracks closely, easily chases noise. The lowest train SSE does NOT guarantee the lowest test WMAPE — "
         "which is why we always score out of sample.")

with tab2:
    c1, c2 = st.columns(2)
    n_orig = c1.slider("Months of rolling evaluation", 6, 18, 12)
    hmax = c2.slider("Maximum lag)", 1, 6, 3)
    yv = y.values
    fn = {"SES": lambda yy, h: smoothing.ses(yy, h, alpha=opt.params["alpha"]).forecast,
          "Holt": lambda yy, h: smoothing.holt(yy, h, alpha=opt.params["alpha"], beta=opt.params["beta"]).forecast,
          "Damped Holt": lambda yy, h: smoothing.holt(yy, h, alpha=opt.params["alpha"], beta=opt.params["beta"], damped=True, phi=opt.params["phi"]).forecast}[method]
    ro = evaluation.rolling_origin(yv, len(yv) - n_orig - hmax + 1, hmax, fn)
    ro = ro[ro.target >= len(yv) - n_orig]
    lag = evaluation.accuracy_by_lag(ro)
    f = fig_base("WMAPE by lag", 320)
    f.add_trace(go.Bar(x=[f"Lag-{int(v)}" for v in lag.lag], y=lag["WMAPE%"], marker_color=CAT[0],
                       text=[f"{v:.1f}%" for v in lag["WMAPE%"]], textposition="outside"))
    f.update_layout(showlegend=False, hovermode="closest")
    st.plotly_chart(f, use_container_width=True)
    st.dataframe(lag.style.format({"WMAPE%": "{:.1f}", "Bias%": "{:+.1f}", "n": "{:.0f}"}), hide_index=True, use_container_width=True)
    note("<b>Measure KPIs at the right lag.</b> If the factory freezes its schedule 3 months ahead (the frozen zone), the operationally meaningful accuracy is lag-3, "
         "not lag-1. Sales wants to change a number inside the frozen zone? → ask: what for, and who pays for rescheduling.")
