# Luna — ứng dụng desktop Windows

MVP local-first bằng Python/PySide6, giao diện tiếng Việt. Không phải web app. Bản này hoạt động offline với dữ liệu mẫu; không mở Zalo/eOffice, không kết nối Firebase, không gọi OpenAI và không phát sinh phí API.

## Chạy trên Windows

Cần Python 3.12+ (64-bit). Trong PowerShell tại thư mục repo:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python -m pip install -e .
.\.venv\Scripts\python -m luna
```

Dependency duy nhất trực tiếp: `PySide6-Essentials==6.12.0`. Không cần Playwright hoặc trình duyệt cho bản mock. Chưa kiểm chứng native Windows/DPAPI; đã kiểm tra GUI Qt offscreen trên Linux.

## Các màn hình

- **Chat:** phản hồi mock; yêu cầu có “tổng hợp”/“báo cáo” tạo báo cáo theo nhóm và ngày đang chọn. Không suy luận bằng AI thật.
- **Zalo / Tệp:** chọn đúng một trong ba nhóm allowlist, lọc ngày, xem tin nhắn mẫu, chọn ảnh/PDF mẫu để lưu. File mẫu độc lập với thời gian tin nhắn.
- **Báo cáo:** lịch sử local được đọc lại sau khi mở app; xem nguồn tin nhắn và xuất TXT/JSON.
- **eOffice:** bảng thống kê hai hồ sơ mẫu; chọn hồ sơ/trường, nhập giá trị mới và xem đối chiếu. Preview mất hiệu lực khi đổi lựa chọn/nội dung. Không có nút submit hoạt động.
- **Hàng đợi offline:** task, report, file metadata, preview/approval và audit; trạng thái pending_sync là chưa gửi RTDB. Không có sync worker.
- **Cấu hình:** Zalo, eOffice, model, Firebase và thư mục OneDrive. Chọn thư mục có sẵn, bấm kiểm tra rồi lưu cấu hình local. Có thể bỏ chọn nhóm để chặn thao tác mẫu tương ứng.

## Thử luồng hoàn chỉnh

1. Trong Cấu hình, chọn thư mục local thử nghiệm. Nếu nằm trong OneDrive, client OneDrive có thể tự upload file; app không gọi API OneDrive.
2. Trong Zalo/Tệp, chọn nhóm và khoảng ngày hôm qua–hôm nay; đọc tin nhắn mẫu.
3. Chọn file mẫu và xác nhận lưu; tạo báo cáo rồi xuất TXT/JSON.
4. Xem metadata/hàng đợi. Mỗi file có tên riêng và SHA-256, không ghi đè. Không tự xóa khi gần đầy; dừng ghi nếu còn dưới dung lượng file + 100 MiB. Không đo được quota OneDrive cloud.
5. Trong eOffice, chọn hồ sơ/trường và nhập đề xuất; bấm preview. Không có thay đổi nào trên website thật.

## Cấu hình và dữ liệu local

Không có đường dẫn tài khoản cá nhân hoặc Firebase project cụ thể trong source. `.env.example` chỉ mô tả tên biến; app không tự đọc `.env`.

- `LUNA_OUTPUT_DIR`: thư mục local đã chọn (ví dụ BAO CAO trong OneDrive). Settings lưu lựa chọn cho lần chạy sau.
- `LUNA_STATE_DIR`: tùy chọn thư mục cache/settings/outbox; mặc định `%LOCALAPPDATA%/Luna/offline` trên Windows. Giữ ngoài repo và OneDrive vì chứa nội dung local.
- `FIREBASE_PROJECT_ID`, `FIREBASE_DATABASE_URL`: nhập trong Settings hoặc môi trường; chỉ lưu cấu hình, không gọi Firebase.
- Model key: chỉ nhập khi cần; nút lưu dùng Windows DPAPI, không lưu plaintext, không đọc credential hiện có. Linux vô hiệu hóa nút lưu key. Chưa có chức năng dùng/giải mã key để gọi API.

RTDB vẫn là canonical DB khi được triển khai và cấp quyền. JSON local là dữ liệu chờ đồng bộ, không phải một DB cloud thay thế. File binary không vào RTDB. Lưu local không chứng minh đã đồng bộ OneDrive.

## Những chức năng chưa hoạt động thật

Mở QR Zalo, kiểm tra session, đọc website, Firebase read/sync, model API test và mọi ghi/gửi/trình/xóa/upload ngoài hệ thống đều chưa triển khai hoặc bị khóa. Các nút có nhãn mock chỉ kiểm tra mẫu/local. Checkbox “đã đăng nhập” không chứng minh phiên hợp lệ. ChatGPT subscription không cung cấp API miễn phí.

Cần kiểm chứng Windows, triển khai browser connectors đọc-only, xác minh Firebase auth/Rules, và phê duyệt API budget trước khi mở live. Không tự thay đổi Rules/billing.

## Kiểm tra đã thực hiện

Cài editable package và `pip check`; GUI Qt offscreen/event loop; chat/tổng hợp, lọc ngày; khôi phục lịch sử/cấu hình; PNG hợp lệ; lưu PNG/PDF/TXT/JSON và đối chiếu SHA-256; chống trùng tên/path traversal; chặn thiếu dung lượng; nhóm không khớp/trùng/bị bỏ quyền; URL lỗi và preview invalidation. Smoke script dùng thư mục tạm, không thêm test suite vào repo. Chưa kiểm tra Windows native, QR, OneDrive sync hoặc dịch vụ live.
