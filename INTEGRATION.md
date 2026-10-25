# Gắn module Demand Planning vào website ERX chung

Tài liệu này dành cho người dựng website trung tâm ERX và các anh chị phụ trách module khác (Production Planning, Procurement, Warehouse…). Mục tiêu: mỗi module là **một thư mục tĩnh tự chứa**, song ngữ Việt – Anh, gắn vào website chung chỉ bằng cách chép thư mục và thêm một dòng menu.

## 1. Cấu trúc module

```
site/                      ← toàn bộ module, chép nguyên thư mục này
├── index.html             ← bộ chọn ngôn ngữ: chuyển sang vi/ hoặc en/
├── vi/  *.html            ← 28 trang tiếng Việt
├── en/  *.html            ← 28 trang tiếng Anh, cùng tên file
├── assets/                ← CSS, JS, font, logo, pdf.js (dùng chung cho 2 ngôn ngữ)
│   ├── css/erx-tokens.css ← biến màu, font, nút VI | EN — dùng chung cho mọi module ERX
│   └── js/games/en/       ← bản tiếng Anh của 6 trò chơi (tự sinh)
├── files/                 ← slide, Excel, giáo trình (tài liệu tải về — hiện là tiếng Việt)
├── config.js              ← cấu hình lớp: ngày học, link nộp bài, LAB_URL, ngôn ngữ mặc định
├── module.json            ← "hồ sơ" module cho website chung đọc (tên, trang, ngôn ngữ, liên kết module khác)
└── 404.html
```

Mọi liên kết trong trang đều là **đường dẫn tương đối**, nên module chạy được ở bất kỳ đường dẫn nào: `/`, `/demand-planning/`, `/khoa-hoc/dp/`… Bản demo Railway chứng minh điều này: cùng một thư mục được phục vụ ở cả `/` và `/demand-planning/`.

## 2. Gắn vào website chung (3 bước)

1. Chép thư mục `site/` vào website chung, đổi tên thành `demand-planning/` (tên gợi ý trong `module.json → suggestedMountPath`).
2. Thêm vào menu website chung một liên kết tới `demand-planning/` — trang `index.html` của module tự chuyển sang tiếng Việt hoặc tiếng Anh theo lựa chọn của người học.
3. Forecasting Lab (Streamlit) không phải file tĩnh, chọn một trong hai cách:
   - **Cách 1 – Lab là dịch vụ riêng** (đơn giản nhất): deploy repo này lên Railway như bản demo, rồi trong `demand-planning/config.js` điền `LAB_URL: "https://<ten-dich-vu>.up.railway.app/lab"`.
   - **Cách 2 – Lab chung tên miền**: máy chủ web chung chuyển tiếp `demand-planning/lab/*` tới Streamlit (`--server.baseUrlPath lab`) và **bỏ tiền tố** `/demand-planning` trước khi chuyển. Mẫu cấu hình Caddy: khối `handle_path /demand-planning/*` trong `deploy/Caddyfile`. Khi đó để trống `LAB_URL` — trang tự tìm Lab ở `demand-planning/lab/`.

## 3. Quy ước dùng chung cho mọi module ERX

| Hạng mục | Quy ước |
| --- | --- |
| Ngôn ngữ | Thư mục `vi/` và `en/` cùng tên file. Nút **VI \| EN** ở góc phải thanh đầu trang, giữ nguyên trang, tham số và `#neo` khi chuyển |
| Ghi nhớ ngôn ngữ | `localStorage["erx.lang"] = "vi" \| "en"` — module nào cũng đọc/ghi cùng khóa này, nên người học chọn tiếng Anh một lần là cả website chung theo tiếng Anh |
| Thẻ HTML | `<html lang="vi\|en">` và `<link rel="alternate" hreflang=…>` trỏ sang trang tương ứng |
| Giao diện | Dùng `assets/css/erx-tokens.css` (màu, font, sáng/tối). Sáng/tối lưu ở `localStorage["erx_theme"]` |
| Lab / ứng dụng | Nhận tham số `?lang=vi\|en` trên URL |
| Hồ sơ module | Mỗi module có `module.json` (id, tên 2 thứ tiếng, trang, ngôn ngữ, module liên quan). Website chung có thể đọc file này để tự dựng menu |
| Tài liệu tải về | Nếu chưa có bản tiếng Anh, trang tiếng Anh ghi rõ *(Vietnamese)* cạnh liên kết |

## 4. Nối dữ liệu với các module khác

Module Demand Planning bàn giao **nhu cầu đồng thuận chưa giới hạn năng lực**, kèm σ sai số và Safety Stock, qua file Excel tải từ **Lab → Buổi 10** (sheet `Ban_giao_PP` / bản tiếng Anh `Handover_PP`):

| Cột (VI) | Cột (EN) | Ý nghĩa |
| --- | --- | --- |
| Chuỗi | Series | Mã hàng kế hoạch \| kênh, ví dụ `N01\|GT` |
| Tháng | Month | `YYYY-MM`, 10/2026 → 09/2027 |
| Thống kê | Statistical | Dự báo thống kê |
| Nhu cầu đồng thuận (chưa giới hạn) | Consensus demand (unconstrained) | **Số Production Planning dùng để lập MPS** |
| σ sai số | Error σ | Độ lệch chuẩn sai số ngoài mẫu |
| Safety Stock | Safety Stock | Tồn kho an toàn theo mức phục vụ đã chọn |
| Phương pháp | Method | Mô hình đã chọn |
| Giả định | Assumption | Giả định điều chỉnh (nếu có) |

- **Production Planning:** MPS/MRP từ cột nhu cầu đồng thuận; năng lực dây chuyền nằm trong `lab/data/capacity.csv`.
- **Procurement:** nhu cầu nguyên vật liệu đi qua MRP từ cùng số nhu cầu đồng thuận.
- **Warehouse:** Safety Stock/ROP và cảnh báo hạn dùng FEFO ở Lab → Buổi 9; tồn kho đầu kỳ trong `lab/data/inventory_snapshot.csv`.

Mọi module dùng chung bộ dữ liệu case **Mekong Bloom Foods** (`lab/data/`, từ điển dữ liệu `data_dictionary.csv`).

## 5. Sửa nội dung và dựng lại bản song ngữ

Nguồn tiếng Việt là bản gốc; bản tiếng Anh được **sinh tự động** từ bảng dịch, không sửa tay.

| Muốn sửa | Sửa ở đâu | Sau đó chạy |
| --- | --- | --- |
| Nội dung trang web | `src/pages/*.html` (tiếng Việt) và câu dịch trong `i18n/html_en.json` | `python3 tools/build_site.py` |
| Chữ trong trò chơi | `site/assets/js/games/*.js` và `i18n/js/<tên>.tsv` | `python3 tools/build_site.py` |
| Lab | `lab/home.py`, `lab/lab_pages/*.py`, `lab/dpkit/*.py` và `i18n/lab/*.tsv` | `python3 tools/build_lab.py` |

Hai lệnh build kiểm tra và **báo lỗi nếu còn chữ tiếng Việt chưa dịch** trên trang tiếng Anh, hoặc câu dịch làm hỏng cấu trúc thẻ HTML. Cần Python 3.10+ và `pip install beautifulsoup4 pandas`.

Liên hệ module Demand Planning: Thư Nguyễn · thu.minh090997@gmail.com
