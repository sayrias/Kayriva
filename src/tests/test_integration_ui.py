import os
import unittest
import tempfile
import threading
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QListWidgetItem
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest

from ai_studio.i18n import set_language
from ai_studio.config import Settings, Config
from ai_studio.ui.integrations import ExtensionBrowser, GitHubPanel, SkillsBrowser, IntegrationHub


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
        self.assertEqual(panel.list.count(), len(panel.library.entries))
        panel.category.setCurrentText('Belgeler')
        self.assertEqual(panel.list.count(), 1)
        self.assertIn('MarkItDown', panel.publisher.text())
        self.assertFalse(panel.enable.isChecked())
        panel.search.setText('bulunmayacak-araç')
        self.assertEqual(panel.list.count(), 0)
        self.assertIn('bulunamadı', panel.status.text())
        panel.deleteLater()

    def test_app_connections_share_real_enabled_configuration(self):
        self.window.config.save = Mock()
        self.window.refresh_mcp = Mock()
        self.window.config.settings.mcp_servers = [{'name':'GitHub', 'library_id':'github', 'enabled':False, 'transport':'http', 'url':'https://api.githubcopilot.com/mcp/'}]
        panel = ExtensionBrowser(self.window, apps_only=True)
        panel.search.setText('GitHub')
        self.assertEqual(panel.list.count(), 1)
        self.assertFalse(panel.enable.isChecked())
        with patch.dict(os.environ, {}, clear=True):
            panel.enable.setChecked(True)
            self.assertFalse(panel.enable.isChecked())
            self.assertFalse(self.window.config.settings.mcp_servers[0]['enabled'])
        with patch.dict(os.environ, {'KAYRIVA_GITHUB_AUTHORIZATION':'Bearer test-local-value'}):
            panel.enable.setChecked(True)
            self.assertTrue(self.window.config.settings.mcp_servers[0]['enabled'])
        self.window.config.save.assert_called_once()
        self.window.refresh_mcp.assert_called_once()
        panel.deleteLater()

    def test_hub_has_mcp_apps_skills_and_imported_skill_can_be_managed(self):
        with tempfile.TemporaryDirectory() as raw:
            self.window.config = Config(Path(raw))
            hub = IntegrationHub(self.window)
            self.assertEqual(hub.tabs.count(), 3)
            self.assertEqual(hub.tabs.tabText(0), 'MCP')
            self.assertGreater(hub.skills.list.count(), 0)
            self.assertTrue(all(hub.apps.list.item(i).data(Qt.ItemDataRole.UserRole).get('app') for i in range(hub.apps.list.count())))
            guide = Path(raw) / 'SKILL.md'
            guide.write_text('---\nname: project-helper\ndescription: Review Python project files carefully\n---\nRead relevant files before editing. See [review](references/review.md).\n')
            (Path(raw) / 'references').mkdir()
            (Path(raw) / 'references/review.md').write_text('Verify actual callers and preserve user changes.')
            hub.skills.import_path(guide)
            hub.skills.search.setText('project-helper')
            self.assertEqual(hub.skills.list.count(), 1)
            self.assertIn('Read relevant', hub.skills.preview.toPlainText())
            self.assertEqual(hub.skills.resource.count(), 2)
            hub.skills.resource.setCurrentIndex(1)
            self.assertIn('Verify actual callers', hub.skills.preview.toPlainText())
            self.assertTrue(hub.skills.enabled.isChecked())
            hub.skills.enabled.setChecked(False)
            self.assertFalse(next(e for e in hub.skills.library.entries() if e['name']=='project-helper')['enabled'])
            hub.skills.remove()
            self.assertEqual(hub.skills.list.count(), 0)
            self.assertTrue(guide.exists())
            hub.deleteLater()

    def test_library_preserves_provider_names_and_filters_transport_without_installing(self):
        panel = ExtensionBrowser(self.window)
        panel.search.setText('Chrome DevTools')
        self.assertEqual(panel.list.count(), 1)
        self.assertEqual(panel.title.text(), 'Chrome DevTools')
        self.assertFalse(panel.detail_icon.pixmap().isNull())
        panel.search.clear()
        panel.type_filter.setCurrentIndex(panel.type_filter.findData('remote'))
        for index in range(panel.list.count()):
            self.assertEqual(panel.list.item(index).data(Qt.ItemDataRole.UserRole)['kind'], 'http')
        panel.type_filter.setCurrentIndex(panel.type_filter.findData('installed'))
        self.assertEqual(panel.list.count(), 0)
        panel.set_installing(True)
        self.assertFalse(panel.search.isEnabled())
        self.assertFalse(panel.list.isEnabled())
        panel.set_installing(False)
        self.assertTrue(panel.search.isEnabled())
        panel.deleteLater()

    def test_original_impeccable_is_findable_previewable_and_added_without_running_programs(self):
        with tempfile.TemporaryDirectory() as raw:
            self.window.config = Config(Path(raw))
            panel = SkillsBrowser(self.window)
            panel.search.setText('impeccable')
            self.assertEqual(panel.list.count(), 1)
            self.assertEqual(panel.title.text(), 'impeccable')
            self.assertFalse(panel.enabled.isVisible())
            self.assertIn('Apache-2.0', panel.source.text())
            self.assertIn('design', panel.preview.toPlainText().lower())
            self.assertGreater(panel.resource.count(), 30)
            with patch('subprocess.Popen') as execute:
                panel.install_curated()
                execute.assert_not_called()
            self.assertTrue(panel.library.read('impeccable')['enabled'])
            panel.resource.setCurrentIndex(panel.resource.findData('reference/craft-floor.md'))
            self.assertIn('Contrast:',panel.preview.toPlainText())
            panel.remove()
            self.assertEqual(panel.list.count(),1)
            self.assertFalse(panel.list.item(0).data(Qt.ItemDataRole.UserRole)['installed'])
            panel.deleteLater()

    def test_compact_footer_keeps_checkbox_and_actions_clear_of_splitter(self):
        for language in ('en', 'tr'):
            with self.subTest(language=language):
                set_language(language)
                self.window.config.settings.mcp_servers = [{'name': 'GitHub', 'library_id': 'github', 'enabled': False}]
                panel = ExtensionBrowser(self.window)
                self.window.setCentralWidget(panel)
                self.window.resize(760, 620)
                self.window.show()
                panel.search.setText('GitHub')
                QTest.qWait(30)
                footer = panel.install_footer
                checkbox = panel.enable.geometry()
                self.assertGreaterEqual(checkbox.left(), 16)
                self.assertGreaterEqual(checkbox.top(), 12)
                self.assertLessEqual(checkbox.right(), footer.width() - 16)
                self.assertFalse(panel.source.geometry().intersects(panel.install_button.geometry()))
                self.assertFalse(panel.enable.geometry().intersects(panel.test_button.geometry()))

    def test_connection_test_is_bounded_cancelable_and_closes_without_tool_execution(self):
        self.window.config.settings.mcp_servers = [{'name': 'GitHub', 'library_id': 'github', 'enabled': False}]
        worker = SimpleNamespace(cancel=threading.Event(), failed=Mock(), status=Mock())
        worker.isRunning = lambda: False
        self.window.run_task = Mock(return_value=worker)
        panel = ExtensionBrowser(self.window)
        panel.search.setText('GitHub')
        with patch('ai_studio.mcp.MCPClient') as constructor:
            panel.test_connection()
            action, done, _ = self.window.run_task.call_args.args
            client = constructor.return_value
            client.open.side_effect = InterruptedError('stopped')
            self.assertIsNone(action(worker))
            constructor.assert_called_once_with(self.window.config.settings.mcp_servers[0], cancel=worker.cancel, timeout=20)
            client.close.assert_called_once()
            client.call.assert_not_called()
        done(None)
        self.assertIn('durduruldu', panel.status.text())
        self.assertTrue(panel.search.isEnabled())
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
