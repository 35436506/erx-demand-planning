import numpy as np
import pandas as pd
import streamlit as st

from dpkit import cleaning
from lab_common import CAT, INK, add_line, fig_base, load_all, note, page, pick_series

page(2, "Hiểu và làm sạch dữ liệu nhu cầu",
     "Doanh số ≠ xuất kho ≠ đơn hàng ≠ nhu cầu. Trang này chạy đúng quy trình làm sạch của lớp và in nhật ký điều chỉnh cho từng chuỗi.")
D = load_all()
h, m, so = D["sales_history"], D["sku_master"], D["sellout_dms"]

cases = {"N01|GT": "Đẩy hàng cuối quý + hết hàng (có sell-out DMS)", "N03|GT": "Lỗi đơn vị tính", "S04|GT": "Hết hàng, GT không ghi đơn bị từ chối",
         "B01|MT": "Hết hàng, MT có PO", "S06|GT": "Đổi mã S06 → S06N", "S02|MT": "Thiếu dữ liệu", "S01|GT": "Sự kiện thật (tin đồn tăng giá)",
         "K02|GT": "Hàng trả về sau Tết", "N05|MT": "Sản phẩm mới (lấp đầy kênh)"}
c1, c2 = st.columns([1.2, 1])
with c1:
    key = pick_series("Chọn chuỗi (gợi ý các ca có vấn đề)", "N01|GT", options=list(cases) + [k for k in
                      (D["demand_clean"]["item"] + "|" + D["demand_clean"]["channel"]).drop_duplicates() if k not in cases])
with c2:
    st.markdown(f"**Vấn đề cài sẵn:** {cases.get(key, '—')}")
it, ch = key.split("|")
log = cleaning.AdjustmentLog()
c = cleaning.clean_series(h, it, ch, m, so, log)

f = fig_base(f"{key}: số ghi nhận vs nhu cầu đã làm sạch", 400)
add_line(f, c.index, c.recorded.values, "Xuất kho (ghi nhận)", CAT[2])
if ch == "MT":
    add_line(f, c.index, c.orders.values, "Đơn hàng (PO)", CAT[1], dash="dot")
add_line(f, c.index, c.demand.values, "Nhu cầu ước tính", INK, width=3)
if c.returns.sum() > 0:
    add_line(f, c.index, c.returns.values, "Hàng trả về", CAT[4], dash="dash")
adj = c[c.rule != ""]
f.add_scatter(x=list(adj.index), y=adj.demand.values, mode="markers", name="Tháng đã điều chỉnh",
              marker=dict(size=11, color="#C2185B", symbol="circle-open", line=dict(width=2)))
st.plotly_chart(f, use_container_width=True)

c1, c2 = st.columns([1.3, 1])
with c1:
    st.markdown("#### Nhật ký điều chỉnh")
    lg = log.to_frame()
    if len(lg):
        st.dataframe(lg.rename(columns={"series": "Chuỗi", "month": "Tháng", "original": "Số gốc", "adjusted": "Số mới", "rule": "Quy tắc",
                                        "reason": "Lý do", "evidence": "Bằng chứng"}).style.format({"Số gốc": "{:,.0f}", "Số mới": "{:,.0f}"}, na_rep="(trống)"),
                     hide_index=True, use_container_width=True, height=300)
    else:
        st.info("Chuỗi này không cần điều chỉnh theo các quy tắc chuẩn.")
with c2:
    st.markdown("#### Phát hiện bất thường")
    k = st.slider("Hệ số IQR (k)", 1.0, 3.0, 1.5, 0.25)
    flags, lo, hi = cleaning.iqr_flags(c.recorded.values, k)
    st.write(f"Ngưỡng IQR: **{lo:,.0f} – {hi:,.0f}** → gắn cờ: {', '.join(np.array(c.index)[flags]) or 'không có'}")
    rf = cleaning.robust_flags(c.recorded.values, [int(x[-2:]) for x in c.index])
    st.write(f"Cờ MAD (robust, k=3,5): {', '.join(np.array(c.index)[rf]) or 'không có'}")
    note("Cờ ≠ lỗi. Câu hỏi đầu tiên luôn là <i>'chuyện gì đã xảy ra?'</i> — hỏi kho, Sales, IT. "
         "Lỗi dữ liệu thì sửa; sự kiện thật thì <b>giữ</b> ở cột nhu cầu, nhưng loại khỏi baseline khi tính mùa vụ.")

st.markdown("#### Cây quyết định: tháng bán 0 (hoặc rất thấp) — vì sao?")
st.dataframe(pd.DataFrame([
    ["Tồn kho = 0 / có ngày hết hàng", "Đứt hàng", "Phục hồi nhu cầu (PO hoặc quy đổi theo ngày có hàng)"],
    ["Mã mới xuất hiện cùng lúc mã cũ biến mất", "Đổi mã", "Nối lịch sử theo planning_item"],
    ["Trạng thái 'ngừng bán' trong sku_master", "Ngừng bán", "Không dự báo tiếp; chuyển nhu cầu sang mã thay thế nếu có"],
    ["Ô trống / lỗi truyền dữ liệu", "Thiếu dữ liệu", "Nội suy, đánh dấu là ước tính"],
    ["Mã B2B/HoReCa, nhiều tháng 0 xen kẽ", "Nhu cầu rời rạc thật", "Giữ nguyên 0; dùng Croston/SBA (Buổi 7)"],
], columns=["Dấu hiệu", "Chẩn đoán", "Xử lý"]), hide_index=True, use_container_width=True)
