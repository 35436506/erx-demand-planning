import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from dpkit_en import baseline, inventory, smoothing
from lab_common_en import BRAND, CAT, INK, add_line, clean_series, fig_base, load_all, note, page, pick_series

page(9, "From forecast to inventory, early warning and S&OP",
     "Forecast error becomes safety stock; the in-month sales rate becomes an early warning; unconstrained demand meets capacity in S&OP.")
D = load_all()
m = D["sku_master"].set_index("sku")
tab1, tab2, tab3, tab4 = st.tabs(["Safety Stock & ROP", "In-month early warning", "Shelf life (FEFO)", "Capacity & Volume→Value"])

with tab1:
    c1, c2, c3 = st.columns([2, 1, 1])
    with c1:
        key = pick_series(default="B01|GT")
    meth = c2.selectbox("Forecasting method", ["SES", "Damped Holt", "Seasonal Naive", "Multiplicative Holt-Winters"], index=3)
    sl = c3.slider("Service level", 0.80, 0.995, 0.95, 0.005)
    it = key.split("|")[0]
    y = clean_series(key, "demand_ex_event").values
    fn = {"SES": lambda yy, h: smoothing.ses(yy, h).forecast, "Damped Holt": lambda yy, h: smoothing.holt(yy, h, damped=True).forecast,
          "Seasonal Naive": lambda yy, h: baseline.seasonal_naive(yy, h), "Multiplicative Holt-Winters": lambda yy, h: smoothing.holt_winters(yy, h, 12, "mul").forecast}[meth]
    errs = np.array([y[t] - fn(y[:t], 1)[0] for t in range(len(y) - 12, len(y))])
    sigma = float(np.sqrt(np.mean(errs ** 2)))
    sd = float(np.std(y[-12:], ddof=1))
    lt_w = st.slider("Lead time (weeks)", 1, 12, int(m.loc[it if it in m.index else "S06", "lead_time_weeks"]))
    L = lt_w / 4.33
    fc1 = float(fn(y, 1)[0])
    ss = inventory.safety_stock(sigma, L, sl)
    ss_bad = inventory.safety_stock(sd, L, sl)
    k = st.columns(5)
    k[0].metric("Error σ (out of sample)", f"{sigma:,.0f}")
    k[1].metric("12-month demand SD", f"{sd:,.0f}")
    k[2].metric("Safety Stock (error σ)", f"{ss:,.0f}")
    k[3].metric("SS if demand SD is used", f"{ss_bad:,.0f}", delta=f"{(ss_bad / ss - 1) * 100:+.0f}%", delta_color="inverse")
    k[4].metric("ROP", f"{fc1 * L + ss:,.0f}")
    cost = float(m.loc[it if it in m.index else "S06", "cost_k"])
    curve = inventory.service_tradeoff(sigma, L, cost, 0.20, levels=np.round(np.arange(0.80, 0.996, 0.005), 3))
    f = fig_base("Service level ↔ safety-stock capital", 340, "SS capital (VND million)")
    add_line(f, (curve.service_level * 100).round(1), curve.von_ton_kho_trieu, "SS capital", CAT[0], mode="lines")
    f.add_vline(x=sl * 100, line_dash="dash", line_color=INK)
    f.update_layout(xaxis_title="Target service level (%)")
    st.plotly_chart(f, use_container_width=True)
    note("SS = z × σ × √L. σ must be the OUT-OF-SAMPLE forecast error — the part the stock really has to absorb. Using the demand SD (which includes forecastable seasonality) "
         "inflates SS, especially for seasonal items like B01. The service level is a business decision (S&OP), not a default number.")

with tab2:
    im = D["in_month_tracking"].copy()
    c1, c2 = st.columns(2)
    day = c1.slider("Days of October elapsed", 7, 14, 14, help="Actual data is available up to day 14")
    thr = c2.slider("Alert threshold ±", 0.05, 0.30, 0.15, 0.01)
    rows = []
    for r in im.itertuples():
        a = r.actual_day1_14 * day / 14
        al = inventory.run_rate_alert(a, day, 31, r.consensus_forecast_month, thr)
        rows.append({"Series": f"{r.sku}|{r.channel}", "October consensus": r.consensus_forecast_month, "Sold to date": a,
                     "Ratio": al["run_rate_ratio"], "Full-month projection": al["projected_month"], "Alert": al["flag"]})
    t = pd.DataFrame(rows).sort_values("Ratio")
    f = fig_base("Sales rate / expected ratio", 420)
    colors = [CAT[4] if v > 1 + thr else (CAT[2] if v < 1 - thr else "#C9CCC9") for v in t["Ratio"]]
    f.add_trace(go.Bar(x=t["Series"], y=t["Ratio"], marker_color=colors))
    f.add_hrect(y0=1 - thr, y1=1 + thr, fillcolor="#EAF7EF", opacity=0.6, line_width=0)
    f.update_layout(showlegend=False, hovermode="closest")
    st.plotly_chart(f, use_container_width=True)
    st.dataframe(t[t["Alert"] != "Normal"].style.format({"October consensus": "{:,.0f}", "Sold to date": "{:,.0f}", "Ratio": "{:.0%}", "Full-month projection": "{:,.0f}"}),
                 hide_index=True, use_container_width=True)
    note("An early warning is not for changing the forecast straight away but for <b>asking</b> within 24 hours: weather? competitors? an unannounced promotion? → then decide "
         "whether to move stock between channels, change production orders or update next month's forecast. Small items fluctuate randomly a lot — set thresholds by ABC group.")

with tab3:
    inv = D["inventory_snapshot"]
    dc = D["demand_clean"]
    thr = st.slider("MT only accepts goods with ≥ … shelf life remaining", 0.5, 0.9, 0.67, 0.01)
    daily = (dc[dc.month >= "2026-07"].groupby("item").demand.sum() / 92).rename(index={"S06": "S06N"}).to_dict()
    risk = inventory.shelf_life_risk(inv, daily, thr)
    risk["Value (VND m)"] = [r.qty * float(m.loc[r.sku, "cost_k"]) / 1000 for r in risk.itertuples()]
    st.metric("Value of stock at risk", f"{risk.loc[risk.rui_ro == 'ALERT', 'Value (VND m)'].sum():,.0f} VND million")
    st.dataframe(risk.rename(columns={"sku": "SKU", "batch": "Batch", "qty": "Quantity", "remaining_days": "Days remaining",
                                      "ngay_ban_het_luy_ke": "Days to sell through (cumulative)", "ngay_con_ban_duoc": "Sellable days left", "rui_ro": "Risk"})
                 .style.format({"Quantity": "{:,.0f}", "Days to sell through (cumulative)": "{:,.0f}", "Sellable days left": "{:,.0f}", "Value (VND m)": "{:,.0f}"})
                 .map(lambda v: "color:#C2185B;font-weight:600" if v == "ALERT" else "", subset=["Risk"]),
                 hide_index=True, use_container_width=True, height=420)

with tab4:
    cap = D["capacity"]
    line = st.selectbox("Production line", cap.line.unique())
    members = {"Packet-noodle line (N01,N02,N04,N05,N06)": ["N01", "N02", "N04", "N05"], "Cup-noodle line (N03)": ["N03"],
               "Sauce bottling line (S01,S02,S06N)": ["S01", "S02", "S06"]}[line]
    H = 6
    dem = np.zeros(H)
    for it in members:
        for ch in ("GT", "MT"):
            try:
                yy = clean_series(f"{it}|{ch}", "demand_ex_event").values
            except KeyError:
                continue
            if len(yy) == 0:
                continue
            fcst = smoothing.holt_winters(yy, H, 12, "mul").forecast if len(yy) >= 24 else smoothing.ses(yy, H).forecast
            dem += np.maximum(fcst, 0)
    cl = cap[cap.line == line].set_index("month")
    mos = [str(p) for p in pd.period_range("2026-10", periods=H, freq="M")]
    reg = cl.loc[mos, "regular_capacity"].values
    ot = cl.loc[mos, "overtime_capacity"].values
    f = fig_base(f"{line}: unconstrained demand (statistical) vs capacity", 380)
    f.add_bar(x=mos, y=reg, name="Regular capacity", marker_color="#C9CCC9")
    f.add_bar(x=mos, y=ot, name="Overtime", marker_color="#E6E8E6")
    add_line(f, mos, dem, "Unconstrained demand", INK, mode="lines+markers")
    f.update_layout(barmode="stack")
    st.plotly_chart(f, use_container_width=True)
    gap = dem - reg - ot
    t = pd.DataFrame({"Month": mos, "Demand": dem, "Maximum capacity": reg + ot, "Short (+)/surplus (−)": gap})
    st.dataframe(t.style.format({c: "{:,.0f}" for c in t.columns if c != "Month"}), hide_index=True, use_container_width=True)
    price = float(m.loc[members[0], "price_k"])
    st.write(f"Revenue at risk if the shortfall isn't handled (price of {members[0]}): **{np.maximum(gap, 0).sum() * price / 1000:,.0f} VND million**")
    note("The 5-step S&OP cycle: data gathering → Demand Review → <b>Supply Review</b> (the gateway to Production Planning) → Pre-S&OP (options & trade-offs) "
         "→ Executive S&OP (decisions). Reports always separate <b>unconstrained demand</b> from the <b>constrained plan</b>.")
