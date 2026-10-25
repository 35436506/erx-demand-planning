import numpy as np
import pandas as pd
import plotly.graph_objects as go
import statsmodels.api as sm
import streamlit as st

from lab_common import CAT, INK, add_line, clean_series, fig_base, load_all, note, page, pick_series

page(6, "Hồi quy, giá & khuyến mãi",
     "Tự chọn biến giải thích, đọc hệ số – R² – p-value, tách baseline/uplift và kiểm chứng đề xuất khuyến mãi bằng lãi gộp.")
D = load_all()
cal = D["calendar"].set_index("month")
promo = D["promo_calendar"]
m = D["sku_master"].drop_duplicates("planning_item").set_index("planning_item")
mt_keys = [k for k in (D["demand_clean"]["item"] + "|" + D["demand_clean"]["channel"]).drop_duplicates() if k.endswith("MT") and not k.startswith(("N06", "K04"))]
key = pick_series("Chuỗi kênh MT (nhiều khuyến mãi)", "K01|MT", options=mt_keys)
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
vars_all = {"t": "Xu hướng (t)", "khai_giang": "Mùa khai giảng (T8–T9)", "mua_he": "Mùa hè (T4–T7)", "tet_pre": "Tỷ trọng trước Tết",
            "promo_depth": "Mức giảm giá KM", "post_promo": "Tháng sau KM"}
default = ["t", "khai_giang", "tet_pre", "promo_depth", "post_promo"] if it == "K01" else ["t", "tet_pre", "promo_depth", "post_promo"]
chosen = st.multiselect("Biến giải thích (chỉ biến BIẾT TRƯỚC được tại thời điểm dự báo)", list(vars_all), default=default, format_func=vars_all.get)
if not chosen:
    st.stop()
X = allX.iloc[:len(y)][chosen]
model = sm.OLS(y.values, sm.add_constant(X)).fit()
tab1, tab2, tab3 = st.tabs(["Hệ số & độ khớp", "Baseline / uplift", "Kiểm chứng đợt khuyến mãi"])
with tab1:
    c1, c2 = st.columns([1.3, 1])
    with c1:
        t = pd.DataFrame({"Biến": ["Hệ số chặn"] + [vars_all[c] for c in chosen], "Hệ số": model.params.values, "Sai số chuẩn": model.bse.values,
                          "t": model.tvalues.values, "p-value": model.pvalues.values})
        t["Giữ biến?"] = np.where(t["p-value"] < 0.05, "Giữ", "Cân nhắc")
        st.dataframe(t.style.format({"Hệ số": "{:,.1f}", "Sai số chuẩn": "{:,.1f}", "t": "{:.2f}", "p-value": "{:.3f}"}), hide_index=True, use_container_width=True)
    with c2:
        st.metric("R²", f"{model.rsquared:.3f}")
        st.metric("R² hiệu chỉnh", f"{model.rsquared_adj:.3f}")
        if "promo_depth" in chosen:
            st.metric("Mỗi 10% giảm giá ≈", f"+{model.params['promo_depth'] * 0.1:,.0f} thùng/tháng")
    note("Thêm biến luôn làm R² tăng — nhìn R² hiệu chỉnh và p-value. Biến 'tháng sau KM' có ý nghĩa kinh doanh rõ (khách đã găm hàng) "
         "nên có thể giữ dù p hơi cao — miễn là ghi lý do.")
with tab2:
    Xc = sm.add_constant(X)
    fit = model.predict(Xc)
    Xb = Xc.copy()
    for c_ in ("promo_depth", "post_promo"):
        if c_ in Xb:
            Xb[c_] = 0
    base = model.predict(Xb)
    f = fig_base(f"{key}: thực tế, mô hình, baseline", 420)
    f.add_trace(go.Scatter(x=[str(p) for p in per], y=base, name="Baseline", fill="tozeroy", line=dict(color="#9FD8B4"), fillcolor="rgba(1,174,66,0.10)"))
    add_line(f, per, y.values, "Thực tế", INK)
    add_line(f, per, fit, "Mô hình", CAT[0], dash="dash")
    pm = [str(p) for p in per if pk.get(str(p), 0) > 0]
    f.add_scatter(x=pm, y=[y[pd.Period(p, 'M')] for p in pm], mode="markers", name="Tháng KM", marker=dict(size=10, color=CAT[2]))
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
    st.markdown("**Lịch KM 10–12/2026:** " + (", ".join(f"{r.month}: giảm {r.depth:.0%} ({r.mechanic}) – Marketing kỳ vọng +{r.marketing_expected_uplift:.0%}"
                                                   for r in planned.itertuples()) or "không có"))
    tbl = pd.DataFrame({"Tháng": fut.index, "Baseline": bc.values, "Dự báo (mô hình)": fc.values})
    tbl["Uplift %"] = (tbl["Dự báo (mô hình)"] / tbl["Baseline"] - 1) * 100
    st.dataframe(tbl.style.format({"Baseline": "{:,.0f}", "Dự báo (mô hình)": "{:,.0f}", "Uplift %": "{:+.0f}%"}), hide_index=True, use_container_width=True)
    st.markdown("#### Lãi gộp: có nên chạy khuyến mãi?")
    c1, c2, c3, c4 = st.columns(4)
    price = c1.number_input("Giá NPP (k/thùng)", value=float(m.loc[it, "price_k"]))
    cost = c2.number_input("Giá vốn (k/thùng)", value=float(m.loc[it, "cost_k"]))
    depth = c3.slider("Mức giảm", 0.05, 0.40, float(planned.depth.iloc[0]) if len(planned) else 0.20, 0.05)
    fee = c4.number_input("Phí trưng bày (triệu đ)", value=60.0) * 1000
    co_fund = st.slider("Nhà cung cấp/brand đồng tài trợ (% giá)", 0.0, 0.25, 0.0, 0.05)
    b0 = float(bc.iloc[1])
    up_units = model.params.get("promo_depth", 0) * depth
    dip = model.params.get("post_promo", 0)
    gp_no = 2 * b0 * (price - cost)
    gp_yes = (b0 + up_units) * (price * (1 - depth + co_fund) - cost) + (b0 + dip) * (price - cost) - fee
    k1, k2, k3 = st.columns(3)
    k1.metric("Lãi gộp 2 tháng — không KM", f"{gp_no / 1000:,.0f} tr.đ")
    k2.metric("Lãi gộp 2 tháng — có KM", f"{gp_yes / 1000:,.0f} tr.đ", delta=f"{(gp_yes - gp_no) / 1000:+,.0f} tr.đ")
    be = (b0 * (depth - co_fund) * price + fee - dip * (price - cost)) / (b0 * (price * (1 - depth + co_fund) - cost)) if price * (1 - depth + co_fund) > cost else np.inf
    k3.metric("Uplift hòa vốn", f"{be * 100:,.0f}%" if np.isfinite(be) else "Không thể hòa vốn")
    note("Đóng vai: Marketing nói 'giảm 25%, chắc chắn tăng 110%'. Demand Planner hỏi: đợt tương tự trước tăng bao nhiêu? bao nhiêu cửa hàng trưng bày? "
         "ăn lạm sang mã nào? ai trả phần giảm giá? → rồi trả lời bằng bảng trên.")
