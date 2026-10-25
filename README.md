# ERX · Demand Planning & Forecasting in Practice — module song ngữ (Việt | English)

Website học viên 10 buổi, 6 trò chơi mô phỏng và Forecasting Lab — **mọi trang có nút VI | EN**. Bản này không chứa tài liệu dành cho giảng viên.

- **Deploy demo (Railway):** GitHub → Railway, website và Lab chung một link. Xem từng bước trong [HUONG_DAN_DEPLOY.md](HUONG_DAN_DEPLOY.md).
- **Gắn vào website ERX chung:** xem [INTEGRATION.md](INTEGRATION.md) — module là một thư mục tĩnh, chạy ở bất kỳ đường dẫn nào (ví dụ `/demand-planning/`).
- **Cấu hình lớp:** sửa `site/config.js` (ngày học, link nộp bài, ngôn ngữ mặc định, `LAB_URL`).

| Thư mục | Nội dung |
| --- | --- |
| `site/` | Module web đã dựng: `vi/`, `en/`, `assets/`, `files/`, `config.js`, `module.json` |
| `lab/` | Forecasting Lab (Streamlit) — bản Việt và bản Anh (`*_en`, tự sinh) |
| `deploy/`, `Dockerfile`, `railway.json` | Cấu hình chạy trên Railway |
| `src/pages/`, `i18n/`, `tools/` | Nguồn tiếng Việt, bảng dịch và lệnh dựng lại bản song ngữ |

Chạy thử trên máy có Docker: `docker build -t erx-dpf . && docker run -p 8080:8080 erx-dpf`, rồi mở http://localhost:8080 (bản gắn thử dưới đường dẫn con: http://localhost:8080/demand-planning/).
