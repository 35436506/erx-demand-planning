# ERX Forecasting Lab (Streamlit)

Phòng thực hành trực quan cho khóa **Demand Planning & Forecasting in Practice** (10 buổi). Mỗi trang ứng với một buổi học, dùng chung thư viện `dpkit/` với code bài giảng và cùng công thức với file Excel.

## Chạy trên máy cá nhân
```bash
pip install -r requirements.txt
streamlit run app.py
```
Trình duyệt mở tại http://localhost:8501.

## Deploy lên Streamlit Community Cloud (miễn phí)
1. Tạo repository GitHub (nên để **Private** nếu sau này thay bằng dữ liệu thật đã ẩn danh), đẩy **toàn bộ thư mục này** lên gốc repo:
   `app.py`, `home.py`, `lab_common.py`, `lab_pages/`, `dpkit/`, `data/`, `assets/`, `.streamlit/`, `requirements.txt`.
2. Vào https://share.streamlit.io → **Create app** → chọn repo, nhánh `main`, *Main file path* = `app.py` → **Deploy**.
3. Python 3.11 hoặc 3.12 (Advanced settings). Lần đầu cài thư viện mất 2–4 phút.
4. Chia sẻ link cho học viên. Nếu repo private: thêm email học viên ở *Settings → Sharing*, hoặc để app *public* nhưng repo private.

## Cấu trúc
| Thư mục / file | Vai trò |
|---|---|
| `app.py` | Điểm vào, khai báo 11 trang (st.navigation) |
| `home.py` | Trang chủ: bản đồ khóa học, từ điển dữ liệu |
| `lab_pages/` | 10 trang theo buổi |
| `lab_common.py` | Nạp dữ liệu (cache), giao diện ERX, hàm vẽ |
| `dpkit/` | Thư viện tính toán (giống hệt `07_Python_Code/dpkit`) |
| `data/` | Bộ dữ liệu case Mekong Bloom Foods (CSV) + `mau_tai_len_CSV.csv` để thử chức năng tải dữ liệu riêng |

## Thay bằng dữ liệu thật (đã ẩn danh)
Giữ nguyên tên file và tên cột trong `data/` (xem `data/data_dictionary.csv`), chạy lại `07_Python_Code/make_clean_dataset.py` để tạo `demand_clean.csv`, rồi chép vào `data/`. Trang Buổi 10 cũng cho phép tải CSV (`month, series, demand`) mà không cần sửa code.

## Bảo mật
Không tải dữ liệu chưa ẩn danh lên app công khai. Chức năng tải CSV xử lý trong phiên làm việc, không lưu lại trên máy chủ.
