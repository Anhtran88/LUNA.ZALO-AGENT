"""Local settings UI. No live connection checks or credential reads."""
import ctypes
from ctypes import wintypes
import json
import os
from pathlib import Path
from urllib.parse import urlparse
from PySide6.QtWidgets import QWidget, QVBoxLayout, QGroupBox, QFormLayout, QLabel, QLineEdit, QPushButton, QCheckBox, QFileDialog, QMessageBox
from .core import GROUPS, EOFFICE_URL, state_dir


class Blob(ctypes.Structure):
    _fields_ = [('size', wintypes.DWORD), ('data', ctypes.POINTER(ctypes.c_ubyte))]


def protect_key(value: str):
    """Encrypt for current Windows user. Never fall back to plaintext."""
    if os.name != 'nt':
        raise ValueError('Lưu key chỉ hỗ trợ Windows DPAPI; không lưu plaintext trên Linux.')
    buffer = ctypes.create_string_buffer(value.encode('utf-8'))
    source = Blob(len(value.encode('utf-8')), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_ubyte)))
    target = Blob()
    crypt = ctypes.WinDLL('crypt32', use_last_error=True)
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    crypt.CryptProtectData.argtypes = [ctypes.POINTER(Blob), wintypes.LPCWSTR, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(Blob)]
    crypt.CryptProtectData.restype = wintypes.BOOL
    kernel.LocalFree.argtypes = [ctypes.c_void_p]
    kernel.LocalFree.restype = ctypes.c_void_p
    if not crypt.CryptProtectData(ctypes.byref(source), 'Luna model key', None, None, None, 1, ctypes.byref(target)):
        raise OSError('DPAPI không lưu được key.')
    try:
        encrypted = ctypes.string_at(target.data, target.size)
    finally:
        kernel.LocalFree(ctypes.cast(target.data, ctypes.c_void_p))
    folder = state_dir(); folder.mkdir(parents=True, exist_ok=True)
    temporary = folder / 'model-key.dpapi.tmp'
    temporary.write_bytes(encrypted)
    temporary.replace(folder / 'model-key.dpapi')


class SettingsPage(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel('OFFLINE: cấu hình không bật live. “Kiểm tra” hiện chỉ kiểm tra local/mock, không chứng minh kết nối.'))
        form, self.zstatus = self.card(layout, 'Zalo')
        self.groups = []
        for group in GROUPS:
            check = QCheckBox(group); check.setChecked(True); self.groups.append(check); form.addRow(check)
        button = QPushButton('Mở Zalo Web / Quét QR — chưa triển khai')
        button.setEnabled(False); form.addRow(button)
        self.zlogin = QCheckBox('Tôi đã đăng nhập trong browser profile riêng (dành cho connector tương lai)'); form.addRow(self.zlogin)
        test = QPushButton('Kiểm tra cấu hình mock'); test.setEnabled(False); self.zlogin.toggled.connect(test.setEnabled)
        test.clicked.connect(lambda: self.zstatus.setText('Chưa cấu hình — mock, không kiểm tra phiên thật')); form.addRow(test)
        form, self.estatus = self.card(layout, 'eOffice')
        self.url = QLineEdit(EOFFICE_URL); form.addRow('URL', self.url)
        self.elogin = QCheckBox('Tôi đã đăng nhập (không xác minh session trong scaffold)'); form.addRow(self.elogin)
        test = QPushButton('Kiểm tra URL read-only/mock'); test.setEnabled(False); self.elogin.toggled.connect(test.setEnabled)
        test.clicked.connect(self.check_site); form.addRow(test)
        form, self.mstatus = self.card(layout, 'AI Model')
        form.addRow(QLabel('Provider: OpenAI/ChatGPT API-compatible. 9Router: để sau.'))
        self.model = QLineEdit(); self.model.setPlaceholderText('Model ID — chưa bật API')
        self.key = QLineEdit(); self.key.setEchoMode(QLineEdit.EchoMode.Password); self.key.setPlaceholderText('Key mới, không đọc credential hiện có')
        form.addRow('Model', self.model); form.addRow('Key', self.key)
        save = QPushButton('Lưu key bằng Windows DPAPI'); save.clicked.connect(self.save_key); form.addRow(save)
        form.addRow(QLabel('API có thể tính phí; chưa có ngân sách. Live test khóa, không gửi request.'))
        self.mtest = QPushButton('Test cấu hình mock — không gọi API'); self.mtest.setEnabled(False)
        self.key.textChanged.connect(self.model_gate); self.model.textChanged.connect(self.model_gate)
        self.mtest.clicked.connect(lambda: self.mstatus.setText('Chưa cấu hình live — dữ liệu nhập đủ cho mock, chưa xác minh key'))
        form.addRow(self.mtest)
        form, self.fstatus = self.card(layout, 'Firebase RTDB')
        form.addRow('Project', QLabel(os.environ.get('FIREBASE_PROJECT_ID', 'Chưa cấu hình')))
        form.addRow('Database', QLabel(os.environ.get('FIREBASE_DATABASE_URL', 'Chưa cấu hình')))
        form.addRow(QLabel('Credential: không đọc/hiển thị. Rules/auth chưa xác minh.'))
        test = QPushButton('Test read-only live — chưa triển khai'); test.setEnabled(False); form.addRow(test)
        form, self.ostatus = self.card(layout, 'File / OneDrive')
        self.folder = QLineEdit(os.environ.get('LUNA_OUTPUT_DIR', ''))
        form.addRow('Thư mục', self.folder)
        choose = QPushButton('Chọn thư mục'); choose.clicked.connect(self.choose_folder); form.addRow(choose)
        test = QPushButton('Kiểm tra thư mục local'); test.clicked.connect(self.check_folder); form.addRow(test)
        form.addRow(QLabel('OneDrive client chịu trách nhiệm sync. App chưa xác nhận được đã sync cloud.'))
        save = QPushButton('Lưu cấu hình không chứa secret'); save.clicked.connect(self.save_config); layout.addWidget(save)
        self.load_config()

    def card(self, layout, title):
        box = QGroupBox(title); form = QFormLayout(box); layout.addWidget(box)
        status = QLabel('Chưa cấu hình'); form.addRow('Trạng thái', status)
        return form, status

    def model_gate(self, *_):
        self.mtest.setEnabled(bool(self.model.text().strip() and self.key.text().strip()))

    def save_key(self):
        try:
            if not self.key.text().strip(): raise ValueError('Chưa nhập key.')
            protect_key(self.key.text())
            self.key.clear()
            self.mstatus.setText('Chưa cấu hình live — key đã lưu DPAPI, chưa xác minh')
        except Exception:
            self.mstatus.setText('Lỗi — không lưu được key; cần Windows DPAPI. Không có plaintext fallback.')

    def check_site(self):
        parsed = urlparse(self.url.text())
        valid = parsed.scheme == 'https' and parsed.hostname == 'eoffice.becamexijc.com' and not parsed.username and not parsed.password and parsed.port in (None, 443)
        self.estatus.setText('Chưa đăng nhập — URL hợp lệ, session chưa xác minh' if valid else 'Lỗi — chỉ cho phép HTTPS eoffice.becamexijc.com')

    def choose_folder(self):
        folder = QFileDialog.getExistingDirectory(self, 'Chọn thư mục OneDrive')
        if folder: self.folder.setText(folder)

    def check_folder(self):
        value = self.folder.text().strip()
        if not value or (os.name != 'nt' and ('\\' in value or ':' in value)):
            self.ostatus.setText('Lỗi — cần đường dẫn native trên máy hiện tại'); return False
        path = Path(value).expanduser()
        valid = path.is_dir() and os.access(path, os.W_OK)
        self.ostatus.setText('Đã kết nối local — kiểm tra quyền sơ bộ; OneDrive sync chưa rõ' if valid else 'Lỗi — thư mục không tồn tại hoặc không có quyền ghi')
        return valid

    def save_config(self):
        if not self.check_folder(): return
        try:
            data = {'eoffice_url': self.url.text(), 'model': self.model.text(), 'groups': [g.text() for g in self.groups if g.isChecked()], 'output_dir': str(Path(self.folder.text()).expanduser().resolve())}
            parsed = urlparse(data['eoffice_url'])
            if parsed.scheme != 'https' or parsed.hostname != 'eoffice.becamexijc.com' or parsed.username or parsed.password or parsed.port not in (None, 443) or parsed.query != urlparse(EOFFICE_URL).query:
                raise ValueError('URL ngoài phạm vi hoặc query chưa được duyệt; không lưu để tránh chứa secret.')
            folder = state_dir(); folder.mkdir(parents=True, exist_ok=True)
            temporary = folder / 'settings.tmp'; temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8'); temporary.replace(folder / 'settings.json')
            os.environ['LUNA_OUTPUT_DIR'] = data['output_dir']
            QMessageBox.information(self, 'Đã lưu local', 'Đã lưu cấu hình không chứa key; chưa bật kết nối live.')
        except Exception:
            QMessageBox.warning(self, 'Lỗi', 'Không lưu cấu hình. Kiểm tra URL trong domain được phép và quyền thư mục.')

    def load_config(self):
        try:
            data = json.loads((state_dir() / 'settings.json').read_text(encoding='utf-8'))
            self.folder.setText(data.get('output_dir', self.folder.text()))
            self.url.setText(data.get('eoffice_url', EOFFICE_URL)); self.model.setText(data.get('model', ''))
            for group in self.groups: group.setChecked(group.text() in data.get('groups', list(GROUPS)))
            if data.get('output_dir'): os.environ.setdefault('LUNA_OUTPUT_DIR', data['output_dir'])
        except (OSError, ValueError, TypeError):
            pass
