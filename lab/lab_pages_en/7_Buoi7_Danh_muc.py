import warnings

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from dpkit_en import classify, evaluation, intermittent, metrics, smoothing
from lab_common_en import CAT, INK, MUTED, TEST_MONTHS, add_line, clean_series, fig_base, load_all, metric_table, note, page, pick_series, shade_test

warnings.filterwarnings("ignore")
page(7, "Choosing models by product group",
     "Set policy for the WHOLE portfolio: ABC-XYZ, demand shapes, Croston for intermittent items, 'best-fit' out of sample — and an academic extension with SARIMA.")
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
    port["Group"] = port.ABC + port.XYZ_khu_mua_vu
    port["Method"] = np.where(port.ADI >= 1.32, "Croston / SBA / TSB (intermittent)", port["Group"].map(classify.METHOD_MATRIX))
    ser_port = classify.portfolio_table(series, m.price_k.to_dict(), 12)
    return port, ser_port


tab1, tab2, tab3, tab4 = st.tabs(["ABC × XYZ matrix", "Shape map & Croston", "Best fit in vs out of sample", "Extension: SARIMA"])
with tab1:
    c = st.columns(4)
    ax = c[0].slider("Threshold A (cumulative)", 0.6, 0.9, 0.80, 0.05)
    ay = c[1].slider("Threshold B (cumulative)", 0.85, 0.99, 0.95, 0.01)
    xx = c[2].slider("Threshold X (CV ≤)", 0.05, 0.30, 0.15, 0.01)
    xy = c[3].slider("Threshold Y (CV ≤)", 0.20, 0.80, 0.35, 0.05)
    port, ser_port = portfolio(ax, ay, xx, xy)
    mat = pd.crosstab(port.ABC, port.XYZ_khu_mua_vu).reindex(index=list("ABC"), columns=list("XYZ"), fill_value=0)
    c1, c2 = st.columns([1, 1.6])
    with c1:
        f = px.imshow(mat, text_auto=True, color_continuous_scale=["#FFFFFF", "#01AE42"], aspect="auto")
        f.update_layout(height=320, coloraxis_showscale=False, margin=dict(t=30, l=10, r=10, b=10), title="Number of SKUs (XYZ after deseasonalising)")
        st.plotly_chart(f, use_container_width=True)
    with c2:
        show = port[["item", "value_12m_trieu", "ABC", "CV", "XYZ", "CV_khu_mua_vu", "XYZ_khu_mua_vu", "ADI", "Group", "Method"]].rename(
            columns={"item": "SKU", "value_12m_trieu": "12-month value (VND m)", "CV": "Raw CV", "XYZ": "Raw XYZ", "CV_khu_mua_vu": "Deseasonalised CV", "XYZ_khu_mua_vu": "Deseasonalised XYZ"})
        st.dataframe(show.style.format({"12-month value (VND m)": "{:,.0f}", "Raw CV": "{:.2f}", "Deseasonalised CV": "{:.2f}", "ADI": "{:.2f}"}),
                     hide_index=True, use_container_width=True, height=330)
    note("K02 and B01 have a high raw CV because of SEASONALITY, not because they are hard to forecast — once deseasonalised they move to an easier group. "
         "A question for the APS software: is the XYZ grouping based on raw CV or on the CV of the forecast error?")

with tab2:
    port, ser_port = portfolio(0.8, 0.95, 0.15, 0.35)
    f = px.scatter(ser_port, x=ser_port.ADI.clip(upper=6), y=ser_port.CV2.clip(upper=2.5), color="SBC", hover_name="series",
                   color_discrete_sequence=CAT, labels={"x": "ADI (months)", "y": "CV² of order size"})
    f.add_vline(x=1.32, line_color=INK, line_width=1)
    f.add_hline(y=0.49, line_color=INK, line_width=1)
    f.update_layout(template="plotly_white", height=380, title="Syntetos–Boylan: smooth · erratic · intermittent · lumpy (SKU × channel, 12 months)")
    st.plotly_chart(f, use_container_width=True)
    key = pick_series("Intermittent series", "H02|GT", options=["H01|GT", "H02|GT", "H03|GT", "K04|MT"], key="s7b")
    alpha = st.slider("α", 0.05, 0.5, 0.10, 0.05)
    y = clean_series(key).values
    per = clean_series(key).index
    res = {v: intermittent.croston(y, 6, alpha, v) for v in ("croston", "sba", "tsb")}
    f = fig_base(f"{key}: Croston / SBA / TSB (1-step forecast)", 360)
    f.add_bar(x=[str(p) for p in per], y=y, name="Actual", marker_color="#C9CCC9")
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
        rows.append({"Method": nm, "MAE": metrics.mae(y[start:], fcs), "Bias%": metrics.bias_pct(y[start:], fcs) * 100,
                     "Mean forecast": fcs.mean(), "Mean actual": y[start:].mean()})
    st.dataframe(pd.DataFrame(rows).style.format({"MAE": "{:,.1f}", "Bias%": "{:+.1f}", "Mean forecast": "{:,.1f}", "Mean actual": "{:,.1f}"}),
                 hide_index=True, use_container_width=True)
    note("Croston forecasts the <i>average demand rate</i>, not which month will have an order. Classic Croston is biased high → SBA multiplies by (1 − α/2). "
         "TSB lowers the forecast gradually when no orders arrive — suited to items going obsolete. K04 (Tết gift basket) is intermittent BUT seasonal: Croston ignores seasonality!")

with tab3:
    st.write("APS software usually picks the 'best-fit' on in-sample error. The table below compares that choice with the choice based on 6 test months.")

    @st.cache_data(show_spinner=False)
    def bestfit_table():
        rows = []
        for key in ser_port.sort_values("value_12m_trieu", ascending=False).series.head(10):
            s = clean_series(key).values
            tr = s[:-TEST_MONTHS]
            _, tbl = evaluation.best_fit(s, TEST_MONTHS)
            ins = {}
            for nm, fn in {"SES": lambda yy: smoothing.ses(yy, 6), "Holt": lambda yy: smoothing.holt(yy, 6),
                           "Multiplicative Holt-Winters": lambda yy: smoothing.holt_winters(yy, 6, 12, "mul")}.items():
                r = fn(tr)
                ins[nm] = metrics.wmape(tr[12:], r.fitted[12:])
            bi = min(ins, key=ins.get)
            out_of_bi = tbl.set_index("method").loc[bi, "WMAPE%"]
            rows.append({"Series": key, "IN-sample best fit": bi, "In-sample WMAPE": ins[bi], "→ its test WMAPE": out_of_bi,
                         "OUT-of-sample best fit": tbl.iloc[0]["method"], "WMAPE test": tbl.iloc[0]["WMAPE%"]})
        return pd.DataFrame(rows)

    _, ser_port = portfolio(0.8, 0.95, 0.15, 0.35)
    bt = bestfit_table()
    st.dataframe(bt.style.format({c: "{:.1f}" for c in bt.columns if "WMAPE" in c}), hide_index=True, use_container_width=True)
    note("When the software reports a 'best-fit', ask: (1) was it chosen on in-sample or out-of-sample error? (2) at which horizon/lag? (3) was it compared with Naive? "
         "(4) how often is the model re-selected — re-selecting every month easily makes the forecast 'jump' (nervousness).")

with tab4:
    st.write("Academic extension — seasonal ARIMA (SARIMA) on log(demand), orders chosen by AIC **on train only**, compared with Holt-Winters.")
    key = pick_series(default="B01|GT", key="s7d")
    if st.button("Run the SARIMA grid (≈ 10–20 seconds)"):
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
        add_line(f, y.index, y.values, "Actual", INK)
        add_line(f, y.index[-TEST_MONTHS:], sar, "SARIMA", CAT[3], mode="lines+markers")
        add_line(f, y.index[-TEST_MONTHS:], hw, "Multiplicative Holt-Winters", CAT[0], mode="lines+markers")
        shade_test(f, y.index)
        st.plotly_chart(f, use_container_width=True)
        st.dataframe(metric_table([{"Method": "SARIMA", **metrics.summary(te, sar, tr, 12)},
                                   {"Method": "Multiplicative Holt-Winters", **metrics.summary(te, hw, tr, 12)}]), hide_index=True, use_container_width=True)
        note("With 30 months of data, a model with more parameters doesn't automatically win (the lesson of the M-Competitions). "
             "The data-leakage trap: choosing the ARIMA orders by AIC on ALL the data and only then splitting off the test set.")
