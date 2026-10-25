import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from dpkit_en import metrics
from lab_common_en import CAT, INK, MUTED, add_line, fig_base, load_all, note, page

page(8, "Demand Review & Forecast Value Added",
     "Does each adjustment step (Sales, consensus) make the forecast better? Measured with FVA on the case's 460 real lag-1 forecasts (10/2025–09/2026).")
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
tab1, tab2, tab3 = st.tabs(["FVA waterfall", "Tracking Signal", "Simulating an adjustment rule"])
with tab1:
    c1, c2 = st.columns(2)
    scope = c1.radio("Scope", ["All", "Months WITH promotions", "Months WITHOUT promotions"], horizontal=True)
    cats = c2.multiselect("Filter channels", ["GT", "MT"], default=["GT", "MT"])
    d = fh[fh.channel.isin(cats)]
    if scope != "All":
        d = d[d.promo_flag == (1 if scope.startswith("Months WITH") else 0)]
    rows = metrics.fva(d.actual_shipments.values, {"Statistical": d.stat_forecast.values, "Sales": d.sales_input.values,
                                                   "Consensus": d.consensus.values}, naive=d.naive.values)
    t = pd.DataFrame(rows)
    t["vs"] = t["vs"].fillna("–")
    f = fig_base(f"WMAPE by step — {scope.lower()} ({len(d)} forecasts)", 380, "WMAPE %")
    colors = [MUTED, CAT[0], CAT[2], CAT[1]]
    f.add_trace(go.Bar(x=t.step, y=t["WMAPE%"], marker_color=colors, text=[f"{v:.1f}%" for v in t["WMAPE%"]], textposition="outside"))
    f.update_layout(showlegend=False, hovermode="closest")
    st.plotly_chart(f, use_container_width=True)
    st.dataframe(t.rename(columns={"step": "Step", "FVA_vs_prev_pp": "FVA vs previous step (% points)", "vs": "Compared with"})
                 .style.format({"WMAPE%": "{:.1f}", "Bias%": "{:+.1f}", "FVA vs previous step (% points)": "{:+.1f}"}, na_rep="–"),
                 hide_index=True, use_container_width=True)
    note("Read them together: (1) does the statistical forecast beat Naive? (2) is the Sales number positively biased (optimistic)? (3) in months WITH promotions the consensus step "
         "adds a lot of value — because there is real information; in months WITHOUT promotions manual adjustments usually make things worse. → Rule: adjust only with new information, record the reason, measure again.")
with tab2:
    keys = (fh.sku + "|" + fh.channel).drop_duplicates().tolist()
    key = st.selectbox("Series", keys, index=keys.index("N01|GT") if "N01|GT" in keys else 0)
    it, ch = key.split("|")
    d = fh[(fh.sku == it) & (fh.channel == ch)].sort_values("target_month")
    thr = st.slider("Alert threshold |TS|", 2.0, 6.0, 4.0, 0.5)
    f = fig_base(f"Tracking Signal — {key}", 360)
    for col_, nm, colr in [("sales_input", "Sales", CAT[2]), ("stat_forecast", "Statistical", CAT[0]), ("consensus", "Consensus", CAT[1])]:
        add_line(f, d.target_month, metrics.tracking_signal(d.actual_shipments, d[col_]), nm, colr, mode="lines+markers")
    f.add_hline(y=thr, line_dash="dash", line_color=INK)
    f.add_hline(y=-thr, line_dash="dash", line_color=INK)
    st.plotly_chart(f, use_container_width=True)
    note("TS = cumulative sum of errors / MAD. A TS drifting negative = the forecast is persistently HIGHER than actuals. Beyond the threshold → investigate: where does the optimism come from, "
         "has the model missed a trend?")
with tab3:
    st.write("Suppose the company adopts the rule: **accept Sales adjustments only when there is a promotion**, and keep the statistical number in other months. What would happen?")
    w = st.slider("In promotion months, take what % of the Sales − Statistical gap", 0, 100, 60, 10)
    sim = np.where(fh.promo_flag == 1, fh.stat_forecast + w / 100 * (fh.sales_input - fh.stat_forecast), fh.stat_forecast)
    a = fh.actual_shipments.values
    res = pd.DataFrame([{"Version": "Statistical", "WMAPE%": metrics.wmape(a, fh.stat_forecast), "Bias%": metrics.bias_pct(a, fh.stat_forecast) * 100},
                        {"Version": "Sales", "WMAPE%": metrics.wmape(a, fh.sales_input), "Bias%": metrics.bias_pct(a, fh.sales_input) * 100},
                        {"Version": "Consensus (what was actually done)", "WMAPE%": metrics.wmape(a, fh.consensus), "Bias%": metrics.bias_pct(a, fh.consensus) * 100},
                        {"Version": f"Simulated rule ({w}%)", "WMAPE%": metrics.wmape(a, sim), "Bias%": metrics.bias_pct(a, sim) * 100}])
    st.dataframe(res.style.format({"WMAPE%": "{:.1f}", "Bias%": "{:+.1f}"}), hide_index=True, use_container_width=True)
    note("This is an 'experiment' on past data — use the conclusion to propose a rule for the Demand Review, then track FVA for a few months before locking it in.")
