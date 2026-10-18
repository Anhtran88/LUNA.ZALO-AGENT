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
