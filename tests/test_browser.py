"""Read-only safety checks using local HTML and fake downloads, never live sites."""
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from luna.browser import BrowserWorker, BrowserSession, BrowserError, check_zalo_group, validate_binary, private_directory
from luna.core import GROUPS, EOFFICE_URL, Outbox, sample_files


class BrowserFixtureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from playwright.sync_api import sync_playwright
        cls.driver = sync_playwright().start()
        executable = os.environ.get('LUNA_TEST_CHROMIUM')
        try:
            cls.browser = cls.driver.chromium.launch(headless=True, **({'executable_path': executable} if executable else {}))
        except Exception:
            cls.driver.stop()
            raise

    @classmethod
    def tearDownClass(cls):
        cls.browser.close(); cls.driver.stop()

    def setUp(self):
        self.context = self.browser.new_context(accept_downloads=True)
        self.page = self.context.new_page()
        self.worker = BrowserWorker()
        self.temp = tempfile.TemporaryDirectory()
        self.env = patch.dict(os.environ, {'LUNA_OUTPUT_DIR': self.temp.name, 'LUNA_STATE_DIR': str(Path(self.temp.name)/'state')})
        self.env.start()

    def tearDown(self):
        self.worker.executor.shutdown(wait=True)
        self.context.close(); self.env.stop(); self.temp.cleanup()

    def zalo(self, duplicate=False, identity='group-1'):
        title = GROUPS[0]
        entries = f'<div data-conversation-id="group-1"><span class="conv-item-title__name">{title}</span></div>'
        if duplicate: entries += entries
        html = f'<div id="conversationList">{entries}</div><div id="header"><h1 class="header-title">{title}</h1></div><div id="messageView" data-conversation-id="{identity}"><p class="text-message">Nội dung fixture</p><a download="sample.pdf" href="https://files.zaloapp.com/sample.pdf">PDF</a></div>'
        self.page.route('**/*', lambda route: route.fulfill(body=html, content_type='text/html; charset=utf-8'))
        self.page.goto('https://chat.zalo.me/')
        self.worker.sessions['zalo'] = BrowserSession(self.context, self.page)

    def test_exact_read_and_duplicates(self):
        self.zalo()
        self.page.locator('#conversationList').evaluate('(el) => el.insertAdjacentHTML("afterbegin", "<div data-conversation-id=wrong><span class=conv-item-title__name>ĐỐI CHIẾU KL- KẾ TOÁN IJC khác</span></div>")')
        snapshot = self.worker.read_zalo(GROUPS[0])
        self.assertEqual(snapshot['messages'], ['Nội dung fixture'])
        self.assertEqual(len(snapshot['files']), 1)
        self.assertNotIn('https://', str(snapshot))
        self.page.locator('#conversationList').evaluate('(el) => el.innerHTML += el.innerHTML')
        with self.assertRaises(ValueError): self.worker.read_zalo(GROUPS[0])

    def test_mismatch_and_missing_identity(self):
        self.zalo(identity='other')
        with self.assertRaises(BrowserError): self.worker.read_zalo(GROUPS[0])
        self.page.locator('#messageView').evaluate('(el) => el.removeAttribute("data-conversation-id")')
        with self.assertRaises(BrowserError): self.worker.read_zalo(GROUPS[0])

    def observed_layout(self):
        title = GROUPS[0]
        html = f'''<div style="display:none">{title}</div>
        <div id="conversationList"><div class="msg-item" data-id="real-row-1">
        <div class="gridv2 conv-item selected"><div class="conv-item-title__name truncate grid-item"><div class="truncate">{title}</div></div></div></div></div>
        <div id="header"><div class="header-title"><span>{title}</span></div></div>
        <div id="messageView"><div class="text-message">Tin nhắn của nhóm đang chọn</div></div>'''
        self.page.route('**/*', lambda route: route.fulfill(body=html, content_type='text/html; charset=utf-8'))
        self.page.goto('https://chat.zalo.me/')
        self.worker.sessions['zalo'] = BrowserSession(self.context, self.page)

    def test_observed_sidebar_header_hidden_label_are_one_group(self):
        self.observed_layout()
        self.assertEqual(check_zalo_group(self.page, GROUPS[0]), 'selected-row:real-row-1')
        self.assertEqual(self.worker.read_zalo(GROUPS[0])['messages'], ['Tin nhắn của nhóm đang chọn'])

    def test_observed_layout_requires_selected_row_and_unique_name(self):
        self.observed_layout()
        self.page.locator('.conv-item').evaluate('(el) => el.classList.remove("selected")')
        with self.assertRaises(BrowserError): self.worker.read_zalo(GROUPS[0])
        self.page.locator('.conv-item').evaluate('(el) => el.classList.add("selected")')
        self.page.locator('#conversationList').evaluate('(el) => el.innerHTML += el.innerHTML')
        with self.assertRaises(BrowserError): self.worker.read_zalo(GROUPS[0])

    def test_nested_title_nodes_are_not_duplicate_groups(self):
        self.observed_layout()
        self.page.locator('.conv-item-title__name .truncate').evaluate('(el) => el.classList.add("conv-item-title__name")')
        self.assertEqual(check_zalo_group(self.page, GROUPS[0]), 'selected-row:real-row-1')

    def test_title_badge_does_not_change_exact_group_label(self):
        self.observed_layout()
        self.page.locator('.conv-item-title__name').evaluate('(el) => el.insertAdjacentHTML("beforeend", "<span>49 phút</span>")')
        self.assertEqual(check_zalo_group(self.page, GROUPS[0]), 'selected-row:real-row-1')
        with self.assertRaisesRegex(BrowserError, 'My Documents'):
            check_zalo_group(self.page, GROUPS[2])

    def test_attachment_only_conversation_is_readable(self):
        self.zalo()
        self.page.locator('.text-message').evaluate('(el) => el.remove()')
        result = self.worker.read_zalo(GROUPS[0])
        self.assertEqual(result['content_state'], 'files_only')
        self.assertEqual(result['messages'], [])
        self.assertEqual(len(result['files']), 1)

    def test_empty_pane_is_not_group_or_login_failure(self):
        self.observed_layout()
        self.page.locator('#messageView').evaluate('(el) => {el.innerHTML=""; el.style.minHeight="100px";}')
        result = self.worker.read_zalo(GROUPS[0])
        self.assertEqual(result['content_state'], 'content_not_loaded')
        self.assertEqual(result['files'], [])
        self.assertEqual(result['messages'], [])

    def test_unsupported_message_layout_is_not_faked_as_empty(self):
        self.observed_layout()
        self.page.locator('.text-message').evaluate('(el) => el.className="unknown-message-layout"')
        result = self.worker.read_zalo(GROUPS[0])
        self.assertEqual(result['content_state'], 'unsupported_layout')
        self.assertEqual(result['messages'], [])

    def test_diagnostics_excludes_private_content_and_urls(self):
        import json
        self.zalo()
        self.page.locator('#messageView').evaluate('(el) => el.insertAdjacentHTML("beforeend", "<div class=message-body>PRIVATE_CONTENT_SENTINEL</div>")')
        encoded = json.dumps(self.worker.diagnose_zalo(), ensure_ascii=False)
        self.assertNotIn('PRIVATE_CONTENT_SENTINEL', encoded)
        self.assertNotIn(GROUPS[0], encoded)
        self.assertNotIn('https://', encoded)
        self.assertNotIn('group-1', encoded)

    def test_download_expiry_and_validation(self):
        self.zalo()
        snapshot = self.worker.read_zalo(GROUPS[0]); token = snapshot['files'][0]['id']
        self.page.locator('#header .header-title').evaluate('(el) => el.textContent="Other"')
        with self.assertRaises(BrowserError): self.worker.download(GROUPS[0],[token],Outbox(),self.temp.name)
        for sample in sample_files(GROUPS[0]): validate_binary(sample.name,sample.content)
        with self.assertRaises(BrowserError): validate_binary('fake.pdf',b'<html>login</html>')

    def test_selected_download_stays_local_with_hash(self):
        import hashlib
        self.zalo()
        pdf = sample_files(GROUPS[0])[1].content
        self.page.route('https://files.zaloapp.com/sample.pdf', lambda route: route.fulfill(
            body=pdf, content_type='application/pdf', headers={'Content-Disposition': 'attachment; filename="sample.pdf"'}))
        snapshot = self.worker.read_zalo(GROUPS[0])
        result = self.worker.download(GROUPS[0], [snapshot['files'][0]['id']], Outbox(), self.temp.name)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['sha256'], hashlib.sha256(pdf).hexdigest())
        self.assertEqual((Path(self.temp.name)/result[0]['relative_path']).read_bytes(), pdf)
        self.assertEqual(result[0]['onedrive_state'], 'unknown')
        self.assertNotIn('https://', str(result))

    def test_eoffice_read_only_table(self):
        html = '<table><tr><th>Mã</th><th>Giá trị</th></tr><tr><td>A</td><td>12</td></tr></table>'
        self.page.route('**/*',lambda route:route.fulfill(body=html,content_type='text/html; charset=utf-8'))
        self.page.goto(EOFFICE_URL)
        self.worker.sessions['eoffice'] = BrowserSession(self.context,self.page)
        snapshot = self.worker.read_eoffice(); self.assertEqual(snapshot['count'],1)
        self.page.evaluate('document.body.innerHTML += document.body.innerHTML')
        with self.assertRaises(BrowserError): self.worker.read_eoffice()

    def test_live_launch_prohibited_on_cloud(self):
        if os.name != 'nt':
            with self.assertRaises(BrowserError): private_directory()


if __name__ == '__main__': unittest.main()
