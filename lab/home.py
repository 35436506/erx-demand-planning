"""ERX Forecasting Lab — trang chủ.  Chạy:  streamlit run app.py"""
import pandas as pd
import streamlit as st

from lab_common import SESSIONS, load_all, note, page

page(None, "Forecasting Lab",
     "Phòng thực hành trực quan đi kèm khóa <b>Demand Planning & Forecasting in Practice</b> của ERX. "
     "Mỗi trang ứng với một buổi học, dùng <b>đúng công thức</b> trong slide và file Excel (thư viện <code>dpkit</code>), "
     "trên cùng bộ dữ liệu case Mekong Bloom Foods (công ty giả định).")

D = load_all()
h, m, dc = D["sales_history"], D["sku_master"], D["demand_clean"]
c1, c2, c3, c4 = st.columns(4)
c1.metric("SKU (hàng kế hoạch)", m.planning_item.nunique())
c2.metric("Chuỗi SKU × kênh", (dc["item"] + dc["channel"]).nunique())
c3.metric("Lịch sử", "36 tháng", help=f"{h.month.min()} → {h.month.max()}")
c4.metric("Kỳ cần dự báo", "12 tháng", help="10/2026 → 09/2027")

st.subheader("Bản đồ khóa học")
rows = []
parts = {1: "Nền tảng", 2: "Nền tảng", 3: "Nền tảng", 4: "Kỹ thuật cốt lõi", 5: "Kỹ thuật cốt lõi", 6: "Kỹ thuật cốt lõi",
         7: "Kỹ thuật cốt lõi", 8: "Quy trình & quyết định", 9: "Quy trình & quyết định", 10: "Quy trình & quyết định"}
tools = {1: "CV theo cấp · trò chơi Forecast Challenge", 2: "Xuất kho vs nhu cầu · IQR · nhật ký điều chỉnh",
         3: "Naive / Seasonal Naive / MA · 6 thước đo sai số", 4: "Thanh trượt α · Holt · cuốn chiếu theo lag",
         5: "Chỉ số mùa vụ · Holt-Winters · công cụ Tết dịch tháng", 6: "Hồi quy tự chọn biến · baseline/uplift · lãi gộp KM",
         7: "ABC-XYZ · bản đồ ADI/CV² · Croston/SBA/TSB · best-fit · SARIMA (mở rộng)", 8: "FVA · Tracking Signal · mô phỏng đồng thuận",
         9: "Safety Stock/ROP · đường cong mức phục vụ · cảnh báo sớm · hạn dùng · năng lực",
         10: "Chạy cả chu kỳ cho portfolio P0–P6 hoặc dữ liệu của bạn · xuất file bàn giao"}
for k, v in SESSIONS.items():
    rows.append({"Buổi": k, "Chặng": parts[k], "Chủ đề": v, "Công cụ trong Lab": tools[k]})
st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
st.caption("Mở các trang ở thanh bên trái. Mọi thao tác chỉ chạy trên trình duyệt của bạn, không lưu dữ liệu lên máy chủ.")

st.subheader("Dữ liệu dùng trong Lab")
cA, cB = st.columns([1.2, 1])
with cA:
    st.dataframe(m[["sku", "name", "category", "uom", "price_k", "shelf_life_days", "lead_time_weeks", "status"]]
                 .rename(columns={"sku": "Mã", "name": "Tên", "category": "Nhóm", "uom": "ĐVT", "price_k": "Giá NPP (k)",
                                  "shelf_life_days": "Hạn dùng (ngày)", "lead_time_weeks": "Lead time (tuần)", "status": "Trạng thái"}),
                 hide_index=True, use_container_width=True, height=420)
with cB:
    dd = D["data_dictionary"]
    st.dataframe(dd[["table", "field", "meaning"]].rename(columns={"table": "Bảng", "field": "Trường", "meaning": "Ý nghĩa"}),
                 hide_index=True, use_container_width=True, height=420)
note("<b>Nguyên tắc dùng Lab:</b> (1) luôn so với mốc Naive; (2) chọn tham số trên train, chấm trên test; "
     "(3) đọc code trong thư mục <code>dpkit/</code> nếu muốn biết bên trong một nút bấm làm gì — đó là cùng loại thuật toán "
     "chạy trong tầng 'statistical baseline' của phần mềm APS thương mại.")
