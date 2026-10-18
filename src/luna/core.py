"""Offline services. No network clients or credential loading."""
from dataclasses import dataclass, asdict
from pathlib import Path
import base64
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
        with target.open('x', encoding='utf-8') as stream:
            json.dump(record, stream, ensure_ascii=False, indent=2)
        return record


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
    png = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jRZkAAAAASUVORK5CYII=')
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
    safe_name = Path(name).name
    destination = folder / (uuid.uuid4().hex + '-' + safe_name)
    with destination.open('xb') as stream:
        stream.write(content)
        stream.flush()
        os.fsync(stream.fileno())
    metadata = {'stored_name': destination.name, 'original_name': safe_name, 'relative_path': destination.name, 'sha256': hashlib.sha256(content).hexdigest(), 'bytes': len(content), 'source': source, 'onedrive_state': 'unknown'}
    try:
        record = outbox.add('file', metadata)
    except OSError as exc:
        raise OSError(f'File đã lưu tại {destination}, nhưng metadata chưa lưu được. Không tự tải lại để tránh trùng.') from exc
    return record


def make_report(group: str, outbox: Outbox) -> dict:
    resolve_group(group, list(GROUPS))
    task = outbox.add('task', {'type': 'mock_report', 'group': group, 'status': 'completed_mock'})
    report = outbox.add('report', {'task_id': task['id'], 'group': group, 'text': f'[DỮ LIỆU MẪU] {group}\n2 tin nhắn giả lập: yêu cầu đối chiếu và nhắc kiểm tra tài liệu.\n2 file mẫu. Chưa đọc Zalo, chưa lọc khoảng thời gian. Không dùng làm báo cáo nghiệp vụ.', 'fixture': True})
    outbox.add('audit', {'action': 'mock_report_created', 'task_id': task['id'], 'report_id': report['id']})
    return report


def edit_preview(record: str, field: str, current: str, proposed: str) -> dict:
    return {'record': record, 'field': field, 'current': current, 'proposed': proposed, 'mode': 'dry_run', 'executable': False}
