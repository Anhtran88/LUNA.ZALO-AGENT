"""Offline services. No network clients or credential loading."""
from dataclasses import dataclass, asdict
from pathlib import Path
import struct
import zlib
import hashlib
import json
import os
import shutil
import time
import uuid

GROUPS = ('ĐỐI CHIẾU KL- KẾ TOÁN IJC', 'TDC-ĐỐI CHIẾU KL BÊ TÔN', 'My Documents')
EOFFICE_URL = 'https://eoffice.becamexijc.com/workflow/sitepages/workflowdynamicrequest.aspx?rcid=8&rscid=0&wid=0'


def resolve_group(name: str, available: list[str]) -> str:
    if name not in GROUPS or available.count(name) != 1:
        raise ValueError('Nhóm không được phép, không tìm thấy hoặc trùng tên. Hãy chọn lại nhóm chính xác.')
    return name


def output_dir() -> Path:
    configured = os.environ.get('LUNA_OUTPUT_DIR')
    if os.name != 'nt':
        if not configured or '\\' in configured or ':' in configured:
            raise ValueError('Linux: cần LUNA_OUTPUT_DIR là đường dẫn local; không dùng đường dẫn Windows.')
        return Path(configured).expanduser().resolve()
    if not configured:
        raise ValueError('Chọn thư mục đích trong Cấu hình hoặc đặt LUNA_OUTPUT_DIR trước khi lưu.')
    return Path(configured).expanduser().resolve()


def state_dir() -> Path:
    configured = os.environ.get('LUNA_STATE_DIR')
    base = Path(configured) if configured else Path(os.environ.get('LOCALAPPDATA', str(Path.home() / '.local' / 'share'))) / 'Luna' / 'offline'
    return base.expanduser().resolve()


class Outbox:
    """Durable local pending records. No cloud synchronization yet."""
    def add(self, kind: str, data: dict) -> dict:
        record = dict(data, id=uuid.uuid4().hex, kind=kind, created_at=time.time(), sync_state='pending_sync')
        folder = state_dir()
        folder.mkdir(parents=True, exist_ok=True)
        target = folder / (record['id'] + '.json')
        temporary = folder / (record['id'] + '.pending')
        with temporary.open('x', encoding='utf-8') as stream:
            json.dump(record, stream, ensure_ascii=False, indent=2)
            stream.flush()
            os.fsync(stream.fileno())
        temporary.replace(target)
        return record

    def records(self, kind: str | None = None) -> list[dict]:
        records = []
        for path in state_dir().glob('*.json'):
            if path.name == 'settings.json':
                continue
            try:
                record = json.loads(path.read_text(encoding='utf-8'))
                if isinstance(record, dict) and record.get('id') and record.get('kind'):
                    if kind is None or record['kind'] == kind:
                        records.append(record)
            except (OSError, ValueError):
                records.append({'id': path.stem, 'kind': 'error', 'sync_state': 'corrupt_local_record', 'created_at': 0})
        return sorted(records, key=lambda row: row.get('created_at', 0), reverse=True)



@dataclass(frozen=True)
class ChatRequest:
    messages: list[dict[str, str]]
    model: str = 'mock-openai'


class MockModel:
    def complete(self, request: ChatRequest) -> dict:
        prompt = request.messages[-1]['content'] if request.messages else ''
        return {'choices': [{'message': {'role': 'assistant', 'content': '[MOCK — không gọi AI] Yêu cầu đã nhận: ' + prompt + '\nChọn tab Zalo hoặc eOffice để xem dữ liệu mẫu.'}}], 'usage': {'total_tokens': 0}, 'cost': 0}


@dataclass(frozen=True)
class SampleFile:
    id: str
    group: str
    name: str
    content: bytes


def sample_files(group: str) -> list[SampleFile]:
    resolve_group(group, list(GROUPS))
    def chunk(kind, payload):
        return struct.pack('!I', len(payload)) + kind + payload + struct.pack('!I', zlib.crc32(kind + payload) & 0xffffffff)
    png = b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('!IIBBBBB', 1, 1, 8, 2, 0, 0, 0)) + chunk(b'IDAT', zlib.compress(b'\x00\x30\x80\xc0')) + chunk(b'IEND', b'')

    objects = [b'<< /Type /Catalog /Pages 2 0 R >>', b'<< /Type /Pages /Kids [3 0 R] /Count 1 >>', b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 200 200] /Resources << >> /Contents 4 0 R >>', b'<< /Length 0 >>\nstream\n\nendstream']
    pdf = b'%PDF-1.4\n'
    offsets = [0]
    for i, obj in enumerate(objects, 1):
        offsets.append(len(pdf))
        pdf += f'{i} 0 obj\n'.encode() + obj + b'\nendobj\n'
    start = len(pdf)
    pdf += b'xref\n0 5\n0000000000 65535 f \n'
    pdf += b''.join(f'{offset:010d} 00000 n \n'.encode() for offset in offsets[1:])
    pdf += f'trailer\n<< /Size 5 /Root 1 0 R >>\nstartxref\n{start}\n%%EOF\n'.encode()
    return [SampleFile('mock-image', group, 'MOCK-image.png', png), SampleFile('mock-pdf', group, 'MOCK-document.pdf', pdf)]


def save_selected(sample: SampleFile, selected_group: str, available: list[str], outbox: Outbox) -> dict:
    resolve_group(selected_group, available)
    if sample.group != selected_group:
        raise ValueError('File không thuộc nhóm đã chọn.')
    if Path(sample.name).suffix.lower() not in {'.png', '.jpg', '.jpeg', '.pdf'}:
        raise ValueError('Chỉ hỗ trợ ảnh/PDF.')
    return save_local(sample.name, sample.content, {'group': selected_group, 'fixture': True}, outbox)


def save_local(name: str, content: bytes, source: dict, outbox: Outbox) -> dict:
    folder = output_dir()
    folder.mkdir(parents=True, exist_ok=True)
    free = shutil.disk_usage(folder).free
    if free < len(content) + 100 * 1024 * 1024:
        raise OSError('Dung lượng thấp: chặn lưu mới, không tự xóa file.')
    if not name or '/' in name or '\\' in name or ':' in name or name in {'.', '..'}:
        raise ValueError('Tên file không hợp lệ.')
    safe_name = Path(name).name
    destination = folder / (uuid.uuid4().hex + '-' + safe_name)
    try:
        with destination.open('xb') as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
    except OSError as exc:
        raise OSError(f'Không hoàn tất lưu file tại {destination}. Kiểm tra dung lượng/quyền; không tự thử lại hoặc xóa file dở.') from exc

    metadata = {'stored_name': destination.name, 'original_name': safe_name, 'relative_path': destination.name, 'sha256': hashlib.sha256(content).hexdigest(), 'bytes': len(content), 'local_state': 'saved', 'source': source, 'onedrive_state': 'unknown'}
    try:
        record = outbox.add('file', metadata)
    except OSError as exc:
        raise OSError(f'File đã lưu tại {destination}, nhưng metadata chưa lưu được. Không tự tải lại để tránh trùng.') from exc
    return record


def make_report(group: str, outbox: Outbox, start: str | None = None, end: str | None = None) -> dict:
    from datetime import date, timedelta
    start = start or str(date.today() - timedelta(days=1))
    end = end or str(date.today())
    messages = mock_messages(group, start, end)
    task = outbox.add('task', {'type': 'mock_report', 'group': group, 'status': 'completed_mock', 'start': start, 'end': end})
    lines = [f'[DỮ LIỆU MẪU] {group}', f'Khoảng thời gian: {start} → {end}', f'{len(messages)} tin nhắn mẫu; {len(sample_files(group))} file mẫu độc lập.', 'Tóm tắt theo nội dung mẫu, không gọi AI:']
    lines += [f'- {m.text} [nguồn: {m.id}, {m.timestamp}]' for m in messages]
    if not messages:
        lines.append('Không có tin nhắn mẫu trong khoảng đã chọn.')
    lines.append('Chưa đọc Zalo thật. Không dùng làm báo cáo nghiệp vụ.')
    report = outbox.add('report', {'task_id': task['id'], 'group': group, 'start': start, 'end': end, 'messages': [asdict(m) for m in messages], 'text': '\n'.join(lines), 'fixture': True})
    outbox.add('audit', {'action': 'mock_report_created', 'task_id': task['id'], 'report_id': report['id']})
    return report


def edit_preview(record: str, field: str, current: str, proposed: str) -> dict:
    return {'record': record, 'field': field, 'current': current, 'proposed': proposed, 'mode': 'dry_run', 'executable': False}


@dataclass(frozen=True)
class MockMessage:
    id: str
    group: str
    timestamp: str
    sender: str
    text: str


def mock_messages(group: str, start: str, end: str) -> list[MockMessage]:
    from datetime import date, datetime, timedelta
    resolve_group(group, list(GROUPS))
    first, last = date.fromisoformat(start), date.fromisoformat(end)
    if first > last:
        raise ValueError('Ngày bắt đầu phải trước hoặc bằng ngày kết thúc.')
    today = date.today()
    messages = [
        MockMessage('sample-1', group, f'{today - timedelta(days=1)}T09:00:00', 'Người dùng mẫu A', 'Đề nghị đối chiếu khối lượng trong tài liệu mẫu.'),
        MockMessage('sample-2', group, f'{today}T10:00:00', 'Người dùng mẫu B', 'Cần kiểm tra lại số liệu trước khi lập báo cáo.'),
        MockMessage('sample-3', group, f'{today}T14:00:00', 'Người dùng mẫu A', 'Ảnh và PDF mẫu đã sẵn sàng để đối chiếu.'),
    ]
    return [m for m in messages if first <= datetime.fromisoformat(m.timestamp).date() <= last]


EOFFICE_RECORDS = (
    {'id': 'MOCK-001', 'title': 'Hồ sơ đối chiếu mẫu', 'status': 'Chờ xử lý', 'quantity': 12},
    {'id': 'MOCK-002', 'title': 'Hồ sơ vật tư mẫu', 'status': 'Đã kiểm tra', 'quantity': 8},
)


def validate_site(value: str) -> str:
    from urllib.parse import urlsplit
    try:
        parsed = urlsplit(value)
        valid = (parsed.scheme == 'https' and parsed.hostname == 'eoffice.becamexijc.com'
                 and parsed.port in (None, 443) and not parsed.username and not parsed.password
                 and not parsed.fragment and parsed.path == '/workflow/sitepages/workflowdynamicrequest.aspx'
                 and parsed.query == 'rcid=8&rscid=0&wid=0')
    except ValueError:
        valid = False
    if not valid:
        raise ValueError('Chỉ cho phép URL trang eOffice đã duyệt, không chứa credential hoặc tham số bổ sung.')
    return value
