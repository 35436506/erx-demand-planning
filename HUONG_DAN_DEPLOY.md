# Hướng dẫn deploy website ERX DPF lên Railway qua GitHub

Website học viên (trang chủ, lịch học, slide, bài tập, trò chơi, thư viện) và Forecasting Lab chạy chung trên **một dịch vụ Railway**, lấy mã từ **một repository GitHub**. Mỗi lần sửa file trên GitHub, Railway tự deploy lại.

Bản này **song ngữ**: mọi trang có nút **VI | EN** ở góc phải thanh đầu trang; Lab có nút *Tiếng Việt / English* ở đầu thanh bên trái. Cùng một bản deploy còn chạy thử module dưới đường dẫn con `/demand-planning/` — đúng cách website ERX chung sẽ gắn module (xem `INTEGRATION.md`).

## Vì sao tải lên GitHub bị lỗi

Trang tải file của GitHub trên trình duyệt chỉ nhận **tối đa 100 file và 25 MiB mỗi file trong một lần**. Cả gói có khoảng 270 file, nặng khoảng 52 MB, trong đó 3 file giáo trình đã chiếm hơn 30 MB. Tải một lần nên trình duyệt báo quá nặng.

Có hai cách khắc phục, chọn một:

| Cách | Khi nào dùng | Gói cần tải |
| --- | --- | --- |
| **A. GitHub Desktop** (khuyến nghị) | Máy tính cài được phần mềm. Không giới hạn số file, một lần là xong | `ERX_DPF_Website_Railway.zip` |
| **B. Trình duyệt, chia 7 đợt** | Không cài được phần mềm | `ERX_DPF_GitHub_Upload_7_Dot.zip` |

## Chuẩn bị

1. Tài khoản GitHub: https://github.com/signup
2. Tài khoản Railway: https://railway.com → **Login** → chọn **GitHub** để đăng nhập bằng tài khoản GitHub.
3. Gói Railway: tài khoản mới có $5 dùng thử một lần. Gói **Hobby $5/tháng** (đã gồm $5 sử dụng) là đủ cho một lớp. Gói Free chỉ có 0,5 GB RAM cho mỗi dịch vụ, có thể không đủ cho Forecasting Lab.

---

## Cách A — GitHub Desktop (khuyến nghị)

1. Tải và cài GitHub Desktop: https://desktop.github.com → mở ứng dụng → **Sign in to GitHub.com**.
2. Giải nén `ERX_DPF_Website_Railway.zip`. Sẽ có thư mục `ERX_DPF_Website`, bên trong là `Dockerfile`, `railway.json`, `deploy`, `lab`, `site`, `src`, `i18n`, `tools`…
3. Trong GitHub Desktop: **File → Add local repository…** → **Choose…** → chọn thư mục `ERX_DPF_Website` → **Add repository**.
4. GitHub Desktop báo *"This directory does not appear to be a Git repository"* → bấm **create a repository** → giữ nguyên tên `ERX_DPF_Website` (hoặc đổi thành `erx-dpf-website`) → **Create repository**.
5. Nếu cột bên trái còn liệt kê file chưa commit: nhập Summary `Website ERX DPF` → **Commit to main**.
6. Bấm **Publish repository** → **giữ dấu tích "Keep this code private"** (để bảo vệ học liệu) → **Publish repository**.
7. Mở repository trên github.com (GitHub Desktop: **Repository → View on GitHub**). Ngay ở thư mục gốc phải thấy `Dockerfile`, `deploy`, `lab`, `site`. Không được có thêm một tầng thư mục bọc ngoài.

Xong. Sang **Bước Railway** ở dưới.

---

## Cách B — Trình duyệt, chia 7 đợt

### B1. Tạo repository trống

1. Mở https://github.com/new
2. **Repository name:** `erx-dpf-website` · chọn **Private** · **không** tích *Add a README file* → **Create repository**.

### B2. Tải lên từng đợt

Giải nén `ERX_DPF_GitHub_Upload_7_Dot.zip`, sẽ có 7 thư mục `Dot_1` … `Dot_7`. Mỗi thư mục đã có sẵn đúng đường dẫn con (ví dụ `site/files/docs/…`), nên kéo vào trang gốc của repository thì file tự vào đúng chỗ.

| Đợt | Nội dung | Số file | Dung lượng |
| --- | --- | --- | --- |
| Dot_1 | `Dockerfile`, `railway.json`, `.dockerignore`, tài liệu `.md`, `deploy/`, `lab/` | 83 | ~1 MB |
| Dot_2 | `site/vi/`, `site/en/` (56 trang), `site/index.html`, `404.html`, `config.js`, `module.json` | 60 | ~1 MB |
| Dot_3 | `site/assets/` (CSS, JS, font, logo), `src/`, `i18n/`, `tools/` | 88 | ~3 MB |
| Dot_4 | `site/files/` slide PDF, bài tập Excel, dữ liệu + tài liệu nhỏ trong `docs/` | 35 | ~14 MB |
| Dot_5 | `site/files/docs/ERX_DPF_Lecture_Notes.pdf` | 1 | ~12 MB |
| Dot_6 | `site/files/docs/ERX_Lecture_Notes.pdf` | 1 | ~7 MB |
| Dot_7 | `site/files/docs/ERX_DPF_Lecture_Notes.docx` | 1 | ~15 MB |

Với **mỗi đợt**, làm theo thứ tự:

1. Mở trang gốc của repository → **Add file → Upload files**. (Lần đầu, repository còn trống thì bấm link **uploading an existing file**.)
2. Mở thư mục `Dot_N` trên máy → **chọn tất cả bên trong** (Ctrl + A trên Windows, Cmd + A trên Mac). **Không** kéo chính thư mục `Dot_N`.
3. Kéo thả vào khung tải lên. Đợi đến khi danh sách file hiện đủ và thanh tiến trình chạy xong.
4. Ô *Commit changes* ghi `Đợt N` → **Commit changes**. Đợi trang quay về repository rồi mới làm đợt sau.

Lưu ý:
- **Trên Mac:** file `.dockerignore` (Dot_1) và thư mục `lab/.streamlit` bị ẩn. Nhấn **Cmd + Shift + .** trong Finder để hiện trước khi chọn. Trên Windows không cần làm gì.
- **Kiểm tra sau đợt 7:** thư mục `site/files/docs` trên GitHub phải có **13 file**, `site/files/slides` có **10 file**.

---

## Bước Railway — nối GitHub và deploy

1. Mở https://railway.com/new → chọn **GitHub Repository** (Deploy from GitHub repo).
2. Lần đầu, Railway yêu cầu cấp quyền GitHub: bấm **Configure GitHub App** → chọn tài khoản của bạn → **Only select repositories** → chọn repository vừa tạo → **Install & Authorize** (hoặc **Save**).
3. Quay lại Railway, tìm và bấm vào repository đó → **Deploy Now**.
4. Railway tự nhận `Dockerfile` (log build ghi *Using detected Dockerfile*). Build lần đầu mất 3–6 phút. Đợi trạng thái **Active / Deployed**.
5. Bấm vào dịch vụ → tab **Variables** → **New Variable**: tên `PORT`, giá trị `8080` → **Add**. Railway sẽ deploy lại.
6. Tab **Settings → Networking → Public Networking** → **Generate Domain** → khi được hỏi cổng thì nhập `8080`. Railway cấp link dạng `https://<tên>.up.railway.app`.
7. (Khuyến nghị) **Settings → Deploy → Healthcheck Path**: nhập `/`.

### Kiểm tra sau khi deploy

- [ ] Mở link Railway: tự chuyển sang `/vi/` và thấy trang chủ ERX.
- [ ] Bấm **EN** ở góc phải: chuyển sang trang tiếng Anh cùng nội dung; mở lại link gốc thì website nhớ tiếng Anh.
- [ ] Mục **Lịch học** mở được Buổi 1; slide hiện trong trình xem.
- [ ] Mục **Thư viện** mở được *Lecture Notes* (PDF).
- [ ] Mục **Trò chơi**: mở Beer Game, bấm *Xem máy tự chơi* thấy hai biểu đồ.
- [ ] Mở `https://<tên>.up.railway.app/lab/`: thấy Forecasting Lab với menu 10 buổi (lần đầu có thể mất 20–30 giây). Thêm `?lang=en` hoặc chọn *English* ở thanh bên trái → Lab chuyển sang tiếng Anh.
- [ ] Mở `https://<tên>.up.railway.app/demand-planning/`: module chạy y hệt dưới đường dẫn con (bản xem trước khi gắn vào website ERX chung).
- [ ] Mục **Tiến độ**: đánh dấu một ô, tải lại trang, ô vẫn được giữ.

---

## Cập nhật sau này

- **Ngày học, link nộp bài, email liên hệ, ngôn ngữ mặc định:** sửa file `site/config.js` ngay trên GitHub (mở file → biểu tượng bút chì → sửa → **Commit changes**). Railway tự deploy lại sau 2–4 phút.
- **Thay một tài liệu:** trên GitHub mở đúng thư mục (ví dụ `site/files/docs`) → **Add file → Upload files** → kéo file mới cùng tên → **Commit changes**.
- **Dùng GitHub Desktop:** chép file mới đè vào thư mục trên máy → **Commit to main** → **Push origin**.
- **Sửa chữ trên trang hoặc trong Lab:** sửa bản tiếng Việt và câu dịch rồi chạy lệnh dựng lại — xem mục 5 trong `INTEGRATION.md`. Không sửa tay các file trong `site/en/`, `site/vi/`, `lab/*_en`.

## Lỗi thường gặp

| Hiện tượng | Cách xử lý |
| --- | --- |
| GitHub báo file quá nặng hoặc quá nhiều file | Dùng Cách A, hoặc tải theo đúng 7 đợt ở Cách B |
| Railway báo *Dockerfile not found* / build bằng Railpack | `Dockerfile` không nằm ở thư mục gốc của repository (bị bọc trong `ERX_DPF_Website/`). Chuyển file ra gốc, hoặc thêm biến `RAILWAY_DOCKERFILE_PATH` = `ERX_DPF_Website/Dockerfile` |
| Link Railway báo *Application failed to respond* (502) | Kiểm tra biến `PORT` = `8080` và cổng của domain là `8080` |
| Trang web chạy nhưng `/lab/` báo lỗi hoặc trắng | Xem tab **Deployments → View Logs**. Nếu báo thiếu bộ nhớ (out of memory) thì nâng lên gói Hobby |
| Thư viện báo không tìm thấy file | Thiếu một đợt tải lên (thường là Dot_5–Dot_7). Kiểm tra `site/files/docs` đủ 13 file |
| Trang tiếng Anh vẫn hiện tiếng Việt / nút VI \| EN không thấy | Thiếu Dot_2 hoặc Dot_3. Kiểm tra `site/en` có 28 file |
| Sửa xong nhưng website vẫn hiện bản cũ | Trình duyệt giữ bộ nhớ đệm tối đa 1 ngày. Nhấn Ctrl + F5 (Mac: Cmd + Shift + R) |

## Liên kết

- GitHub — tạo repository: https://github.com/new
- GitHub Desktop: https://desktop.github.com
- Railway — tạo dự án mới: https://railway.com/new
- Railway — hướng dẫn bắt đầu: https://docs.railway.com/quick-start
- Railway — cách nhận Dockerfile: https://docs.railway.com/reference/dockerfiles
- Railway — bảng giá: https://docs.railway.com/pricing/plans

Liên hệ: Thư Nguyễn · thu.minh090997@gmail.com
