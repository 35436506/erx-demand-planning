import numpy as np
import streamlit as st

from dpkit import baseline, metrics
from lab_common import CAT, INK, add_line, fig_base, metric_table, note, page, pick_series, clean_series, shade_test

page(3, "Dự báo đầu tiên và đo sai số",
     "Ba phương pháp mốc (Naive, Seasonal Naive, MA) và sáu thước đo. Mọi mô hình ở các buổi sau phải thắng các mốc này trên dữ liệu TEST.")
c1, c2, c3 = st.columns([2, 1, 1])
with c1:
    key = pick_series(default="B01|GT")
with c2:
    n_test = st.slider("Số tháng test", 3, 12, 6)
with c3:
    n_ma = st.slider("MA: số tháng", 2, 12, 3)
y = clean_series(key)
tr, te = y.values[:-n_test], y.values[-n_test:]
fcs = {"Naive": baseline.naive(tr, n_test), "Seasonal Naive": baseline.seasonal_naive(tr, n_test, 12),
       f"MA({n_ma})": baseline.moving_average(tr, n_test, n_ma)}

f = fig_base(f"{key} — train {len(tr)} tháng, test {n_test} tháng", 400)
add_line(f, y.index, y.values, "Thực tế", INK)
for (nm, fc), colr in zip(fcs.items(), CAT):
    add_line(f, y.index[-n_test:], fc, nm, colr, mode="lines+markers")
shade_test(f, y.index, n_test)
st.plotly_chart(f, use_container_width=True)

rows = [{"Phương pháp": nm, **{k: v for k, v in metrics.summary(te, fc, tr).items()}} for nm, fc in fcs.items()]
st.dataframe(metric_table(rows), hide_index=True, use_container_width=True)
c1, c2 = st.columns(2)
with c1:
    note("<b>Mỗi thước đo trả lời một câu hỏi.</b> ME/Bias: lệch về một phía? · MAE: sai bao nhiêu đơn vị? · RMSE: phạt sai số lớn "
         "(dùng cho Safety Stock) · MAPE: sai bao nhiêu % (thiên lệch ở mã nhỏ) · WMAPE: % có trọng số sản lượng · MASE: tốt hơn Naive bao nhiêu (<1 là tốt hơn).")
with c2:
    note("<b>Bẫy MAPE:</b> chọn H02|GT hoặc K04|MT để xem MAPE 'nổ' vì có tháng thực tế rất nhỏ hoặc bằng 0. "
         "Không có 'MAPE chuẩn' cho mọi SKU — so với mốc Naive của chính SKU đó mới công bằng.")
with st.expander("Vì sao không chia train/test ngẫu nhiên?"):
    st.write("Chuỗi thời gian có thứ tự. Chia ngẫu nhiên cho mô hình 'nhìn thấy' tháng sau để dự báo tháng trước — kết quả đẹp giả. "
             "Luôn cắt theo thời gian: phần đầu để ước lượng, phần cuối giấu đi để chấm.")
