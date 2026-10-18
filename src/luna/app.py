"""Vietnamese desktop UI. No network or external execution paths."""
import json
import sys
from PySide6.QtWidgets import (QApplication, QScrollArea, QComboBox, QDateEdit, QFormLayout,
    QLabel, QLineEdit, QListWidget, QListWidgetItem, QMainWindow, QMessageBox,
    QPushButton, QTabWidget, QTextEdit, QVBoxLayout, QWidget, QTableWidget, QTableWidgetItem)
from PySide6.QtCore import Qt, QDate
from .settings import SettingsPage
from .core import (GROUPS, ChatRequest, MockModel, Outbox, edit_preview, make_report,
    sample_files, save_local, save_selected, mock_messages, EOFFICE_RECORDS)


class Window(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Luna • Bản thử nghiệm offline')
        self.resize(1000, 760)
        self.outbox = Outbox()
        self.report = None
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)
        self.statusBar().showMessage('MOCK / DRY-RUN • Không kết nối tài khoản thật • Không gọi AI có phí')
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

        self.settings = SettingsPage()
        scroll = QScrollArea(); scroll.setWidgetResizable(True); scroll.setWidget(self.settings)
        self.tabs.addTab(scroll, 'Cấu hình')
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

    def allowed_group(self):
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
        self.samples = sample_files(self.groups.currentText())
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


def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    window = Window(); window.show()
    sys.exit(app.exec())
