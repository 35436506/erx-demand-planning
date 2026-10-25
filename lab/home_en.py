"""ERX Forecasting Lab — trang chủ.  Chạy:  streamlit run app.py"""
import pandas as pd
import streamlit as st

from lab_common_en import SESSIONS, load_all, note, page

page(None, "Forecasting Lab",
     "The interactive practice room that accompanies the <b>Demand Planning & Forecasting in Practice</b> course by ERX. "
     "Each page matches one session and uses <b>exactly the same formulas</b> as the slides and Excel files (the <code>dpkit</code> library), "
     "on the same Mekong Bloom Foods case data (a fictional company).")

D = load_all()
h, m, dc = D["sales_history"], D["sku_master"], D["demand_clean"]
c1, c2, c3, c4 = st.columns(4)
c1.metric("SKUs (planning items)", m.planning_item.nunique())
c2.metric("SKU × channel series", (dc["item"] + dc["channel"]).nunique())
c3.metric("History", "36 months", help=f"{h.month.min()} → {h.month.max()}")
c4.metric("Forecast horizon", "12 months", help="10/2026 → 09/2027")

st.subheader("Course map")
rows = []
parts = {1: "Foundations", 2: "Foundations", 3: "Foundations", 4: "Core techniques", 5: "Core techniques", 6: "Core techniques",
         7: "Core techniques", 8: "Process & decisions", 9: "Process & decisions", 10: "Process & decisions"}
tools = {1: "CV by level · the Forecast Challenge game", 2: "Shipments vs demand · IQR · adjustment log",
         3: "Naive / Seasonal Naive / MA · 6 error metrics", 4: "α slider · Holt · rolling by lag",
         5: "Seasonal indices · Holt-Winters · the moving-Tết tool", 6: "Regression with your choice of variables · baseline/uplift · promotion gross margin",
         7: "ABC-XYZ · ADI/CV² map · Croston/SBA/TSB · best fit · SARIMA (extension)", 8: "FVA · Tracking Signal · consensus simulation",
         9: "Safety Stock/ROP · service-level curve · early warning · shelf life · capacity",
         10: "Run the whole cycle for portfolio P0–P6 or your own data · export the handover file"}
for k, v in SESSIONS.items():
    rows.append({"Session": k, "Stage": parts[k], "Topic": v, "Tools in the Lab": tools[k]})
st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
st.caption("Open the pages in the left sidebar. Everything runs only in your session; no data is stored on the server.")

st.subheader("Data used in the Lab")
cA, cB = st.columns([1.2, 1])
with cA:
    st.dataframe(m[["sku", "name", "category", "uom", "price_k", "shelf_life_days", "lead_time_weeks", "status"]]
                 .rename(columns={"sku": "Code", "name": "Name", "category": "Group", "uom": "Unit", "price_k": "Distributor price (k)",
                                  "shelf_life_days": "Shelf life (days)", "lead_time_weeks": "Lead time (weeks)", "status": "Status"}),
                 hide_index=True, use_container_width=True, height=420)
with cB:
    dd = D["data_dictionary"]
    st.dataframe(dd[["table", "field", "meaning"]].rename(columns={"table": "Table", "field": "Field", "meaning": "Meaning"}),
                 hide_index=True, use_container_width=True, height=420)
note("<b>Ground rules for the Lab:</b> (1) always compare with the Naive benchmark; (2) choose parameters on train, score on test; "
     "(3) read the code in the <code>dpkit/</code> folder if you want to know what a button does inside — it is the same kind of algorithm "
     "that runs in the 'statistical baseline' layer of commercial APS software.")
