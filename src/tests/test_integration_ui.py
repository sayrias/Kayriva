import os
import unittest
from pathlib import Path
from types import SimpleNamespace

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QListWidgetItem
from PySide6.QtCore import Qt

from ai_studio.i18n import set_language
from ai_studio.config import Settings
from ai_studio.ui.integrations import ExtensionBrowser, GitHubPanel


class IntegrationUITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        set_language("tr")
        self.window = QMainWindow()
        self.window.setCentralWidget(QWidget())
        self.window.config = SimpleNamespace(root=Path(__file__).resolve().parents[2], settings=Settings())

    def tearDown(self):
        self.window.close()
        self.window.deleteLater()
        self.app.processEvents()

    def test_extension_filter_and_empty_state_without_installing(self):
        panel = ExtensionBrowser(self.window)
        self.window.centralWidget().layout()
        self.assertEqual(panel.list.count(), 17)
        panel.category.setCurrentText('Belgeler')
        self.assertEqual(panel.list.count(), 1)
        self.assertIn('MarkItDown', panel.publisher.text())
        self.assertFalse(panel.enable.isChecked())
        panel.search.setText('bulunmayacak-araç')
        self.assertEqual(panel.list.count(), 0)
        self.assertIn('bulunamadı', panel.status.text())
        panel.deleteLater()

    def test_github_publishing_needs_account_review_and_correct_project(self):
        panel = GitHubPanel(self.window, '/tmp/selected-project')
        self.assertEqual(panel.path.text(), '/tmp/selected-project')
        self.assertTrue(panel.private.isChecked())
        panel.mode.setCurrentIndex(1)
        panel.name.setText('test-project')
        panel.confirm.setChecked(True)
        self.assertFalse(panel.publish_button.isEnabled())
        panel.account_ready = True
        panel.update_publish()
        self.assertTrue(panel.publish_button.isEnabled())
        panel.mode.setCurrentIndex(0)
        self.assertFalse(panel.publish_button.isEnabled())
        panel.preview = object()
        selected = QListWidgetItem('README.md')
        selected.setCheckState(Qt.CheckState.Checked)
        panel.files.addItem(selected)
        panel.confirm.setChecked(True)
        panel.update_publish()
        self.assertTrue(panel.publish_button.isEnabled())
        panel.path.setText('/tmp/different-project')
        self.assertIsNone(panel.preview)
        self.assertFalse(panel.confirm.isChecked())
        self.assertFalse(panel.publish_button.isEnabled())
        panel.deleteLater()


if __name__ == '__main__':
    unittest.main()
