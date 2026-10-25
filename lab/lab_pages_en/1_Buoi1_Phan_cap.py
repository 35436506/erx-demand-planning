import numpy as np
import pandas as pd
import streamlit as st

from dpkit_en import hierarchy, metrics
from lab_common_en import BRAND, CAT, INK, add_line, fig_base, label, load_all, note, page, raw_series, series_keys

page(1, "Why forecast demand & the forecasting hierarchy",
     "Same data — at which level is it most stable? And how well do people forecast 'by eye' compared with the simplest method?")
D = load_all()
tab1, tab2, tab3 = st.tabs(["CV by forecasting level", "Forecast Challenge game", "Planning chain & time fences"])

with tab1:
    tbl = hierarchy.cv_by_level(D["sales_history"], "shipments", D["sku_master"])
    c1, c2 = st.columns([1, 1.4])
    with c1:
        st.dataframe(tbl.rename(columns={"cap": "Level", "so_chuoi": "Series", "CV_trung_vi": "Median CV", "CV_trung_binh": "Mean CV"})
                     .style.format({"Median CV": "{:.2f}", "Mean CV": "{:.2f}"}), hide_index=True, use_container_width=True)
        note("CV = standard deviation / mean. The more you aggregate, the more random deviations cancel out (the portfolio effect, ≈ divide by √n). "
             "→ Capacity/budget plans are set at group level; the MPS and deliveries need SKU × channel level.")
    with c2:
        import plotly.graph_objects as go
        f = fig_base("Median CV by level", 330)
        f.add_trace(go.Bar(x=tbl.cap, y=tbl.CV_trung_vi, marker_color=BRAND, text=[f"{v:.2f}" for v in tbl.CV_trung_vi], textposition="outside"))
        f.update_layout(showlegend=False, hovermode="closest")
        st.plotly_chart(f, use_container_width=True)
    h = D["sales_history"].merge(D["sku_master"][["sku", "category", "planning_item"]], on="sku")
    cats_ = sorted(h.category.unique())
    cat = st.selectbox("View a product group", cats_, index=cats_.index("Instant noodles"))
    g = h[h.category == cat]
    f = fig_base(f"{cat}: each SKU × channel vs the group total (normalised to mean = 1)", 380)
    for i, ((it, ch), x) in enumerate(g.groupby(["planning_item", "channel"])):
        s = x.groupby("month").shipments.sum()
        add_line(f, s.index, (s / s.mean()).values, f"{it}|{ch}", color="#C9CCC9", width=1)
    tot = g.groupby("month").shipments.sum()
    add_line(f, tot.index, (tot / tot.mean()).values, "Group total", color=INK, width=3)
    st.plotly_chart(f, use_container_width=True)

with tab2:
    st.markdown("**Rules:** look at the first 24 months, guess the next 3. After you submit, the Lab compares your score with *Naive* (last month's value).")
    opts = ["N02|GT", "S03|MT", "B02|GT", "K01|MT", "N04|GT", "S05|MT"]
    if "fc_round" not in st.session_state:
        st.session_state.fc_round = 0
    key = opts[st.session_state.fc_round % len(opts)]
    s = raw_series(key).dropna()
    hist, fut = s.iloc[:24], s.iloc[24:27]
    st.caption(f"Round {st.session_state.fc_round + 1}: an anonymous series (name revealed after you submit)")
    f = fig_base("24 months of history", 320)
    add_line(f, hist.index, hist.values, "History", INK, mode="lines+markers")
    st.plotly_chart(f, use_container_width=True)
    with st.form(f"guess_{st.session_state.fc_round}"):
        cols = st.columns(3)
        guesses = [cols[i].number_input(f"Guess {fut.index[i]}", min_value=0, value=int(hist.iloc[-1]), step=100) for i in range(3)]
        sub = st.form_submit_button("Submit guesses")
    if sub:
        naive = np.repeat(hist.iloc[-1], 3)
        you = metrics.wmape(fut.values, np.array(guesses))
        nv = metrics.wmape(fut.values, naive)
        c1, c2, c3 = st.columns(3)
        c1.metric("Your WMAPE", f"{you:.1f}%")
        c2.metric("WMAPE Naive", f"{nv:.1f}%")
        c3.metric("Result", "A draw — you haven't added value yet" if abs(you - nv) < 0.05 else ("You win!" if you < nv else "Naive wins"), delta=f"{nv - you:+.1f} % points")
        f = fig_base(f"Answer: {label(key)}", 320)
        add_line(f, s.index[:27], s.values[:27], "Actual", INK, mode="lines+markers")
        add_line(f, fut.index, guesses, "Your guess", CAT[2], mode="lines+markers")
        add_line(f, fut.index, naive, "Naive", CAT[0], dash="dot")
        st.plotly_chart(f, use_container_width=True)
        note("Common pattern: people overreact to the last month (chasing noise) or 'see' a trend that isn't there. "
             "That is why every method must be compared with the Naive benchmark — and every manual adjustment must be measured with FVA (Session 8).")
    if st.button("Next round ▶"):
        st.session_state.fc_round += 1
        st.rerun()

with tab3:
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("#### Which decisions use the forecast?")
        st.dataframe(pd.DataFrame([
            ["Weeks (1–8 weeks)", "SKU × warehouse × week", "Replenishment, trucks, delivery schedules", "Logistics, Sales Ops"],
            ["Months (3–18 months)", "SKU × channel × month", "S&OP, MPS, materials purchasing, inventory", "Demand/Supply Planning, Production, Procurement"],
            ["Years (1–3 years)", "Product group × month (value)", "Budget, capacity, investment", "Finance, leadership"],
        ], columns=["Horizon", "Level of detail", "Decision", "Users"]), hide_index=True, use_container_width=True)
        st.markdown("#### Four concepts that often get mixed up")
        st.dataframe(pd.DataFrame([
            ["Demand", "How much customers want to buy — including what they couldn't buy because of stock-outs"],
            ["Forecast", "An unbiased estimate of future demand, with its error"],
            ["Plan", "What we DECIDE to make/buy/ship (constrained by capacity, inventory)"],
            ["Target", "The number we WANT to reach — for motivation, not for ordering"],
        ], columns=["Concept", "Meaning"]), hide_index=True, use_container_width=True)
    with c2:
        st.markdown("#### Planning time fences")
        import plotly.graph_objects as go
        f = fig_base("", 230)
        for x0, x1, nm, colr in [(0, 1, "Frozen · month M+1", "#1F2421"), (1, 3, "Slushy · M+2–M+3", "#76777B"),
                                 (3, 12, "Liquid · M+4 onwards", "#01AE42")]:
            f.add_trace(go.Bar(x=[x1 - x0], y=["Plan"], base=[x0], orientation="h", name=nm, marker_color=colr, hovertemplate=nm))
        f.update_layout(barmode="stack", xaxis=dict(title="Months from today", dtick=1), hovermode="closest")
        st.plotly_chart(f, use_container_width=True)
        note("Planning chain: <b>Demand forecast → S&OP → MPS → MRP</b>. Session 10 hands the UNCONSTRAINED consensus demand number "
             "to the Production Planning module. Changing numbers inside the frozen zone = changing a locked production schedule → it needs an approval process.")
