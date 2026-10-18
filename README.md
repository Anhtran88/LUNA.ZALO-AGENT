# Luna — ứng dụng desktop Windows

Ứng dụng Python/PySide6 local-first, giao diện tiếng Việt. Mock vẫn hoạt động offline. Browser read-only chỉ mở khi người dùng bấm nút; không có chức năng gửi tin, submit hoặc sửa website. Firebase và model API chưa kết nối.

## Cài và chạy trên Windows

Python 3.12+ 64-bit, PowerShell trong checkout:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python -m pip install -e .
.\.venv\Scripts\python -m playwright install chromium
.\.venv\Scripts\python -m luna
```

Dependency trực tiếp: PySide6-Essentials 6.12.0, Playwright 1.64.0. Chromium cần tải riêng; không tự cài browser lúc mở app. Browser thật chỉ hỗ trợ Windows, không mở tài khoản trong cloud Linux.

## Màn hình

- **Chat:** phản hồi mock; “tổng hợp”/“báo cáo” tạo báo cáo mẫu theo nhóm/ngày đang chọn. Không gọi AI.
- **Zalo / Tệp:** tin nhắn/file mẫu, lọc ngày, chọn ảnh/PDF để lưu. File mẫu độc lập với ngày.
- **Báo cáo:** lịch sử local, xuất TXT/JSON; báo cáo browser ghi rõ chỉ trích DOM đang tải, chưa tóm tắt AI.
- **eOffice:** bảng và preview chỉnh sửa dữ liệu mẫu. Preview mất hiệu lực khi đổi giá trị; không có thực thi ghi thật.
- **Hàng đợi offline:** metadata/task/report/audit/preview pending_sync. Chưa có Firebase sync worker.
- **Browser chỉ đọc:** kết quả từ cửa sổ browser người dùng đã mở; chọn/tải file và lưu báo cáo local.
- **Cấu hình:** nút mở browser, xác nhận login, kiểm tra read-only, allowlist, model key, Firebase config và thư mục local.

## Zalo QR và đọc-only — adapter thử nghiệm

1. Chọn thư mục đích có sẵn trong Cấu hình; lưu cấu hình. Thư mục trong OneDrive sẽ được client OneDrive đồng bộ, app không gọi API OneDrive.
2. Bấm **Mở Zalo Web / Quét QR**. Tự quét QR/OTP/CAPTCHA trong browser. App không xử lý thay.
3. Tự mở nhóm chính xác trên Zalo. Trong Cấu hình, chọn “Nhóm sẽ đọc”; lựa chọn này đồng bộ với tab Zalo/Tệp. Chỉ các nhóm đã đánh dấu cho phép mới xuất hiện. Nếu chỉ còn một nhóm được phép, app chọn nhóm đó; nếu bỏ quyền nhóm đang chọn và còn nhiều nhóm, phải chọn lại rõ ràng. Chỉ ba tên allowlist được phép; không tìm gần đúng.
4. Trong Cấu hình, đánh dấu đã đăng nhập rồi bấm **Kiểm tra nhóm đang mở / đọc read-only**.
5. Xem kết quả ở Browser chỉ đọc. Chọn file ảnh/PDF được nhận diện, xác nhận tải. Lưu báo cáo khi cần.

**Quan trọng:** selector DOM chưa được xác minh trên Zalo hiện hành/tài khoản thật. Adapter yêu cầu tên nhóm duy nhất trong danh sách DOM, header khớp; dùng `data-conversation-id` khi DOM cung cấp, hoặc dòng `.conv-item` có trạng thái selected rõ ràng bên trong `.msg-item[data-id]`. Tên trong header/phần tử ẩn bên ngoài danh sách không được tính thành nhóm trùng. Nếu thiếu/khác/trùng, app dừng; không đọc toàn trang thay thế. Zalo có thể không cung cấp các marker này, khi đó cần cập nhật adapter dựa trên UI được phép kiểm tra. Danh sách ảo chưa tải hết không chứng minh không có tên trùng ngoài DOM; người dùng phải chọn nhóm rõ ràng. Chưa tự cuộn, lấy đủ lịch sử hoặc lọc ngày cho nội dung thật.

Tải file chỉ hỗ trợ anchor `a[download]` rõ ràng trong vùng tin nhắn, host được phép, tên/snapshot còn khớp, file PNG/JPEG/PDF tối đa 25 MiB (kiểm tra kích thước sau browser download). Nút tải tùy biến, ảnh inline và file chỉ mở preview chưa được hỗ trợ. Không tự click menu/nút gần đúng. File lỗi/đổi nhóm dừng tải; đã lưu một phần trước lỗi sẽ vẫn còn, không tự tải lại.

## eOffice read-only

Bấm **Mở eOffice**, tự đăng nhập, trở về URL workflow đã duyệt. Đánh dấu đã đăng nhập rồi bấm **Đọc bảng thống kê read-only**. Chỉ đọc khi URL đúng, không còn password form và nhận diện đúng một bảng HTML có header. Thống kê hiện tại là số dòng bảng đang tải, không phải tổng nghiệp vụ qua nhiều trang. UI dùng iframe/custom grid hoặc nhiều bảng sẽ dừng để xác minh adapter. Preview chỉnh sửa vẫn chỉ dùng hồ sơ mẫu, chưa ánh xạ record thật; không submit/save.

## Cấu hình, session và file

- Thư mục xuất: chọn trong Settings hoặc `LUNA_OUTPUT_DIR`; không có đường dẫn tài khoản cá nhân hard-code.
- Settings/outbox: `LUNA_STATE_DIR` hoặc `%LOCALAPPDATA%/Luna/offline`. Giữ ngoài repo/OneDrive.
- Browser profile và key: **cố định** `%LOCALAPPDATA%/Luna/private`, không dùng LUNA_STATE_DIR. Chặn nằm dưới checkout hoặc OneDrive. Không xuất cookies, không ghi profile vào RTDB/model/log. Đóng app sẽ đóng context browser để giữ session local.
- Key mới: ô password, nút lưu mã hóa Windows DPAPI theo Windows user; không plaintext fallback, không đọc key cũ hoặc gửi API. Native Windows roundtrip chưa kiểm chứng trong cloud Linux.
- Firebase project/database: nhập Settings hoặc `FIREBASE_PROJECT_ID`/`FIREBASE_DATABASE_URL`. Nút kiểm tra chỉ validate định dạng; live read vẫn khóa chờ auth/Rules. Không truy vấn root, không đổi Rules/billing.
- `.env.example` chỉ mô tả tên biến; không tự đọc .env.

File lưu tên riêng chống ghi đè, SHA-256, metadata pending_sync. Không đưa binary vào RTDB. Không tự xóa; chặn lưu khi disk free dưới payload + 100 MiB. Không đo được quota OneDrive. “Đã lưu local” không chứng minh “đã sync cloud”. Không có API có phí hoặc thay đổi billing.

## Kiểm chứng và giới hạn

Đã chạy 8 tests browser fixture qua Chromium có sẵn trên Linux: exact group/duplicates/identity mismatch, file download/hash, eOffice table ambiguity và chặn live launch trên cloud. Request fixture được intercept hoàn toàn; không đăng nhập hoặc mở site thật. GUI offscreen qua kiểm tra 7 tab, xử lý browser bất đồng bộ, đóng app, mock report và Firebase config-only validation. DPAPI native, QR/session và selector production chưa được xác minh.

Chạy kiểm tra browser fixture trên máy đã cài Chromium Playwright:

```powershell
.\.venv\Scripts\python -m unittest discover -s tests -v
```

Linux có thể chỉ định `LUNA_TEST_CHROMIUM=/usr/bin/chromium` cho tests. Tải Chromium bằng Playwright trên cloud hiện bị network policy chặn tại cdn.playwright.dev; không tắt TLS hoặc bypass proxy. Trên Windows cần cài browser bằng lệnh phía trên.

Kiểm tra hồi quy chọn nhóm: 3 UI tests xác minh My Documents là lựa chọn duy nhất khi chỉ cho phép nhóm này, đồng bộ hai tab và chặn khi không cho phép nhóm nào. Tổng suite hiện tại: 11 tests đạt trên Linux offscreen/Chromium fixture.

Nhận diện tên nhóm: đếm theo dòng hội thoại, gộp các phần tử tên lồng nhau trong cùng dòng; đối chiếu nhãn tên riêng thay vì kèm badge/thời gian. Nếu thất bại, thông báo nêu tên nhóm đang tìm, số vùng danh sách/phần tử tên hoặc số dòng trùng; không in nội dung tin nhắn/DOM đầy đủ. Đây là hỗ trợ chẩn đoán, không chứng minh adapter đã chạy trên Zalo hiện hành.

## Kết nối được nhưng chưa có nội dung
“My Documents” là hội thoại trong Zalo, không phải thư mục OneDrive. App xác minh nhóm trước, sau đó đợi tối đa 1,5 giây cho marker nội dung. Không có chữ vẫn kiểm tra file đính kèm. Trạng thái `files_only` cho phép tải file; `content_not_loaded` báo vùng chat chưa hiển thị dữ liệu; `unsupported_layout` báo có nội dung DOM nhưng adapter chưa nhận diện. Không tạo báo cáo rỗng hoặc coi preview ở danh sách là tin nhắn thật.

Nếu khung nội dung Zalo trống, kiểm tra trực tiếp khả năng hiển thị lịch sử trên Zalo. Việc đồng bộ lịch sử/điện thoại là thao tác của người dùng theo hướng dẫn Zalo, app không tự bấm. Nếu nhìn thấy tin/file nhưng app chưa đọc được, bấm **Chẩn đoán cấu trúc Zalo**, sau đó **Sao chép chẩn đoán để báo lỗi**. Dữ liệu này chỉ gồm số lượng phần tử, độ dài chữ và thống kê class CSS của vùng tin nhắn; không có text tin nhắn, HTML, cookie, URL hoặc ID hội thoại. Không cần gửi session hay toàn bộ DOM.

Đã kiểm tra bổ sung hội thoại chỉ có file, pane trống, layout chưa hỗ trợ, chẩn đoán không chứa dữ liệu riêng và chặn báo cáo rỗng; selector trên phiên Zalo thực vẫn cần xác minh khi có dữ liệu hiển thị.
