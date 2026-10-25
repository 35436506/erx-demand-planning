import numpy as np
import pandas as pd
import streamlit as st

from dpkit_en import cleaning
from lab_common_en import CAT, INK, add_line, fig_base, load_all, note, page, pick_series

page(2, "Understanding and cleaning demand data",
     "Sales ≠ shipments ≠ orders ≠ demand. This page runs the class's exact cleaning procedure and prints the adjustment log for each series.")
D = load_all()
h, m, so = D["sales_history"], D["sku_master"], D["sellout_dms"]

cases = {"N01|GT": "Quarter-end loading + stock-outs (DMS sell-out available)", "N03|GT": "Unit-of-measure error", "S04|GT": "Stock-outs; GT doesn't record refused orders",
         "B01|MT": "Stock-outs; MT has POs", "S06|GT": "Code change S06 → S06N", "S02|MT": "Missing data", "S01|GT": "A real event (price-rise rumour)",
         "K02|GT": "Post-Tết returns", "N05|MT": "New product (channel fill)"}
c1, c2 = st.columns([1.2, 1])
with c1:
    key = pick_series("Choose a series (suggested problem cases)", "N01|GT", options=list(cases) + [k for k in
                      (D["demand_clean"]["item"] + "|" + D["demand_clean"]["channel"]).drop_duplicates() if k not in cases])
with c2:
    st.markdown(f"**Built-in problem:** {cases.get(key, '—')}")
it, ch = key.split("|")
log = cleaning.AdjustmentLog()
c = cleaning.clean_series(h, it, ch, m, so, log)

f = fig_base(f"{key}: recorded numbers vs cleaned demand", 400)
add_line(f, c.index, c.recorded.values, "Shipments (recorded)", CAT[2])
if ch == "MT":
    add_line(f, c.index, c.orders.values, "Orders (PO)", CAT[1], dash="dot")
add_line(f, c.index, c.demand.values, "Estimated demand", INK, width=3)
if c.returns.sum() > 0:
    add_line(f, c.index, c.returns.values, "Returns", CAT[4], dash="dash")
adj = c[c.rule != ""]
f.add_scatter(x=list(adj.index), y=adj.demand.values, mode="markers", name="Adjusted months",
              marker=dict(size=11, color="#C2185B", symbol="circle-open", line=dict(width=2)))
st.plotly_chart(f, use_container_width=True)

c1, c2 = st.columns([1.3, 1])
with c1:
    st.markdown("#### Adjustment log")
    lg = log.to_frame()
    if len(lg):
        st.dataframe(lg.rename(columns={"series": "Series", "month": "Month", "original": "Original", "adjusted": "Adjusted", "rule": "Rule",
                                        "reason": "Reason", "evidence": "Evidence"}).style.format({"Original": "{:,.0f}", "Adjusted": "{:,.0f}"}, na_rep="(blank)"),
                     hide_index=True, use_container_width=True, height=300)
    else:
        st.info("This series needs no adjustment under the standard rules.")
with c2:
    st.markdown("#### Anomaly detection")
    k = st.slider("IQR multiplier (k)", 1.0, 3.0, 1.5, 0.25)
    flags, lo, hi = cleaning.iqr_flags(c.recorded.values, k)
    st.write(f"IQR thresholds: **{lo:,.0f} – {hi:,.0f}** → flagged: {', '.join(np.array(c.index)[flags]) or 'none'}")
    rf = cleaning.robust_flags(c.recorded.values, [int(x[-2:]) for x in c.index])
    st.write(f"MAD flags (robust, k=3.5): {', '.join(np.array(c.index)[rf]) or 'none'}")
    note("A flag ≠ an error. The first question is always <i>'what actually happened?'</i> — ask the warehouse, Sales, IT. "
         "Fix data errors; <b>keep</b> real events in the demand column, but exclude them from the baseline when computing seasonality.")

st.markdown("#### Decision tree: a month with zero (or very low) sales — why?")
st.dataframe(pd.DataFrame([
    ["Stock = 0 / stock-out days recorded", "Stock-out", "Restore demand (PO, or scale up by in-stock days)"],
    ["A new code appears as the old code disappears", "Code change", "Join history by planning_item"],
    ["Status 'discontinued' in sku_master", "Discontinued", "Stop forecasting; transfer demand to the replacement code if there is one"],
    ["Blank cell / data transfer error", "Missing data", "Interpolate, mark as an estimate"],
    ["B2B/HoReCa item, many zero months in between", "Genuinely intermittent demand", "Keep the zeros; use Croston/SBA (Session 7)"],
], columns=["Signal", "Diagnosis", "Action"]), hide_index=True, use_container_width=True)
