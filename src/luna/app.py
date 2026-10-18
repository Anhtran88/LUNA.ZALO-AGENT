"""Minimal desktop UI: all connectors and AI are mock/offline."""
import json
import sys
from PySide6.QtWidgets import (QApplication, QScrollArea, QComboBox, QFormLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem, QMainWindow, QMessageBox, QPushButton, QTabWidget, QTextEdit, QVBoxLayout, QWidget)
from PySide6.QtCore import Qt
from .settings import SettingsPage
from .core import GROUPS, EOFFICE_URL, ChatRequest, MockModel, Outbox, edit_preview, make_report, sample_files, save_local, save_selected


class Window(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Luna — MOCK / OFFLINE — không thao tác tài khoản thật')
        self.resize(850, 650)
        self.outbox = Outbox()
        self.report = None
        tabs = QTabWidget()
        self.setCentralWidget(tabs)
        self.settings = SettingsPage()
        scroll = QScrollArea(); scroll.setWidgetResizable(True); scroll.setWidget(self.settings)
        tabs.addTab(scroll, 'Cấu hình')
        chat, layout = self.page(tabs, 'Chat')
        layout.addWidget(QLabel('AI mock: không API, không phát sinh phí.'))
        self.chat_log = QTextEdit(); self.chat_log.setReadOnly(True)
        self.prompt = QLineEdit(); self.prompt.setPlaceholderText('Nhập yêu cầu…')
        layout.addWidget(self.chat_log); layout.addWidget(self.prompt)
        self.button(layout, 'Gửi tới mock', self.chat)
        _, layout = self.page(tabs, 'Zalo / file')
        layout.addWidget(QLabel('QR/login chưa kết nối. Danh sách và file bên dưới đều là dữ liệu mẫu.'))
        self.groups = QComboBox(); self.groups.addItems(GROUPS)
        layout.addWidget(self.groups)
        self.files = QListWidget(); layout.addWidget(self.files)
        self.groups.currentTextChanged.connect(self.populate)
        self.populate()
        self.button(layout, 'Lưu các file mẫu đã chọn vào thư mục OneDrive', self.save_files)
        self.button(layout, 'Tạo báo cáo mock', self.report_create)
        _, layout = self.page(tabs, 'Báo cáo')
        self.report_view = QTextEdit(); self.report_view.setReadOnly(True)
        layout.addWidget(self.report_view)
        self.button(layout, 'Xuất báo cáo hiện tại ra file local', self.report_save)
        _, layout = self.page(tabs, 'eOffice')
        url = QLabel(EOFFICE_URL); url.setWordWrap(True); layout.addWidget(url)
        layout.addWidget(QLabel('MOCK: 2 hồ sơ mẫu, 1 chờ xử lý. Chưa truy cập website.'))
        form = QFormLayout(); layout.addLayout(form)
        self.record = QLineEdit('MOCK-001'); self.record.setReadOnly(True)
        self.field = QLineEdit('Nội dung'); self.field.setReadOnly(True)
        self.current = QLineEdit('Giá trị mẫu hiện tại'); self.current.setReadOnly(True)
        self.proposed = QLineEdit()
        for label, widget in [('Record mẫu', self.record), ('Field mẫu', self.field), ('Hiện tại', self.current), ('Đề xuất', self.proposed)]: form.addRow(label, widget)
        self.button(layout, 'Preview — không submit', self.preview)
        self.preview_view = QTextEdit(); self.preview_view.setReadOnly(True); layout.addWidget(self.preview_view)
        layout.addWidget(QLabel('Không có chức năng thực thi ghi. Preview không phải xác nhận production.'))

    def page(self, tabs, title):
        widget = QWidget(); layout = QVBoxLayout(widget); tabs.addTab(widget, title)
        return widget, layout

    def button(self, layout, title, callback):
        button = QPushButton(title); button.clicked.connect(lambda: self.guard(callback)); layout.addWidget(button)

    def guard(self, callback):
        try: callback()
        except Exception as exc: QMessageBox.warning(self, 'Thao tác chưa hoàn tất', str(exc))

    def chat(self):
        text = self.prompt.text().strip()
        if not text: return
        result = MockModel().complete(ChatRequest([{'role': 'user', 'content': text}]))
        self.chat_log.append('Bạn: ' + text)
        self.chat_log.append(result['choices'][0]['message']['content'])
        self.prompt.clear()

    def populate(self, *_):
        self.files.clear()
        self.samples = sample_files(self.groups.currentText())
        for sample in self.samples:
            item = QListWidgetItem(sample.name); item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Unchecked); self.files.addItem(item)

    def allowed_group(self):
        allowed = [g.text() for g in self.settings.groups if g.isChecked()]
        if self.groups.currentText() not in allowed:
            raise ValueError('Nhóm chưa được cho phép trong Cấu hình.')

    def save_files(self):
        self.allowed_group()
        selected = [self.samples[i] for i in range(self.files.count()) if self.files.item(i).checkState() == Qt.CheckState.Checked]
        if not selected: raise ValueError('Hãy chọn file mẫu.')
        if QMessageBox.question(self, 'Xác nhận lưu local', 'Lưu các file mẫu đã chọn? OneDrive client có thể tự đồng bộ thư mục này.') != QMessageBox.StandardButton.Yes: return
        results = []
        for sample in selected:
            metadata = save_selected(sample, self.groups.currentText(), list(GROUPS), self.outbox)
            results.append(metadata['stored_name'])
            self.files.item(self.samples.index(sample)).setCheckState(Qt.CheckState.Unchecked)
        QMessageBox.information(self, 'Đã lưu local; chưa xác minh OneDrive sync', '\n'.join(results))

    def report_create(self):
        self.allowed_group()
        self.report = make_report(self.groups.currentText(), self.outbox)
        self.report_view.setPlainText(self.report['text'] + '\n\nTrạng thái: pending_sync (chưa có Firebase sync).')
        QMessageBox.information(self, 'Báo cáo mock', 'Đã lưu nháp local. Xem tab Báo cáo.')

    def report_save(self):
        if not self.report: raise ValueError('Chưa có báo cáo.')
        if QMessageBox.question(self, 'Xuất báo cáo', 'Lưu báo cáo mẫu vào thư mục OneDrive?') != QMessageBox.StandardButton.Yes: return
        save_local('MOCK-report.txt', self.report['text'].encode('utf-8'), {'report_id': self.report['id']}, self.outbox)
        QMessageBox.information(self, 'Đã xuất local', 'OneDrive sync chưa được xác minh.')

    def preview(self):
        if not self.proposed.text().strip(): raise ValueError('Nhập giá trị đề xuất.')
        data = edit_preview(self.record.text(), self.field.text(), self.current.text(), self.proposed.text())
        self.outbox.add('approval', dict(data, status='preview_only_not_approved'))
        self.outbox.add('audit', {'action': 'mock_edit_preview', 'record': data['record']})
        self.preview_view.setPlainText(json.dumps(data, ensure_ascii=False, indent=2))


def main():
    app = QApplication(sys.argv)
    window = Window(); window.show()
    sys.exit(app.exec())
