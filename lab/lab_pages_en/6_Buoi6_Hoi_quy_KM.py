import numpy as np
import pandas as pd
import plotly.graph_objects as go
import statsmodels.api as sm
import streamlit as st

from lab_common_en import CAT, INK, add_line, clean_series, fig_base, load_all, note, page, pick_series

page(6, "Regression, price & promotions",
     "Choose your explanatory variables, read the coefficients – R² – p-values, split baseline/uplift and test a promotion proposal on gross margin.")
D = load_all()
cal = D["calendar"].set_index("month")
promo = D["promo_calendar"]
m = D["sku_master"].drop_duplicates("planning_item").set_index("planning_item")
mt_keys = [k for k in (D["demand_clean"]["item"] + "|" + D["demand_clean"]["channel"]).drop_duplicates() if k.endswith("MT") and not k.startswith(("N06", "K04"))]
key = pick_series("MT channel series (many promotions)", "K01|MT", options=mt_keys)
it, ch = key.split("|")
y = clean_series(key)
per = y.index
pk = promo[(promo.sku == it) & (promo.channel == ch)].set_index("month").depth


def X_of(periods):
    idx = [str(p) for p in periods]
    X = pd.DataFrame(index=idx)
    X["t"] = np.arange(1, len(idx) + 1)
    X["khai_giang"] = [1 if p.month in (8, 9) else 0 for p in periods]
    X["mua_he"] = [1 if p.month in (4, 5, 6, 7) else 0 for p in periods]
    X["tet_pre"] = cal.loc[idx, "tet_pre_share"].values
    d = np.array([pk.get(i, 0.0) for i in idx])
    X["promo_depth"] = d
    X["post_promo"] = np.r_[0, (d[:-1] > 0).astype(int)]
    return X


allX = X_of(list(per) + list(pd.period_range("2026-10", "2026-12", freq="M")))
vars_all = {"t": "Trend (t)", "khai_giang": "Back-to-school season (Aug–Sep)", "mua_he": "Summer (Apr–Jul)", "tet_pre": "Pre-Tết share",
            "promo_depth": "Promotion discount depth", "post_promo": "Post-promotion month"}
default = ["t", "khai_giang", "tet_pre", "promo_depth", "post_promo"] if it == "K01" else ["t", "tet_pre", "promo_depth", "post_promo"]
chosen = st.multiselect("Explanatory variables (only variables KNOWN in advance at forecast time)", list(vars_all), default=default, format_func=vars_all.get)
if not chosen:
    st.stop()
X = allX.iloc[:len(y)][chosen]
model = sm.OLS(y.values, sm.add_constant(X)).fit()
tab1, tab2, tab3 = st.tabs(["Coefficients & fit", "Baseline / uplift", "Testing the promotion"])
with tab1:
    c1, c2 = st.columns([1.3, 1])
    with c1:
        t = pd.DataFrame({"Variable": ["Intercept"] + [vars_all[c] for c in chosen], "Coefficient": model.params.values, "Standard error": model.bse.values,
                          "t": model.tvalues.values, "p-value": model.pvalues.values})
        t["Keep variable?"] = np.where(t["p-value"] < 0.05, "Keep", "Reconsider")
        st.dataframe(t.style.format({"Coefficient": "{:,.1f}", "Standard error": "{:,.1f}", "t": "{:.2f}", "p-value": "{:.3f}"}), hide_index=True, use_container_width=True)
    with c2:
        st.metric("R²", f"{model.rsquared:.3f}")
        st.metric("Adjusted R²", f"{model.rsquared_adj:.3f}")
        if "promo_depth" in chosen:
            st.metric("Each 10% discount ≈", f"+{model.params['promo_depth'] * 0.1:,.0f} cases/month")
    note("Adding variables always raises R² — look at adjusted R² and p-values. The 'post-promotion month' variable has clear business meaning (customers have stocked up) "
         "so it can be kept even if p is a little high — as long as the reason is recorded.")
with tab2:
    Xc = sm.add_constant(X)
    fit = model.predict(Xc)
    Xb = Xc.copy()
    for c_ in ("promo_depth", "post_promo"):
        if c_ in Xb:
            Xb[c_] = 0
    base = model.predict(Xb)
    f = fig_base(f"{key}: actual, model, baseline", 420)
    f.add_trace(go.Scatter(x=[str(p) for p in per], y=base, name="Baseline", fill="tozeroy", line=dict(color="#9FD8B4"), fillcolor="rgba(1,174,66,0.10)"))
    add_line(f, per, y.values, "Actual", INK)
    add_line(f, per, fit, "Model", CAT[0], dash="dash")
    pm = [str(p) for p in per if pk.get(str(p), 0) > 0]
    f.add_scatter(x=pm, y=[y[pd.Period(p, 'M')] for p in pm], mode="markers", name="Promotion months", marker=dict(size=10, color=CAT[2]))
    st.plotly_chart(f, use_container_width=True)
with tab3:
    fut = allX.iloc[len(y):][chosen]
    fc = model.predict(sm.add_constant(fut, has_constant="add"))
    fb = fut.copy()
    for c_ in ("promo_depth", "post_promo"):
        if c_ in fb:
            fb[c_] = 0
    bc = model.predict(sm.add_constant(fb, has_constant="add"))
    planned = promo[(promo.sku == it) & (promo.channel == ch) & (promo.month.between("2026-10", "2026-12"))]
    st.markdown("**Promotion calendar Oct–Dec 2026:** " + (", ".join(f"{r.month}: discount {r.depth:.0%} ({r.mechanic}) – Marketing expects +{r.marketing_expected_uplift:.0%}"
                                                   for r in planned.itertuples()) or "none"))
    tbl = pd.DataFrame({"Month": fut.index, "Baseline": bc.values, "Forecast (model)": fc.values})
    tbl["Uplift %"] = (tbl["Forecast (model)"] / tbl["Baseline"] - 1) * 100
    st.dataframe(tbl.style.format({"Baseline": "{:,.0f}", "Forecast (model)": "{:,.0f}", "Uplift %": "{:+.0f}%"}), hide_index=True, use_container_width=True)
    st.markdown("#### Gross margin: should we run the promotion?")
    c1, c2, c3, c4 = st.columns(4)
    price = c1.number_input("Distributor price (k/case)", value=float(m.loc[it, "price_k"]))
    cost = c2.number_input("Unit cost (k/case)", value=float(m.loc[it, "cost_k"]))
    depth = c3.slider("Discount depth", 0.05, 0.40, float(planned.depth.iloc[0]) if len(planned) else 0.20, 0.05)
    fee = c4.number_input("Display fee (VND million)", value=60.0) * 1000
    co_fund = st.slider("Supplier/brand co-funding (% of price)", 0.0, 0.25, 0.0, 0.05)
    b0 = float(bc.iloc[1])
    up_units = model.params.get("promo_depth", 0) * depth
    dip = model.params.get("post_promo", 0)
    gp_no = 2 * b0 * (price - cost)
    gp_yes = (b0 + up_units) * (price * (1 - depth + co_fund) - cost) + (b0 + dip) * (price - cost) - fee
    k1, k2, k3 = st.columns(3)
    k1.metric("2-month gross margin — no promotion", f"{gp_no / 1000:,.0f} VND m")
    k2.metric("2-month gross margin — with promotion", f"{gp_yes / 1000:,.0f} VND m", delta=f"{(gp_yes - gp_no) / 1000:+,.0f} VND m")
    be = (b0 * (depth - co_fund) * price + fee - dip * (price - cost)) / (b0 * (price * (1 - depth + co_fund) - cost)) if price * (1 - depth + co_fund) > cost else np.inf
    k3.metric("Break-even uplift", f"{be * 100:,.0f}%" if np.isfinite(be) else "Cannot break even")
    note("Role-play: Marketing says '25% off, a guaranteed 110% lift'. The Demand Planner asks: how much did similar past events lift? how many stores have displays? "
         "which items get cannibalised? who pays for the discount? → then answer with the table above.")
