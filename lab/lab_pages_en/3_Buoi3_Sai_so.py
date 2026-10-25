import numpy as np
import streamlit as st

from dpkit_en import baseline, metrics
from lab_common_en import CAT, INK, add_line, fig_base, metric_table, note, page, pick_series, clean_series, shade_test

page(3, "Your first forecast and measuring error",
     "Three benchmark methods (Naive, Seasonal Naive, MA) and six metrics. Every model in later sessions must beat these benchmarks on TEST data.")
c1, c2, c3 = st.columns([2, 1, 1])
with c1:
    key = pick_series(default="B01|GT")
with c2:
    n_test = st.slider("Test months", 3, 12, 6)
with c3:
    n_ma = st.slider("MA: months", 2, 12, 3)
y = clean_series(key)
tr, te = y.values[:-n_test], y.values[-n_test:]
fcs = {"Naive": baseline.naive(tr, n_test), "Seasonal Naive": baseline.seasonal_naive(tr, n_test, 12),
       f"MA({n_ma})": baseline.moving_average(tr, n_test, n_ma)}

f = fig_base(f"{key} — train {len(tr)} months, test {n_test} months", 400)
add_line(f, y.index, y.values, "Actual", INK)
for (nm, fc), colr in zip(fcs.items(), CAT):
    add_line(f, y.index[-n_test:], fc, nm, colr, mode="lines+markers")
shade_test(f, y.index, n_test)
st.plotly_chart(f, use_container_width=True)

rows = [{"Method": nm, **{k: v for k, v in metrics.summary(te, fc, tr).items()}} for nm, fc in fcs.items()]
st.dataframe(metric_table(rows), hide_index=True, use_container_width=True)
c1, c2 = st.columns(2)
with c1:
    note("<b>Each metric answers one question.</b> ME/Bias: skewed to one side? · MAE: off by how many units? · RMSE: penalises large errors "
         "(used for Safety Stock) · MAPE: off by what % (biased for small items) · WMAPE: volume-weighted % · MASE: how much better than Naive (<1 means better).")
with c2:
    note("<b>The MAPE trap:</b> choose H02|GT or K04|MT to see MAPE 'explode' because some actual months are tiny or zero. "
         "There is no 'standard MAPE' for every SKU — comparing with that SKU's own Naive benchmark is the fair test.")
with st.expander("Why not split train/test at random?"):
    st.write("Time series have an order. A random split lets the model 'see' later months when forecasting earlier ones — results that look good but are fake. "
             "Always split by time: the first part to estimate, the last part hidden for scoring.")
