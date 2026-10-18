"""Vietnamese desktop UI. No network or external execution paths."""
import json
import sys
from PySide6.QtWidgets import (QApplication, QScrollArea, QComboBox, QDateEdit, QFormLayout,
    QLabel, QLineEdit, QListWidget, QListWidgetItem, QMainWindow, QMessageBox,
    QPushButton, QTabWidget, QTextEdit, QVBoxLayout, QWidget, QTableWidget, QTableWidgetItem)
from PySide6.QtCore import Qt, QDate, QTimer
from .settings import SettingsPage
from .browser import BrowserWorker, BrowserError
from .core import (GROUPS, ChatRequest, MockModel, Outbox, edit_preview, make_report,
    sample_files, save_local, save_selected, mock_messages, EOFFICE_RECORDS)


class Window(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Luna • Bản thử nghiệm offline')
        self.resize(1000, 760)
        self.outbox = Outbox()
        self.report = None
        self.browser = BrowserWorker()
        self.pending_browser = None
        self.closing_browser = False
        self.browser_closed = False
        self.live_snapshot = None
        self.last_diagnostics = None
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)
        self.statusBar().showMessage('Mock + Browser chỉ đọc theo yêu cầu • Firebase/AI live khóa • Không submit/gửi tin')
        layout = self.page('Chat')
        layout.addWidget(QLabel('Trợ lý mẫu — yêu cầu tổng hợp sẽ tạo báo cáo từ nhóm/thời gian đang chọn ở tab Zalo.'))
        self.chat_log = QTextEdit(); self.chat_log.setReadOnly(True)
        self.prompt = QLineEdit(); self.prompt.setPlaceholderText('Ví dụ: Tổng hợp tin nhắn nhóm đã chọn')
        self.prompt.returnPressed.connect(lambda: self.guard(self.chat))
        layout.addWidget(self.chat_log); layout.addWidget(self.prompt)
        self.button(layout, 'Gửi yêu cầu mẫu', self.chat)

        layout = self.page('Zalo / Tệp')
        layout.addWidget(QLabel('DỮ LIỆU MẪU • Không có phiên Zalo thật. File mẫu độc lập với bộ lọc tin nhắn.'))
        self.groups = QComboBox(); self.groups.addItems(GROUPS)
        layout.addWidget(self.groups)
        form = QFormLayout(); layout.addLayout(form)
        self.start = QDateEdit(QDate.currentDate().addDays(-1)); self.end = QDateEdit(QDate.currentDate())
        for widget in (self.start, self.end): widget.setCalendarPopup(True); widget.setDisplayFormat('dd/MM/yyyy')
        form.addRow('Từ ngày', self.start); form.addRow('Đến ngày', self.end)
        self.button(layout, 'Đọc tin nhắn mẫu trong khoảng thời gian', self.read_messages)
        self.messages = QTextEdit(); self.messages.setReadOnly(True); layout.addWidget(self.messages)
        self.files = QListWidget(); layout.addWidget(self.files)
        self.groups.currentTextChanged.connect(self.populate)
        self.button(layout, 'Lưu ảnh/PDF mẫu đã chọn', self.save_files)
        self.button(layout, 'Tạo báo cáo từ nhóm và thời gian đã chọn', self.report_create)

        layout = self.page('Báo cáo')
        self.history = QComboBox(); self.history.currentIndexChanged.connect(self.select_report)
        layout.addWidget(self.history)
        self.report_view = QTextEdit(); self.report_view.setReadOnly(True); layout.addWidget(self.report_view)
        self.button(layout, 'Xuất báo cáo TXT và JSON', self.report_save)

        layout = self.page('eOffice')
        self.site_label = QLabel(); self.site_label.setWordWrap(True); layout.addWidget(self.site_label)
        self.stats = QLabel(''); layout.addWidget(self.stats)
        self.table = QTableWidget(0, 4); self.table.setHorizontalHeaderLabels(['Mã mẫu', 'Nội dung', 'Trạng thái', 'Khối lượng mẫu'])
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.table)
        self.button(layout, 'Thống kê dữ liệu mẫu', self.refresh_stats)
        form = QFormLayout(); layout.addLayout(form)
        self.record = QComboBox(); self.record.addItems([r['id'] for r in EOFFICE_RECORDS])
        self.field = QComboBox(); self.field.addItems(['title', 'status'])
        self.current = QLineEdit(); self.current.setReadOnly(True)
        self.proposed = QLineEdit()
        for label, widget in [('Hồ sơ mẫu', self.record), ('Trường', self.field), ('Hiện tại', self.current), ('Đề xuất', self.proposed)]: form.addRow(label, widget)
        self.record.currentIndexChanged.connect(self.update_current); self.field.currentIndexChanged.connect(self.update_current)
        self.proposed.textChanged.connect(self.invalidate_preview)
        self.button(layout, 'So sánh / lưu preview — không thực thi', self.preview)
        self.preview_view = QTextEdit(); self.preview_view.setReadOnly(True); layout.addWidget(self.preview_view)
        disabled = QPushButton('Ghi thật / gửi / trình / xóa / upload — chưa hỗ trợ'); disabled.setEnabled(False); layout.addWidget(disabled)

        layout = self.page('Hàng đợi offline')
        self.queue_summary = QLabel(); layout.addWidget(self.queue_summary)
        self.queue = QTableWidget(0, 3); self.queue.setHorizontalHeaderLabels(['Loại', 'Mã', 'Trạng thái'])
        self.queue.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers); layout.addWidget(self.queue)
        self.button(layout, 'Làm mới lịch sử local', self.refresh_queue)
        layout.addWidget(QLabel('Chưa có worker đồng bộ Firebase. Không tự thực thi hành động ngoài hệ thống khi có mạng.'))

        layout = self.page('Browser chỉ đọc')
        layout.addWidget(QLabel('Nguồn: hội thoại Zalo đang mở, không phải thư mục Windows. Đích lưu file: thư mục local/OneDrive trong Cấu hình.'))
        self.live_status = QLabel('Chưa đăng nhập / chưa mở browser'); self.live_status.setWordWrap(True); layout.addWidget(self.live_status)
        self.live_text = QTextEdit(); self.live_text.setReadOnly(True); layout.addWidget(self.live_text)
        self.live_files = QListWidget(); layout.addWidget(self.live_files)
        self.button(layout, 'Đọc lại nhóm Zalo đã chọn', lambda: self.read_browser('zalo'))
        self.button(layout, 'Chẩn đoán cấu trúc Zalo (không lấy nội dung riêng)', self.diagnose_zalo)
        self.button(layout, 'Sao chép chẩn đoán để báo lỗi', self.copy_diagnostics)
        self.button(layout, 'Tải ảnh/PDF browser đã chọn (xác nhận trước khi lưu)', self.download_live)
        self.button(layout, 'Lưu báo cáo từ nội dung browser đã đọc', self.report_live)
        self.settings = SettingsPage()
        self.settings.browser_open.connect(lambda site: self.guard(lambda: self.open_browser(site)))
        self.settings.browser_read.connect(lambda site: self.guard(lambda: self.read_browser(site)))
        self.browser_timer = QTimer(self); self.browser_timer.timeout.connect(self.poll_browser); self.browser_timer.start(100)
        scroll = QScrollArea(); scroll.setWidgetResizable(True); scroll.setWidget(self.settings)
        self.tabs.addTab(scroll, 'Cấu hình')
        self.settings.target_group.currentTextChanged.connect(self.sync_group_choices)
        self.groups.currentTextChanged.connect(self.settings.target_group.setCurrentText)
        self.sync_group_choices()
        self.populate(); self.update_current(); self.refresh_stats(); self.refresh_history(); self.refresh_queue()

    def page(self, title):
        widget = QWidget(); layout = QVBoxLayout(widget); self.tabs.addTab(widget, title)
        return layout

    def button(self, layout, title, callback):
        button = QPushButton(title); button.clicked.connect(lambda: self.guard(callback)); layout.addWidget(button)
        return button

    def guard(self, callback):
        try:
            callback()
        except Exception as exc:
            QMessageBox.warning(self, 'Thao tác chưa hoàn tất', str(exc))

    def period(self):
        return self.start.date().toString('yyyy-MM-dd'), self.end.date().toString('yyyy-MM-dd')

    def sync_group_choices(self, *_):
        selected = self.settings.target_group.currentText()
        allowed = [g.text() for g in self.settings.groups if g.isChecked()]
        self.groups.blockSignals(True)
        self.groups.clear(); self.groups.addItems(allowed)
        self.groups.setCurrentIndex(allowed.index(selected) if selected in allowed else -1)
        self.groups.blockSignals(False)
        self.groups.setPlaceholderText('Chọn nhóm trong Cấu hình' if allowed else 'Chưa cho phép nhóm nào')
        self.populate()

    def allowed_group(self):
        if not self.groups.currentText():
            raise ValueError('Chưa chọn nhóm để đọc. Hãy chọn nhóm cụ thể trong Cấu hình hoặc tab Zalo/Tệp.')
        if self.groups.currentText() not in [g.text() for g in self.settings.groups if g.isChecked()]:
            raise ValueError('Nhóm chưa được cho phép trong Cấu hình.')

    def chat(self):
        text = self.prompt.text().strip()
        if not text: return
        self.chat_log.append('Bạn: ' + text)
        if 'tổng hợp' in text.lower() or 'báo cáo' in text.lower():
            self.allowed_group()
            report = make_report(self.groups.currentText(), self.outbox, *self.period())
            self.refresh_history(report['id']); self.refresh_queue()
            reply = report['text']
        else:
            reply = MockModel().complete(ChatRequest([{'role': 'user', 'content': text}]))['choices'][0]['message']['content']
        self.chat_log.append(reply); self.prompt.clear()

    def populate(self, *_):
        self.files.clear(); self.messages.clear()
        self.live_snapshot = None
        if hasattr(self, 'live_files'): self.live_files.clear()
        self.samples = sample_files(self.groups.currentText()) if self.groups.currentText() else []
        for sample in self.samples:
            item = QListWidgetItem(sample.name); item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Unchecked); self.files.addItem(item)

    def read_messages(self):
        self.allowed_group()
        messages = mock_messages(self.groups.currentText(), *self.period())
        self.messages.setPlainText('\n\n'.join(f'{m.timestamp} • {m.sender} [{m.id}]\n{m.text}' for m in messages) or 'Không có tin nhắn mẫu trong khoảng đã chọn.')

    def save_files(self):
        self.allowed_group()
        selected = [i for i in range(self.files.count()) if self.files.item(i).checkState() == Qt.CheckState.Checked]
        if not selected: raise ValueError('Hãy chọn file mẫu.')
        if QMessageBox.question(self, 'Lưu local', 'Lưu file mẫu đã chọn? OneDrive client có thể tự đồng bộ thư mục đích.') != QMessageBox.StandardButton.Yes: return
        for i in selected:
            record = save_selected(self.samples[i], self.groups.currentText(), list(GROUPS), self.outbox)
            self.files.item(i).setCheckState(Qt.CheckState.Unchecked)
            self.statusBar().showMessage('Đã lưu local: ' + record['stored_name'] + ' • Chưa xác nhận OneDrive sync')
        self.refresh_queue()

    def report_create(self):
        self.allowed_group()
        report = make_report(self.groups.currentText(), self.outbox, *self.period())
        self.refresh_history(report['id']); self.refresh_queue(); self.tabs.setCurrentIndex(2)

    def refresh_history(self, selected=None):
        self.history.blockSignals(True); self.history.clear()
        for report in self.outbox.records('report'):
            if report.get('kind') == 'report':
                self.history.addItem(f"{report.get('group', '')} • {report.get('start', '')} • {report['id'][:8]}", report)
        self.history.blockSignals(False)
        if selected:
            for i in range(self.history.count()):
                if self.history.itemData(i)['id'] == selected: self.history.setCurrentIndex(i); break
        self.select_report()

    def select_report(self, *_):
        self.report = self.history.currentData()
        self.report_view.setPlainText(self.report['text'] + '\n\nChưa đồng bộ RTDB.' if self.report else 'Chưa có báo cáo local.')

    def report_save(self):
        if not self.report: raise ValueError('Chưa có báo cáo.')
        if QMessageBox.question(self, 'Xuất báo cáo', 'Lưu bản TXT và JSON vào thư mục đã chọn?') != QMessageBox.StandardButton.Yes: return
        for name, content in [('report.txt', self.report['text'].encode()), ('report.json', json.dumps(self.report, ensure_ascii=False, indent=2).encode())]:
            save_local(name, content, {'report_id': self.report['id']}, self.outbox)
        self.refresh_queue(); self.statusBar().showMessage('Đã xuất TXT/JSON local • Chưa xác nhận OneDrive sync')

    def refresh_stats(self):
        self.site_label.setText('URL cấu hình (không truy cập): ' + self.settings.url.text())
        self.stats.setText(f'DỮ LIỆU MẪU • {len(EOFFICE_RECORDS)} hồ sơ • Tổng khối lượng: {sum(r["quantity"] for r in EOFFICE_RECORDS)} • Chờ xử lý: 1')
        self.table.setRowCount(len(EOFFICE_RECORDS))
        for i, record in enumerate(EOFFICE_RECORDS):
            for j, key in enumerate(['id', 'title', 'status', 'quantity']): self.table.setItem(i, j, QTableWidgetItem(str(record[key])))
        self.table.resizeColumnsToContents()

    def update_current(self, *_):
        self.current.setText(EOFFICE_RECORDS[self.record.currentIndex()][self.field.currentText()])
        self.invalidate_preview()

    def invalidate_preview(self, *_):
        self.preview_view.setPlainText('Chưa có preview hợp lệ cho lựa chọn/đề xuất hiện tại.')

    def preview(self):
        proposed = self.proposed.text().strip()
        if not proposed or proposed == self.current.text(): raise ValueError('Giá trị đề xuất phải có nội dung và khác hiện tại.')
        data = edit_preview(self.record.currentText(), self.field.currentText(), self.current.text(), proposed)
        data['action_hash'] = __import__('hashlib').sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()
        self.outbox.add('approval', dict(data, status='preview_only_not_approved'))
        self.outbox.add('audit', {'action': 'mock_edit_preview', 'record': data['record'], 'action_hash': data['action_hash']})
        self.preview_view.setPlainText(f"Hồ sơ: {data['record']}\nTrường: {data['field']}\nHiện tại: {data['current']}\nĐề xuất: {data['proposed']}\n\nDRY-RUN — chưa phê duyệt, không thực thi.")
        self.refresh_queue()

    def refresh_queue(self):
        records = self.outbox.records()
        self.queue_summary.setText(f'{len(records)} bản ghi local • Firebase sync chưa triển khai • OneDrive sync chưa xác minh')
        self.queue.setRowCount(len(records))
        for i, row in enumerate(records):
            for j, key in enumerate(['kind', 'id', 'sync_state']): self.queue.setItem(i, j, QTableWidgetItem(str(row.get(key, ''))))
        self.queue.resizeColumnsToContents()


    def run_browser(self, operation, callback, *args):
        if self.pending_browser or self.closing_browser:
            raise BrowserError('Browser đang xử lý; chờ hoàn tất trước khi thực hiện tiếp.')
        site = args[0] if operation == 'open' else ('eoffice' if operation == 'read_eoffice' else 'zalo')
        self.pending_browser = (self.browser.submit(operation, *args), callback, site)
        self.settings.setEnabled(False)
        self.live_status.setText('Đang xử lý browser… Không tự xử lý CAPTCHA/OTP.')
        self.tabs.setCurrentIndex(5)

    def poll_browser(self):
        if not self.pending_browser: return
        future, callback, site = self.pending_browser
        if not future.done(): return
        self.pending_browser = None
        self.settings.setEnabled(True)
        try:
            result = future.result()
            if not self.closing_browser: callback(result)
        except Exception as exc:
            message = str(exc) if isinstance(exc, BrowserError) else 'Browser lỗi hoặc thiếu Chromium. Cài browser theo README; kiểm tra cửa sổ, phiên và UI. Không log URL/session.'
            self.live_status.setText(message)
            if site == 'zalo': self.settings.zstatus.setText('Chưa xác minh nhóm/nội dung — xem thông báo Browser chỉ đọc')
            else: self.settings.estatus.setText('Chưa xác minh trang/phiên — xem thông báo Browser chỉ đọc')

    def open_browser(self, site):
        self.live_snapshot = None; self.live_files.clear(); self.live_text.clear()
        self.run_browser('open', lambda message: self.live_status.setText(message), site, self.settings.url.text().strip())

    def read_browser(self, site):
        if site == 'zalo':
            self.allowed_group()
            if not self.settings.zlogin.isChecked(): raise BrowserError('Hãy tự quét QR/đăng nhập rồi đánh dấu đã đăng nhập.')
            self.live_snapshot = None; self.live_files.clear(); self.live_text.clear()
            self.run_browser('read_zalo', self.show_zalo, self.groups.currentText())
        else:
            if not self.settings.elogin.isChecked(): raise BrowserError('Hãy tự đăng nhập eOffice rồi xác nhận đã đăng nhập.')
            self.live_snapshot = None; self.live_files.clear(); self.live_text.clear()
            self.run_browser('read_eoffice', self.show_eoffice)

    def show_zalo(self, snapshot):
        self.live_snapshot = snapshot
        self.last_diagnostics = snapshot.get('diagnostics')
        self.live_text.setPlainText('ZALO READ-ONLY • ' + snapshot['group'] + '\n\n' + ('\n\n'.join(snapshot['messages']) or snapshot['warning']))
        self.live_status.setText(snapshot['warning'])
        self.settings.zstatus.setText('Đã xác minh nhóm • ' + snapshot.get('content_state', 'ready'))
        for file in snapshot['files']:
            item = QListWidgetItem(file.get('label', file['name'])); item.setData(Qt.ItemDataRole.UserRole, file['id'])
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable); item.setCheckState(Qt.CheckState.Unchecked)
            self.live_files.addItem(item)

    def show_eoffice(self, snapshot):
        self.live_text.setPlainText('EOFFICE READ-ONLY • ' + str(snapshot['count']) + ' dòng đang tải\n\n' + '\n'.join(' | '.join(row) for row in snapshot['rows']))
        self.live_status.setText(snapshot['warning'])
        self.settings.estatus.setText('Đã đọc một bảng DOM — chưa xác minh toàn bộ dữ liệu')

    def download_live(self):
        from .core import output_dir
        self.allowed_group()
        snapshot = self.live_snapshot
        if not snapshot or snapshot['group'] != self.groups.currentText(): raise BrowserError('Hãy đọc lại đúng nhóm trước khi tải.')
        tokens = [self.live_files.item(i).data(Qt.ItemDataRole.UserRole) for i in range(self.live_files.count()) if self.live_files.item(i).checkState() == Qt.CheckState.Checked]
        if not tokens: raise BrowserError('Chọn ít nhất một file ảnh/PDF từ browser.')
        folder = str(output_dir())
        if QMessageBox.question(self, 'Xác nhận tải/xuất ảnh', f'Lưu {len(tokens)} mục vào {folder}? Ảnh hiển thị xuất PNG, có thể là thumbnail/bản chụp, không cam kết ảnh gốc. OneDrive client có thể tự đồng bộ.') != QMessageBox.StandardButton.Yes: return
        def complete(records):
            self.live_status.setText(f'Đã lưu {len(records)} file local; metadata pending_sync. OneDrive sync chưa xác minh.')
            self.live_snapshot = None; self.live_files.clear(); self.refresh_queue()
        self.run_browser('download', complete, snapshot['group'], tokens, self.outbox, folder)

    def report_live(self):
        self.allowed_group()
        snapshot = self.live_snapshot
        if not snapshot or snapshot['group'] != self.groups.currentText(): raise BrowserError('Chưa có nội dung đúng nhóm được phép.')
        if not snapshot['messages'] and not snapshot['files']:
            raise BrowserError('Chưa có nội dung để báo cáo. Hãy đọc lại sau khi Zalo hiển thị tin/file hoặc lấy chẩn đoán cấu trúc.')
        record = self.outbox.add('report', {'files': [file['name'] for file in snapshot['files']], 'group': snapshot['group'], 'text': '[ZALO READ-ONLY — TRÍCH NỘI DUNG, CHƯA TÓM TẮT AI]\n' + snapshot['warning'] + '\n\n' + '\n\n'.join(snapshot['messages']) + '\n\nFile nhận diện: ' + ', '.join(file['name'] for file in snapshot['files']), 'fixture': False, 'source': 'loaded_browser_dom', 'observed_at': snapshot['observed_at']})
        self.outbox.add('audit', {'action': 'browser_report_local', 'report_id': record['id']})
        self.refresh_history(record['id']); self.refresh_queue(); self.tabs.setCurrentIndex(2)

    def diagnose_zalo(self):
        self.run_browser('diagnose_zalo', self.show_diagnostics)

    def show_diagnostics(self, diagnostics):
        self.last_diagnostics = diagnostics
        self.live_status.setText('Chẩn đoán cấu trúc sẵn sàng; có thể sao chép để kiểm tra selector, không chứa nội dung tin nhắn.')
        self.live_text.setPlainText(json.dumps(diagnostics, ensure_ascii=False, indent=2))

    def copy_diagnostics(self):
        if not self.last_diagnostics:
            raise BrowserError('Bấm Chẩn đoán cấu trúc trước.')
        QApplication.clipboard().setText(json.dumps(self.last_diagnostics, ensure_ascii=False, indent=2))
        self.statusBar().showMessage('Đã sao chép chẩn đoán cấu trúc; không sao chép tin nhắn hoặc session.')

    def closeEvent(self, event):
        if self.browser_closed:
            event.accept(); return
        event.ignore()
        if not self.closing_browser:
            self.closing_browser = True
            self.close_future = self.browser.shutdown()
            self.statusBar().showMessage('Đang đóng browser và lưu session local…')
        QTimer.singleShot(100, self.finish_close)

    def finish_close(self):
        if self.close_future.done():
            self.browser_closed = True; self.close()
        else:
            QTimer.singleShot(100, self.finish_close)


def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    window = Window(); window.show()
    sys.exit(app.exec())
