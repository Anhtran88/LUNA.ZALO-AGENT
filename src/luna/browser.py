"""Headed, user-driven read-only browser adapters.

DOM selectors are conservative and version-dependent. Missing/ambiguous markers
stop extraction; never fall back to reading the full page or sending messages.
All Playwright objects are owned by the single BrowserWorker thread.
"""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit
import os
import uuid
from .core import GROUPS, EOFFICE_URL, save_local

ZALO_URL = 'https://chat.zalo.me/'
MAX_FILE_BYTES = 25 * 1024 * 1024
CONTENT_WAIT_MS = 1500
# Deliberately scoped to conversation navigation/header/message areas.
GROUP_ITEM = '#conversationList .conv-item-title__name'
GROUP_HEADER = '#header .header-title'
MESSAGE = '#messageView .text-message'
ATTACHMENT = '#messageView a[download]'


class BrowserError(ValueError):
    pass


def private_directory() -> Path:
    if os.name != 'nt':
        raise BrowserError('Browser thật chỉ hỗ trợ Windows. Không mở tài khoản trên cloud Linux.')
    appdata = os.environ.get('LOCALAPPDATA')
    if not appdata:
        raise BrowserError('Không tìm thấy LOCALAPPDATA.')
    directory = (Path(appdata) / 'Luna' / 'private').resolve()
    checkout = Path(__file__).resolve().parents[2]
    prohibited = [checkout]
    for name in ('OneDrive', 'OneDriveConsumer', 'OneDriveCommercial'):
        if os.environ.get(name): prohibited.append(Path(os.environ[name]).resolve())
    if any(root == directory or root in directory.parents for root in prohibited) or 'onedrive' in str(directory).lower():
        raise BrowserError('Profile phải nằm trong AppData local, ngoài Git và OneDrive.')
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def visible_unique(locator, description):
    visible = [locator.nth(i) for i in range(locator.count()) if locator.nth(i).is_visible()]
    if len(visible) != 1:
        raise BrowserError(f'{description}: không tìm thấy hoặc trùng/không rõ. Hãy chọn lại; app không chọn gần đúng.')
    return visible[0]


def check_zalo_group(page, group):
    if group not in GROUPS: raise BrowserError('Nhóm không được phép.')
    if urlsplit(page.url).hostname != 'chat.zalo.me':
        raise BrowserError('Chưa ở Zalo Web; người dùng cần tự đăng nhập.')
    # Only count names inside the conversation list, never global exact-text
    # matches (the same label also appears in header and hidden translations).
    items = page.locator(GROUP_ITEM)
    candidates = []
    rows = set()
    for index in range(items.count()):
        item = items.nth(index)
        info = item.evaluate(r"""(el, group) => {
            const clean = s => (s || '').replace(/\s+/g, ' ').trim();
            const labels = [el, ...el.querySelectorAll('.truncate, [data-translate-inner]')];
            const match = labels.some(label => clean(label.innerText) === clean(group));
            const row = el.closest('.msg-item[data-id], [data-conversation-id], .conv-item') || el;
            // Element index distinguishes real duplicate rows even if their IDs repeat.
            const rowIndex = Array.from(document.querySelectorAll('#conversationList *')).indexOf(row);
            return {match, rowIndex};
        }""", group)
        if info['match'] and info['rowIndex'] not in rows:
            rows.add(info['rowIndex']); candidates.append(item)
    count = len(candidates)
    if count == 0:
        raise BrowserError(f'Đang tìm “{group}”: chưa thấy tên khớp trong danh sách (vùng danh sách: {page.locator("#conversationList").count()}, phần tử tên: {items.count()}). Hãy kiểm tra Nhóm sẽ đọc và tự mở nhóm; không cần đồng bộ/gửi gì.')
    if count > 1:
        raise BrowserError(f'Đang tìm “{group}”: có {count} dòng hội thoại cùng tên. Dừng để tránh đọc nhầm; cần xác định đúng nhóm.')
    item = candidates[0]
    if not item.is_visible():
        raise BrowserError(f'Nhóm “{group}” chưa hiển thị trong danh sách. Hãy tự mở đúng nhóm rồi thử lại.')
    header = visible_unique(page.locator(GROUP_HEADER), 'Tiêu đề nhóm')
    if ' '.join(header.inner_text().split()) != ' '.join(group.split()):
        raise BrowserError('Nhóm đang mở không khớp nhóm được phép. Tự mở đúng nhóm rồi thử lại.')
    pane = visible_unique(page.locator('#messageView'), 'Vùng tin nhắn')
    # Legacy fixture/DOM with explicit IDs on both sides.
    entry = item.locator('xpath=ancestor::*[@data-conversation-id][1]')
    if entry.count() == 1 and pane.get_attribute('data-conversation-id'):
        identity = entry.get_attribute('data-conversation-id')
        if identity and pane.get_attribute('data-conversation-id') == identity:
            return 'conversation:' + identity
        raise BrowserError('Định danh nhóm/nội dung không khớp; không đọc hoặc tải file.')
    # Observed Zalo layout: .msg-item[data-id] contains a .conv-item row.
    # Require an explicit selected marker; a matching header by itself is insufficient.
    row = item.locator('xpath=ancestor::*[contains(concat(" ", normalize-space(@class), " "), " conv-item ")][1]')
    owner = item.locator('xpath=ancestor::*[@data-id][1]')
    if row.count() != 1 or owner.count() != 1:
        raise BrowserError('Không xác định được dòng nhóm/data-id. Hãy mở nhóm trong danh sách; UI này cần kiểm tra thêm.')
    classes = (row.get_attribute('class') or '').split()
    selected = (row.get_attribute('aria-selected') == 'true' or 'selected' in classes
                or row.get_attribute('data-selected') == 'true')
    identity = owner.get_attribute('data-id')
    if not selected or not identity:
        raise BrowserError('Chưa xác nhận được dòng nhóm đang chọn. Hãy tự bấm đúng nhóm; app không tự đoán.')
    return 'selected-row:' + identity


def is_safe_attachment_url(value):
    try:
        parsed = urlsplit(value)
        host = parsed.hostname or ''
        return (parsed.scheme == 'https' and not parsed.username and not parsed.password
                and parsed.port in (None, 443)
                and (host == 'chat.zalo.me' or host == 'files.zaloapp.com'
                     or host.endswith('.zdn.vn')))
    except ValueError:
        return False


def validate_binary(name, content):
    suffix = Path(name).suffix.lower()
    valid = ((suffix == '.pdf' and content.startswith(b'%PDF-'))
             or (suffix == '.png' and content.startswith(b'\x89PNG\r\n\x1a\n'))
             or (suffix in ('.jpg', '.jpeg') and content.startswith(b'\xff\xd8\xff')))
    if not valid or len(content) > MAX_FILE_BYTES:
        raise BrowserError('File không phải ảnh/PDF hỗ trợ hoặc vượt giới hạn 25 MiB.')


def zalo_diagnostics(page):
    """Structural metadata only: no text, HTML, URL, IDs, attributes or secrets."""
    selectors = {'list': '#conversationList', 'titles': GROUP_ITEM, 'header': GROUP_HEADER,
                 'pane': '#messageView', 'text_messages': MESSAGE, 'download_links': ATTACHMENT,
                 'message_rows': '#messageView .chat-message, #messageView .message-item, #messageView [data-message-id]',
                 'images': '#messageView img', 'links': '#messageView a'}
    counts = {name: page.locator(selector).count() for name, selector in selectors.items()}
    panes = page.locator('#messageView')
    structure = {'visible_text_chars': 0, 'elements': 0, 'common_classes': []}
    if panes.count() == 1:
        structure = panes.evaluate(r"""el => {
            const classes = new Map();
            const nodes = [...el.querySelectorAll('*')];
            for (const node of nodes) for (const name of node.classList) {
                if (/^[a-zA-Z_-]{1,48}$/.test(name)) classes.set(name, (classes.get(name) || 0) + 1);
            }
            return {visible_text_chars: (el.innerText || '').trim().length, elements: nodes.length,
                    common_classes: [...classes.entries()].sort((a,b) => b[1]-a[1]).slice(0,24)};
        }""")
    return {'schema': 1, 'counts': counts, 'pane_structure': structure,
            'privacy': 'Chỉ số lượng/cấu trúc CSS. Không có tin nhắn, tên người, URL, cookie hoặc mã hội thoại.'}


@dataclass
class BrowserSession:
    context: object
    page: object


class BrowserWorker:
    def __init__(self):
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix='luna-browser')
        self.sessions = {}
        self.playwright = None
        self.attachments = {}
        self.closing = False

    def submit(self, operation, *args):
        if self.closing: raise BrowserError('Browser đang đóng.')
        return self.executor.submit(getattr(self, operation), *args)

    def open(self, site, url=None):
        directory = private_directory()  # prohibit live launch on cloud before importing/starting browser
        if site not in ('zalo', 'eoffice'): raise BrowserError('Site không được phép.')
        if site == 'eoffice':
            from .core import validate_site
            url = validate_site(url or EOFFICE_URL)
        else: url = ZALO_URL
        if not self.playwright:
            from playwright.sync_api import sync_playwright
            self.playwright = sync_playwright().start()
        if site in self.sessions:
            try:
                self.sessions[site].page.bring_to_front()
                return 'Browser đã mở. Đăng nhập thủ công; không tự xử lý OTP/CAPTCHA.'
            except Exception:
                self.sessions.pop(site, None)
        context = self.playwright.chromium.launch_persistent_context(
            str(directory / site), headless=False, accept_downloads=True,
            downloads_path=str(directory / 'downloads'))
        page = context.pages[0] if context.pages else context.new_page()
        page.set_default_timeout(5000)
        page.set_default_navigation_timeout(30000)
        self.sessions[site] = BrowserSession(context, page)
        page.goto(url, wait_until='domcontentloaded')
        return 'Đã mở browser. Hãy tự quét QR/đăng nhập, tự mở nhóm/trang cần đọc rồi bấm kiểm tra.'

    def page(self, site):
        session = self.sessions.get(site)
        if not session or session.page.is_closed():
            raise BrowserError('Chưa mở browser hoặc cửa sổ đã đóng. Hãy mở lại và tự đăng nhập.')
        return session.page

    def read_zalo(self, group):
        page = self.page('zalo')
        self.attachments.clear()
        identity = check_zalo_group(page, group)
        if not page.locator(MESSAGE + ', ' + ATTACHMENT).count():
            from playwright.sync_api import TimeoutError as PlaywrightTimeout
            try:
                page.wait_for_function('(selector) => !!document.querySelector(selector)',
                                       arg=MESSAGE + ', ' + ATTACHMENT, timeout=CONTENT_WAIT_MS)
            except PlaywrightTimeout:
                pass
        messages = [text.strip() for text in page.locator(MESSAGE).all_text_contents() if text.strip()]
        files = []
        links = page.locator(ATTACHMENT)
        for i in range(links.count()):
            link = links.nth(i)
            name = link.get_attribute('download') or ''
            href = link.get_attribute('href') or ''
            if (not link.is_visible() or Path(name).name != name or any(c in name for c in '/\\:')
                    or Path(name).suffix.lower() not in ('.png', '.jpg', '.jpeg', '.pdf')
                    or not is_safe_attachment_url(href)):
                continue
            token = uuid.uuid4().hex
            # Keep signed URLs only in memory; never expose them to logs/RTDB.
            self.attachments[token] = (group, identity, name, href)
            files.append({'id': token, 'name': name})
        if check_zalo_group(page, group) != identity:
            self.attachments.clear()
            raise BrowserError('Nhóm đã thay đổi trong khi đọc; hãy đọc lại.')
        from datetime import datetime, timezone
        diagnostics = zalo_diagnostics(page)
        if messages or files:
            state = 'ready' if messages else 'files_only'
            warning = f'Đúng nhóm “{group}”: {len(messages)} tin nhắn chữ, {len(files)} file tải được trong phần đang tải. Chưa bao gồm toàn bộ lịch sử.'
        elif diagnostics['pane_structure']['visible_text_chars'] or diagnostics['counts']['images'] or diagnostics['counts']['message_rows']:
            state = 'unsupported_layout'
            warning = f'Đúng nhóm “{group}”, có cấu trúc nội dung nhưng chưa nhận diện được tin/file hỗ trợ. Bấm Chẩn đoán cấu trúc; không đọc toàn trang để đoán.'
        else:
            state = 'content_not_loaded'
            warning = f'Đúng nhóm “{group}”, nhưng vùng nội dung chưa hiển thị tin nhắn/file. Đăng nhập không đồng nghĩa đã tải lịch sử. Kiểm tra trực tiếp trong Zalo rồi bấm Đọc lại; app không tự đồng bộ.'
        return {'observed_at': datetime.now(timezone.utc).isoformat(), 'group': group,
                'messages': messages, 'files': files, 'content_state': state,
                'diagnostics': diagnostics, 'warning': warning}

    def diagnose_zalo(self):
        page = self.page('zalo')
        if urlsplit(page.url).hostname != 'chat.zalo.me':
            raise BrowserError('Chưa ở Zalo Web.')
        return zalo_diagnostics(page)

    def download(self, group, tokens, outbox, output_folder):
        from .core import output_dir
        # Freeze output selected on UI thread, do not follow a subsequently edited setting.
        if str(output_dir()) != output_folder: raise BrowserError('Thư mục đã đổi. Hãy xác nhận tải lại.')
        page = self.page('zalo')
        results = []
        for token in tokens:
            check_zalo_group(page, group)
            if token not in self.attachments: raise BrowserError('Danh sách file đã hết hiệu lực; hãy đọc lại nhóm.')
            saved_group, identity, name, href = self.attachments[token]
            if saved_group != group or check_zalo_group(page, group) != identity:
                raise BrowserError('File không thuộc đúng định danh nhóm đang chọn.')
            links = page.locator(ATTACHMENT)
            matches = [links.nth(i) for i in range(links.count())
                       if links.nth(i).get_attribute('download') == name
                       and links.nth(i).get_attribute('href') == href and links.nth(i).is_visible()
                       and not links.nth(i).get_attribute('onclick')]
            if len(matches) != 1: raise BrowserError('File không còn duy nhất trên UI; hãy đọc lại nhóm.')
            with page.expect_download(timeout=15000) as pending:
                matches[0].click(timeout=5000, no_wait_after=True)
            download = pending.value
            if not is_safe_attachment_url(download.url):
                download.delete()
                raise BrowserError('URL tải đã chuyển ra ngoài host được phép; không lưu file.')
            if download.failure(): raise BrowserError('Browser không tải được file. Kiểm tra phiên/quyền truy cập.')
            temporary = Path(download.path())
            if temporary.stat().st_size > MAX_FILE_BYTES:
                download.delete()
                raise BrowserError('File vượt 25 MiB; không lưu vào thư mục đích.')
            content = temporary.read_bytes()
            validate_binary(name, content)
            if check_zalo_group(page, group) != identity: raise BrowserError('Nhóm đã đổi trong khi tải, không lưu file.')
            metadata = save_local(name, content, {'group': group, 'connector': 'zalo_browser', 'fixture': False}, outbox)
            download.delete()
            self.attachments.pop(token, None)
            results.append(metadata)
        return results

    def read_eoffice(self):
        page = self.page('eoffice')
        from .core import validate_site
        validate_site(page.url)
        if page.locator('input[type=password]:visible').count():
            raise BrowserError('Trang vẫn có form đăng nhập; hãy tự hoàn tất login trước khi đọc.')
        tables = page.locator('table:visible')
        candidates = []
        for i in range(tables.count()):
            table = tables.nth(i)
            if table.locator('th').count() and table.locator('tr').count() > 1:
                candidates.append(table)
        if len(candidates) != 1:
            raise BrowserError('Không nhận diện được một bảng dữ liệu duy nhất. Chọn đúng trang/bảng; không đọc toàn trang.')
        rows = []
        for row in candidates[0].locator('tr').all():
            cells = row.locator('th, td').all_text_contents()
            if cells: rows.append([cell.strip() for cell in cells])
        return {'rows': rows, 'count': len(rows) - 1,
                'warning': 'Chỉ thống kê số dòng bảng đang tải; chưa bao gồm trang khác, không suy diễn tổng nghiệp vụ.'}

    def close(self):
        for session in self.sessions.values():
            try: session.context.close()
            except Exception: pass
        self.sessions.clear(); self.attachments.clear()
        if self.playwright:
            self.playwright.stop(); self.playwright = None

    def shutdown(self):
        self.closing = True
        future = self.executor.submit(self.close)
        self.executor.shutdown(wait=False)
        return future
