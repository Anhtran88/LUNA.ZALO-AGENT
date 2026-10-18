"""Local GUI selection regression; never opens a browser or reads credentials."""
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from PySide6.QtWidgets import QApplication
from luna.app import Window
from luna.core import GROUPS


class GroupSelectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.env = patch.dict(os.environ, {'LUNA_STATE_DIR': str(Path(self.temp.name)/'state'), 'LUNA_OUTPUT_DIR': self.temp.name})
        self.env.start(); self.window = Window()

    def tearDown(self):
        self.window.browser.shutdown().result(timeout=5)
        self.window.browser_closed = True; self.window.close()
        self.env.stop(); self.temp.cleanup()

    def test_only_my_documents_is_selected_and_read(self):
        w = self.window
        w.settings.groups[0].setChecked(False); w.settings.groups[1].setChecked(False)
        self.assertEqual(w.groups.currentText(), GROUPS[2])
        self.assertEqual(w.settings.target_group.currentText(), GROUPS[2])
        w.allowed_group()
        w.settings.zlogin.setChecked(True)
        with patch.object(w, 'run_browser') as run:
            w.read_browser('zalo')
        self.assertEqual(run.call_args.args[-1], GROUPS[2])

    def test_two_way_selection_and_no_groups(self):
        w = self.window
        w.settings.target_group.setCurrentText(GROUPS[1]); self.assertEqual(w.groups.currentText(), GROUPS[1])
        w.groups.setCurrentText(GROUPS[2]); self.assertEqual(w.settings.target_group.currentText(), GROUPS[2])
        for group in w.settings.groups: group.setChecked(False)
        self.assertEqual(w.groups.count(), 0); self.assertEqual(w.settings.target_group.count(), 0)
        with self.assertRaises(ValueError): w.allowed_group()
        self.assertEqual(w.samples, [])

    def test_revoking_group_invalidates_files(self):
        w = self.window
        w.live_snapshot = {'group': GROUPS[0]}
        w.settings.groups[0].setChecked(False)
        self.assertIsNone(w.live_snapshot)
        self.assertEqual(w.groups.currentIndex(), -1)
        self.assertEqual(w.settings.target_group.currentIndex(), -1)

    def test_empty_content_is_explained_without_report(self):
        w = self.window
        snapshot = {'group': GROUPS[0], 'messages': [], 'files': [], 'content_state': 'content_not_loaded', 'warning': 'Vùng nội dung chưa tải', 'diagnostics': {'counts': {'pane': 1}}}
        w.show_zalo(snapshot)
        self.assertIn('content_not_loaded', w.settings.zstatus.text())
        self.assertIn('chưa tải', w.live_text.toPlainText())
        with self.assertRaises(ValueError): w.report_live()
        self.assertEqual(w.outbox.records('report'), [])

    def test_dashboard_counts_exclude_mock_records(self):
        w = self.window
        w.outbox.add('file', {'source': {'fixture': True}})
        w.outbox.add('report', {'fixture': True})
        w.refresh_dashboard()
        self.assertEqual([value.text() for value in w.dashboard.values], ['0', '0', '0', '0'])
        w.outbox.add('file', {'source': {'fixture': False}})
        w.outbox.add('report', {'fixture': False})
        w.live_snapshot = {'group': GROUPS[0], 'messages': ['one', 'two'], 'files': [{'id': 'file-ref'}], 'warning': 'Fixture snapshot for UI regression'}
        w.refresh_dashboard()
        self.assertEqual([value.text() for value in w.dashboard.values], ['2', '1', '1', '1'])

    def test_dashboard_actions_require_login_and_never_poll(self):
        w = self.window
        self.assertFalse(w.dashboard.read_button.isEnabled())
        self.assertFalse(w.dashboard.pause_button.isEnabled())
        w.settings.zlogin.setChecked(True)
        self.assertTrue(w.dashboard.read_button.isEnabled())
        with patch.object(w, 'read_browser') as read:
            w.dashboard.read_button.click()
        read.assert_called_once_with('zalo')
        self.assertIsNone(w.pending_browser)

    def test_sidebar_keeps_existing_pages_and_default_dashboard(self):
        w = self.window
        self.assertEqual(w.tabs.currentIndex(), 7)
        self.assertTrue(w.tabs.tabBar().isHidden())
        with patch.object(w.browser, 'submit') as submit:
            for page in range(w.tabs.count()):
                w.shell.navigate(page)
                self.assertEqual(w.tabs.currentIndex(), page)
                self.assertGreaterEqual(w.shell.navigation.currentRow(), 0)
            submit.assert_not_called()
