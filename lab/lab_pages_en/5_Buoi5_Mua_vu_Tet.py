import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from dpkit_en import metrics, seasonal, smoothing
from lab_common_en import BRAND, CAT, INK, TEST_MONTHS, add_line, clean_series, fig_base, load_all, metric_table, note, page, pick_series, shade_test

page(5, "Seasonality & the Lunar New Year (Tết) effect",
     "Seasonal indices, additive/multiplicative Holt-Winters, and a tool to reallocate demand when Tết falls in a different month from last year.")
D = load_all()
cal = D["calendar"]
tab1, tab2, tab3 = st.tabs(["Seasonal indices & decomposition", "Holt-Winters", "Tết moving month"])

with tab1:
    c1, c2 = st.columns([2, 1])
    with c1:
        key = pick_series(default="B01|GT", key="s5a")
    with c2:
        ex = st.toggle("Exclude one-off events before computing", value=True, help="Uses the demand_ex_event column (e.g. S01|GT 06/2024)")
    y = clean_series(key, "demand_ex_event" if ex else "demand")
    mul = seasonal.seasonal_indices(y.values, y.index.month, model="mul")
    cma = seasonal.centered_ma(y.values)
    fig = make_subplots(rows=1, cols=2, column_widths=[0.62, 0.38], subplot_titles=("Actuals and the 2×12 centred moving average", "Seasonal index (mean = 1)"))
    fig.add_trace(go.Scatter(x=[str(v) for v in y.index], y=y.values, name="Actual", line=dict(color=INK)), 1, 1)
    fig.add_trace(go.Scatter(x=[str(v) for v in y.index], y=cma, name="CMA 2×12 (trend-cycle)", line=dict(color=CAT[0], width=3)), 1, 1)
    fig.add_trace(go.Bar(x=[f"T{k}" for k in range(1, 13)], y=mul.values, marker_color=[BRAND if v >= 1 else "#C9CCC9" for v in mul.values],
                         name="Index", text=[f"{v:.2f}" for v in mul.values], textposition="outside"), 1, 2)
    fig.update_layout(template="plotly_white", height=400, legend=dict(orientation="h", y=-0.15), margin=dict(t=50, l=10, r=10, b=10))
    st.plotly_chart(fig, use_container_width=True)
    st.write(f"Seasonal amplitude (max/min): **{mul.max() / mul.min():.2f}×**")
    note("Seasonal amplitude that swells with the sales level (B01's summer) → <b>multiplicative</b> seasonality. Amplitude roughly constant → <b>additive</b>. "
         "Toggle the event-exclusion switch for S01|GT to see how a June 2024 rumour can 'create' a fake seasonality.")

with tab2:
    key = pick_series(default="B01|GT", key="s5b")
    y = clean_series(key, "demand_ex_event")
    tr, te = y.values[:-TEST_MONTHS], y.values[-TEST_MONTHS:]
    try:
        hm = smoothing.holt_winters(tr, TEST_MONTHS, 12, "mul")
        ha = smoothing.holt_winters(tr, TEST_MONTHS, 12, "add")
        sn = np.array([tr[len(tr) - 12 + i % 12] for i in range(TEST_MONTHS)])
        f = fig_base(f"{key}: Holt-Winters vs Seasonal Naive", 400)
        add_line(f, y.index, y.values, "Actual", INK)
        add_line(f, y.index[:len(tr)], hm.fitted, "Multiplicative HW (fit)", CAT[0], width=1)
        add_line(f, y.index[-TEST_MONTHS:], hm.forecast, "Multiplicative HW", CAT[0], mode="lines+markers")
        add_line(f, y.index[-TEST_MONTHS:], ha.forecast, "Additive HW", CAT[1], mode="lines+markers")
        add_line(f, y.index[-TEST_MONTHS:], sn, "Seasonal Naive", CAT[2], dash="dot")
        shade_test(f, y.index)
        st.plotly_chart(f, use_container_width=True)
        rows = [{"Method": "Multiplicative HW", **metrics.summary(te, hm.forecast, tr, 12)},
                {"Method": "Additive HW", **metrics.summary(te, ha.forecast, tr, 12)},
                {"Method": "Seasonal Naive", **metrics.summary(te, sn, tr, 12)}]
        st.dataframe(metric_table(rows), hide_index=True, use_container_width=True)
        st.caption("Multiplicative HW parameters:  " + ", ".join(f"{k}={v:.3f}" for k, v in hm.params.items() if k != "m"))
        note("Excel 365: <code>FORECAST.ETS</code> is automatic Holt-Winters (Microsoft uses the AAA variant). Understanding how it updates L, T, S helps "
             "you explain the software's number instead of just copying it.")
    except ValueError as e:
        st.warning(str(e))

with tab3:
    st.markdown("**Idea:** the Tết shopping window ≈ 35 days before Tết. When Tết is early, most of the window falls in December–January; when it is late it moves into February.")
    c = cal.set_index("month")
    tet = pd.DataFrame([{"Year": y_, "Tết date": d, "Dec": c.loc[f"{y_-1}-12", "tet_pre_share"], "Jan": c.loc[f"{y_}-01", "tet_pre_share"],
                         "Feb": c.loc[f"{y_}-02", "tet_pre_share"]} for y_, d in [(2024, "10/02"), (2025, "29/01"), (2026, "17/02"), (2027, "06/02")]])
    c1, c2 = st.columns([1, 1.3])
    with c1:
        st.dataframe(tet.style.format({"Dec": "{:.0%}", "Jan": "{:.0%}", "Feb": "{:.0%}"}), hide_index=True, use_container_width=True)
        key = pick_series("Tết-sensitive series", "S01|GT", key="s5c", options=["S01|GT", "S01|MT", "S02|GT", "S04|GT", "B04|GT", "B04|MT", "K01|MT"])
        g = st.slider("Growth of the normal level, 2027 vs 2026", -0.10, 0.15, 0.03, 0.01, format="%.2f")
        dip = st.slider("Dip applied to post-Tết days", 0.0, 0.4, 0.15, 0.05)
    y = clean_series(key, "demand_ex_event")
    tp = seasonal.tet_part_ratio(y, cal)
    R = float(tp.phan_Tet.mean())
    normal = float(tp.muc_thuong.iloc[-1]) * (1 + g)
    fc = seasonal.tet_reallocate(normal, R, cal, ["2026-12", "2027-01", "2027-02"], dip)
    naive = {mo: float(y[pd.Period(f"{int(mo[:4]) - 1}{mo[4:]}", "M")]) * (1 + g) for mo in fc}
    with c2:
        st.dataframe(tp.rename(columns={"nam": "Year", "T12_T1_T2": "Dec+Jan+Feb", "muc_thuong": "Normal level", "phan_Tet": "Tết portion (normal months)"})
                     .style.format({"Dec+Jan+Feb": "{:,.0f}", "Normal level": "{:,.0f}", "Tết portion (normal months)": "{:.2f}"}), hide_index=True, use_container_width=True)
        f = fig_base(f"{key}: Dec 2026–Feb 2027", 320)
        f.add_trace(go.Bar(x=list(fc), y=list(naive.values()), name="Same period last year × (1+g)", marker_color="#C9CCC9"))
        f.add_trace(go.Bar(x=list(fc), y=list(fc.values()), name="By the 2027 Tết calendar", marker_color=CAT[0]))
        f.update_layout(barmode="group", hovermode="x")
        st.plotly_chart(f, use_container_width=True)
    diff = {k: fc[k] - naive[k] for k in fc}
    st.write("Difference (Tết calendar − same period):  " + " · ".join(f"**{k}: {v:+,.0f}**" for k, v in diff.items()))
    note(f"Average Tết portion = <b>{R:.2f}</b> normal months. Formula: Forecast = Normal level × (1 + R × pre-Tết share) × (1 − dip × post-Tết share). "
         "Discussion case:  'Tết is 3 weeks early, Sales says January will double' — how far do the numbers support it?")
