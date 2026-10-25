/* =====================================================================
   CẤU HÌNH WEBSITE — giảng viên chỉ cần sửa file này sau khi deploy.
   Sửa xong, deploy lại (hoặc sửa trực tiếp trên GitHub) là website cập nhật.
   ===================================================================== */
window.ERX_CONFIG = {
  // Tên lớp / khóa (hiện ở trang chủ). Ví dụ: "K1 · 11/2026"
  COHORT: "",

  // Ngày học. Cách 1: điền ngày Buổi 1 (YYYY-MM-DD) → các buổi sau tự cách nhau 7 ngày.
  START_DATE: "",
  // Cách 2: điền đủ 10 ngày (ghi đè START_DATE), ví dụ:
  // SESSION_DATES: ["2026-11-07","2026-11-14","2026-11-21","2026-11-28","2026-12-05","2026-12-12","2026-12-19","2027-01-09","2027-01-16","2027-01-23"],
  SESSION_DATES: [],
  SESSION_TIME: "19:30–22:30 (giờ Việt Nam)",
  SESSION_TIME_EN: "19:30–22:30 (Vietnam time, UTC+7)",   // giờ học hiển thị trên trang tiếng Anh

  // Ngôn ngữ mặc định khi học viên mở trang lần đầu: "vi" hoặc "en".
  // (Sau khi học viên bấm VI/EN, lựa chọn được nhớ trong trình duyệt — dùng chung cho mọi module ERX.)
  DEFAULT_LANG: "vi",

  // Địa chỉ Forecasting Lab (Streamlit). Deploy cả gói lên Railway: ĐỂ TRỐNG — website tự tìm Lab ở <thư mục module>/lab/.
  // Khi gắn vào website ERX chung mà Lab chạy ở dịch vụ riêng: điền URL, ví dụ "https://erx-dpf-lab.up.railway.app".
  LAB_URL: "",

  // Link nộp bài (Google Classroom, Moodle, Google Form, ...). Để trống thì ẩn nút "Nộp bài".
  LMS_URL: "",

  // Email / kênh liên hệ giảng viên (hiện ở chân trang). Để trống thì ẩn.
  CONTACT: "thu.minh090997@gmail.com",

  // Link phòng học trực tuyến (Zoom/Meet/Teams). Để trống thì ẩn.
  CLASSROOM_URL: ""
};
