"""Desktop presentation only: no connector, credential or background sync logic."""
from datetime import datetime
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
    QFrame, QPushButton, QListWidget, QScrollArea, QTextEdit)

STYLE = '''
QMainWindow, QWidget#DesktopShell { background: #f3f6f9; color: #223047; }
QWidget { font-family: "Segoe UI", "DejaVu Sans"; font-size: 13px; }
QFrame#Sidebar { background: #12243a; border: none; }
QLabel#Brand { color: #ffffff; font-size: 29px; font-weight: 700; letter-spacing: 3px; }
QLabel#BrandCaption, QLabel#SidebarFoot { color: #a7b9cc; font-size: 11px; }
QListWidget#Navigation { background: transparent; color: #c7d3df; border: none; outline: none; }
QListWidget#Navigation::item { padding: 12px 10px; margin: 2px 0; border-radius: 7px; }
QListWidget#Navigation::item:selected { background: #214357; color: #6ee4cf; }
QListWidget#Navigation::item:hover { background: #1a344d; }
QLabel#Breadcrumb { color: #728195; font-size: 12px; }
QLabel#PageTitle { color: #172c43; font-size: 25px; font-weight: 700; }
QLabel#Subtitle, QLabel#Muted { color: #6b7c90; }
QLabel#Eyebrow { color: #178477; font-size: 11px; font-weight: 700; }
QLabel#CardTitle { color: #21364e; font-size: 16px; font-weight: 600; }
QLabel#KpiValue { color: #153b46; font-size: 30px; font-weight: 700; }
QLabel#Badge { color: #087e70; background: #e1f5ef; padding: 7px 11px; border-radius: 6px; font-size: 11px; }
QFrame#Card { background: #ffffff; border: 1px solid #dfe7ee; border-radius: 10px; }
QFrame#Card QLabel { background: transparent; border: none; }
QPushButton { background: #ffffff; color: #294057; border: 1px solid #d6e0e8; border-radius: 6px; padding: 9px 12px; }
QPushButton:hover { background: #edf6f4; border-color: #65bbaa; }
QPushButton:pressed { background: #d8eee9; }
QPushButton#Primary { background: #078b79; color: white; border-color: #078b79; font-weight: 600; }
QPushButton#Primary:hover { background: #087766; }
QPushButton#Primary:disabled, QPushButton:disabled { background: #edf1f5; color: #8d9aaa; border-color: #e0e6ec; }
QTabWidget::pane { border: none; background: transparent; }
QScrollArea { border: none; background: transparent; }
QScrollArea > QWidget > QWidget { background: transparent; }
QTextEdit, QLineEdit, QComboBox, QDateEdit, QTableWidget, QListWidget {
 background: white; color: #233a50; border: 1px solid #dce5ed; border-radius: 6px; padding: 6px;
 selection-background-color: #d8f1eb; selection-color: #173c43;
}
QGroupBox { border: 1px solid #dce5ed; border-radius: 8px; margin-top: 15px; padding: 14px; background: white; }
QGroupBox::title { subcontrol-origin: margin; left: 12px; padding: 0 5px; color: #284459; }
QHeaderView::section { background: #edf3f7; border: none; padding: 8px; color: #415b71; }
QStatusBar { background: #eaf0f4; color: #52697d; }
'''

PAGES = [
    ('Tổng quan', 7, 'Theo dõi nguồn dữ liệu và các tác vụ theo yêu cầu.'),
    ('Chat AI', 0, 'Trợ lý mẫu offline. Không gọi model API.'),
    ('Zalo / Tệp mẫu', 1, 'Thử luồng đọc và xuất file bằng dữ liệu mẫu.'),
    ('Browser chỉ đọc', 5, 'Đọc nguồn đã đăng nhập thủ công; không gửi hoặc submit.'),
    ('Báo cáo', 2, 'Xem báo cáo local và xuất bản TXT/JSON.'),
    ('eOffice', 3, 'Thống kê và preview mẫu; không thực thi ghi.'),
    ('Hàng đợi offline', 4, 'Các bản ghi local đang chờ đồng bộ; chưa có sync worker.'),
    ('Cấu hình kết nối', 6, 'Thiết lập nguồn, nhóm được phép và nơi lưu file.'),
    ('Nhật ký hoạt động', 8, 'Lịch sử audit local, chỉ hiển thị metadata hoạt động.'),
    ('Chẩn đoán', 9, 'Kiểm tra cấu trúc an toàn; không xuất tin nhắn hoặc session.'),
]


def label(text, name=None, wrap=True):
    widget = QLabel(text)
    if name: widget.setObjectName(name)
    widget.setWordWrap(wrap and name not in {'Badge', 'Eyebrow', 'Breadcrumb', 'PageTitle', 'Brand'})
    return widget


def card(title=None):
    frame = QFrame(); frame.setObjectName('Card')
    layout = QVBoxLayout(frame); layout.setContentsMargins(20, 18, 20, 18); layout.setSpacing(12)
    if title: layout.addWidget(label(title, 'CardTitle'))
    return frame, layout


class Dashboard(QWidget):
    def __init__(self, window):
        super().__init__(); self.window = window
        layout = QVBoxLayout(self); layout.setContentsMargins(0, 0, 0, 0); layout.setSpacing(18)
        status, body = card()
        heading = QHBoxLayout(); heading.addWidget(label('KẾT NỐI & VẬN HÀNH', 'Eyebrow')); heading.addStretch()
        heading.addWidget(label('THEO YÊU CẦU • KHÔNG TỰ ĐỒNG BỘ', 'Badge')); body.addLayout(heading)
        self.connection = label('Zalo: chưa xác minh phiên/nhóm')
        self.target = label('Nhóm đang chọn: —', 'Muted')
        body.addWidget(self.connection); body.addWidget(self.target)
        actions = QGridLayout(); actions.setHorizontalSpacing(8)
        self.open_button = self.action('Mở Zalo', lambda: window.open_browser('zalo'))
        self.connect_button = self.action('Kết nối nhóm', lambda: window.read_browser('zalo'))
        self.read_button = self.action('Bắt đầu cập nhật • 1 lần', lambda: window.read_browser('zalo'), True)
        self.pause_button = QPushButton('Tạm dừng • không có tác vụ nền'); self.pause_button.setEnabled(False)
        self.pause_button.setToolTip('Chưa có chế độ polling/tự đồng bộ. Không có tác vụ nền để tạm dừng.')
        for col, button in enumerate((self.open_button, self.connect_button, self.read_button, self.pause_button)): actions.addWidget(button, 0, col)
        body.addLayout(actions)
        body.addWidget(label('Quét QR/đăng nhập trong browser rồi xác nhận ở Cấu hình. Kết nối nhóm và cập nhật chỉ thực hiện một lượt đọc.', 'Muted'))
        layout.addWidget(status)

        kpis = QGridLayout(); kpis.setHorizontalSpacing(14)
        self.values = []
        for i, (title, note) in enumerate([
            ('Tin nhắn đã ghi nhận', 'Trong snapshot browser hiện tại'),
            ('Tệp / ảnh tham chiếu', 'Các mục của snapshot hiện tại'),
            ('Mục đã xử lý', 'File browser đã lưu local'),
            ('Báo cáo đề xuất', 'Báo cáo browser đã lưu, không gồm mẫu'),
        ]):
            frame, content = card(); content.addWidget(label(title, 'Muted'))
            value = label('0', 'KpiValue'); content.addWidget(value); content.addWidget(label(note, 'Muted'))
            kpis.addWidget(frame, 0, i); self.values.append(value)
        layout.addLayout(kpis)

        panels = QHBoxLayout(); panels.setSpacing(16)
        agent, body = card('Giám sát Agent')
        body.addWidget(label('LUNA DESKTOP AGENT', 'Eyebrow'))
        self.agent_state = label('Sẵn sàng • chưa có tác vụ browser')
        body.addWidget(self.agent_state)
        body.addWidget(label('Chế độ đọc theo yêu cầu', 'Badge'))
        self.details = label('Chưa có nội dung browser được xác minh.', 'Muted'); body.addWidget(self.details)
        body.addStretch()
        body.addWidget(self.action('Xem kết quả đọc', lambda: window.shell.navigate(5)))
        body.addWidget(label('AI / Firebase: live đang khóa. eOffice: preview-only. OneDrive sync do client trên máy thực hiện.', 'Muted'))
        panels.addWidget(agent, 1)

        sources, body = card('Nguồn cập nhật')
        self.source_rows = []
        for group in window.settings.groups:
            row = QHBoxLayout(); name = label(group.text()); state = label('—', 'Muted', False)
            row.addWidget(name, 1); row.addWidget(state); body.addLayout(row)
            self.source_rows.append((group, state))
        body.addStretch()
        body.addWidget(self.action('Quản lý nhóm & kết nối', lambda: window.shell.navigate(6)))
        body.addWidget(label('Chỉ các nhóm được cho phép mới có thể đọc. Không tự chọn gần đúng hoặc bỏ kiểm tra danh tính.', 'Muted'))
        panels.addWidget(sources, 1); layout.addLayout(panels); layout.addStretch()

    def action(self, text, callback, primary=False):
        button = QPushButton(text)
        if primary: button.setObjectName('Primary')
        button.clicked.connect(lambda: self.window.guard(callback))
        return button

    def refresh(self):
        w = self.window
        snapshot = w.live_snapshot or {}
        records = w.outbox.records()
        values = [len(snapshot.get('messages', [])), len(snapshot.get('files', [])),
                  sum(r.get('kind') == 'file' and r.get('source', {}).get('fixture') is False for r in records),
                  sum(r.get('kind') == 'report' and r.get('fixture') is False for r in records)]
        for widget, value in zip(self.values, values): widget.setText(str(value))
        group = w.groups.currentText()
        self.target.setText('Nhóm đang chọn: ' + (group or 'Chưa chọn'))
        verified = bool(snapshot and snapshot.get('group') == group)
        connection = w.settings.zstatus.text() if verified else ('Chưa xác minh nhóm đang chọn' if group else 'Chưa chọn nhóm')
        self.connection.setText('Zalo • ' + connection)
        busy = bool(w.pending_browser or w.closing_browser)
        self.agent_state.setText('Đang thực hiện tác vụ browser…' if busy else 'Sẵn sàng • không chạy cập nhật nền')
        self.details.setText(snapshot.get('warning') or 'Chưa có nội dung browser được xác minh. KPI không tính dữ liệu mẫu.')
        self.open_button.setEnabled(not busy)
        can_read = not busy and bool(group) and w.settings.zlogin.isChecked()
        self.connect_button.setEnabled(can_read); self.read_button.setEnabled(can_read)
        self.read_button.setToolTip('Đọc một lần từ browser; cần tự đăng nhập và xác nhận trong Cấu hình.')
        for checkbox, state in self.source_rows:
            state.setText('Đang chọn' if checkbox.isChecked() and checkbox.text() == group else ('Cho phép' if checkbox.isChecked() else 'Tắt'))


class DesktopShell(QWidget):
    def __init__(self, window, tabs):
        super().__init__(); self.window = window; self.tabs = tabs; self.setObjectName('DesktopShell')
        root = QHBoxLayout(self); root.setContentsMargins(0, 0, 0, 0); root.setSpacing(0)
        sidebar = QFrame(); sidebar.setObjectName('Sidebar'); sidebar.setFixedWidth(220)
        side = QVBoxLayout(sidebar); side.setContentsMargins(18, 28, 18, 20); side.setSpacing(8)
        side.addWidget(label('LUNA', 'Brand')); side.addWidget(label('AI WORKSPACE / LOCAL-FIRST', 'BrandCaption')); side.addSpacing(24)
        self.navigation = QListWidget(); self.navigation.setObjectName('Navigation'); self.navigation.addItems([p[0] for p in PAGES]); side.addWidget(self.navigation, 1)
        side.addWidget(label('WINDOWS DESKTOP\nĐọc theo yêu cầu\nDữ liệu & session ở máy bạn', 'SidebarFoot'))
        root.addWidget(sidebar)
        workspace = QVBoxLayout(); workspace.setContentsMargins(26, 24, 26, 20); workspace.setSpacing(12)
        self.breadcrumb = label('', 'Breadcrumb'); workspace.addWidget(self.breadcrumb)
        top = QHBoxLayout(); self.title = label('', 'PageTitle'); top.addWidget(self.title, 1); top.addWidget(label('LUNA • LOCAL WORKSPACE', 'Badge')); workspace.addLayout(top)
        self.description = label('', 'Subtitle'); workspace.addWidget(self.description); workspace.addSpacing(6)
        workspace.addWidget(tabs, 1); root.addLayout(workspace, 1)
        tabs.tabBar().hide()
        window.dashboard = Dashboard(window)
        scroll = QScrollArea(); scroll.setWidgetResizable(True); scroll.setWidget(window.dashboard)
        tabs.addTab(scroll, 'Tổng quan')
        audit = QWidget(); content = QVBoxLayout(audit)
        self.audit_view = QTextEdit(); self.audit_view.setReadOnly(True); content.addWidget(self.audit_view)
        button = QPushButton('Làm mới nhật ký local'); button.clicked.connect(lambda: window.guard(self.refresh_audit)); content.addWidget(button)
        tabs.addTab(audit, 'Nhật ký hoạt động')
        diagnostics = QWidget(); content = QVBoxLayout(diagnostics)
        content.addWidget(label('Chẩn đoán chỉ chứa cấu trúc/số lượng, không gửi session hoặc nội dung tin nhắn.', 'Muted'))
        self.diagnostic_view = QTextEdit(); self.diagnostic_view.setReadOnly(True); content.addWidget(self.diagnostic_view)
        for title, callback in [('Lấy chẩn đoán Zalo', window.diagnose_zalo), ('Sao chép chẩn đoán', window.copy_diagnostics)]:
            button = QPushButton(title); button.clicked.connect(lambda checked=False, fn=callback: window.guard(fn)); content.addWidget(button)
        tabs.addTab(diagnostics, 'Chẩn đoán')
        self.navigation.currentRowChanged.connect(self.select)
        tabs.currentChanged.connect(self.sync_navigation)
        window.settings.zlogin.toggled.connect(lambda: window.refresh_dashboard())
        self.navigate(7)

    def navigate(self, page):
        self.tabs.setCurrentIndex(page)
        self.sync_navigation(page)

    def select(self, row):
        if row >= 0: self.tabs.setCurrentIndex(PAGES[row][1])

    def sync_navigation(self, page):
        for row, (title, index, description) in enumerate(PAGES):
            if index == page:
                self.navigation.blockSignals(True); self.navigation.setCurrentRow(row); self.navigation.blockSignals(False)
                self.breadcrumb.setText('Luna  /  ' + title); self.title.setText(title); self.description.setText(description)
                break
        if page == 7: self.window.refresh_dashboard()
        if page == 8: self.refresh_audit()
        if page == 9:
            import json
            self.diagnostic_view.setPlainText(json.dumps(self.window.last_diagnostics, ensure_ascii=False, indent=2) if self.window.last_diagnostics else 'Chưa có chẩn đoán. Bấm lấy chẩn đoán sau khi mở browser.')

    def refresh_audit(self):
        rows = self.window.outbox.records('audit')
        lines = []
        for row in rows:
            if row.get('kind') != 'audit': continue
            moment = datetime.fromtimestamp(row['created_at']).strftime('%d/%m/%Y %H:%M')
            lines.append(f"{moment}  •  {row.get('action', '—')}  •  {row['id'][:8]}")
        self.audit_view.setPlainText('\n'.join(lines) or 'Chưa có sự kiện audit local.')
