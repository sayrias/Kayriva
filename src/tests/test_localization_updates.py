"""Public-beta language and update integration, with no real network/install."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile
import time
import unittest
from unittest.mock import patch

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest
from ai_studio.config import Config
from ai_studio.i18n import tr, set_language
from ai_studio.ui.window import Window
from ai_studio.ui.integrations import ExtensionBrowser
from ai_studio.updater import ReleaseInfo, UpdateAsset, ApplyResult


class LocalizationUpdatesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / 'models').mkdir()
        shutil.copy(Path(__file__).resolve().parents[2] / 'models/catalog.json', self.root / 'models/catalog.json')
        self.config = Config(self.root)
        self.window = Window(self.config)
        self.window.timer.stop()
        self.window.usage_timer.stop()
        self.window.resize(940, 680)
        self.window.show()
        self.app.processEvents()

    def tearDown(self):
        self.window.preferences.close()
        self.window.close()
        self.app.processEvents()
        set_language('en')
        self.temp.cleanup()

    def wait_for(self, predicate):
        deadline = time.monotonic() + 4
        while not predicate() and time.monotonic() < deadline:
            QTest.qWait(15)
        self.assertTrue(predicate())

    def test_default_english_and_saved_turkish_do_not_rewrite_user_content(self):
        w = self.window
        self.assertEqual(self.config.settings.language, 'en')
        self.assertEqual(w.page_title.text(), 'New chat')
        self.assertEqual(w.preference_nav.item(5).text(), 'About')
        self.assertIn('Hello', w.welcome_title.text())
        draft = 'Merhaba, proje adı: Yeni sohbet / Hello'
        w.input.setPlainText(draft)
        w.settings_fields['language'].setCurrentIndex(w.settings_fields['language'].findData('tr'))
        w.save_settings()
        self.assertEqual(w.input.toPlainText(), draft)
        self.assertEqual(w.page_title.text(), 'New chat')  # restart applies language
        self.assertEqual(Config(self.root).settings.language, 'tr')
        self.assertIn('next time', w.status_label.text())
        w.input.clear()
        w.close()
        self.window = Window(Config(self.root))
        self.window.timer.stop(); self.window.usage_timer.stop()
        self.assertEqual(self.window.page_title.text(), 'Yeni sohbet')
        self.assertEqual(self.window.preference_nav.item(5).text(), 'Hakkında')
        self.assertEqual(tr(draft), draft)

    def test_english_catalog_and_extension_filters_keep_raw_identity(self):
        w = self.window
        w.open_preferences(2)
        self.assertEqual(w.model_task.itemText(w.model_task.findData('code')), 'Coding')
        note = w.model_catalog()[0]['note']
        self.assertNotEqual(tr(note), note)
        panel = ExtensionBrowser(w)
        index = panel.category.findData('Belgeler')
        self.assertIn(panel.category.itemText(index), {'Documents', 'Documentation'})
        panel.category.setCurrentIndex(index)
        self.assertEqual(panel.list.count(), 1)
        self.assertIn('Converts PDF', panel.description.text())
        self.assertEqual(panel.selected_entry['id'], 'markitdown')
        panel.deleteLater()

    def test_source_startup_and_offline_checks_do_not_contact_github(self):
        about = self.window.about_page
        with patch('ai_studio.ui.about.check_for_updates') as check:
            about.startup_check()
            self.assertFalse(check.called)
            about.packaged = True
            self.config.settings.offline = True
            about.startup_check(); about.check()
            self.assertFalse(check.called)
            self.assertIn('offline', about.status.text())
        self.assertTrue(self.config.settings.check_updates_on_startup)
        self.assertTrue(self.config.settings.auto_install_updates)

    def test_runtime_messages_translate_without_touching_paths_or_memory_values(self):
        from ai_studio.memory_units import memory_text, GB
        from ai_studio.ui.widgets import ActivityDetails
        self.assertEqual(memory_text(6.44 * GB), '6.44 GB')
        self.assertEqual(tr('Model belleğe yükleniyor · 4,096 token çalışma bağlamı…'),
                         'Loading model into memory · 4,096-token working context…')
        path = '/tmp/kişisel-model.GGUF'
        message = f'Model dosyası okunamadı: {path}. Dosya erişim izinlerini kontrol et.'
        self.assertEqual(tr(message), f'Could not read model file: {path}. Check file access permissions.')
        self.assertEqual(ActivityDetails.explain('Local model ready')[0], 'Model ready')
        set_language('tr')
        self.assertEqual(memory_text(6.44 * GB), '6,44 GB')
        self.assertEqual(tr(message), message)

    def test_auto_download_stages_then_explicit_restart_protects_drafts_and_jobs(self):
        w = self.window; about = w.about_page; about.packaged = True
        staged = self.root / 'verified-update'
        staged.write_bytes(b'verified fixture')
        release = ReleaseInfo('1.0.0-beta.2', 'https://github.com/sayrias/Kayriva/releases/tag/v1.0.0-beta.2',
            'Beta release notes', '2026-11-02', UpdateAsset('Kayriva',
            'https://github.com/sayrias/Kayriva/releases/download/v1.0.0-beta.2/Kayriva',
            staged.stat().st_size, hashlib.sha256(staged.read_bytes()).hexdigest(), 'linux', 'x86_64', 'portable'), True)
        with patch('ai_studio.ui.about.check_for_updates', return_value=release) as check, \
             patch('ai_studio.ui.about.download_update', return_value=staged) as download, \
             patch('ai_studio.ui.about.launch_update', return_value=ApplyResult(True, 'Restarting')) as launch:
            about.check()
            self.wait_for(lambda: about.staged is not None and not about.busy() and not w.background)
            check.assert_called_once(); download.assert_called_once(); launch.assert_not_called()
            self.assertEqual(about.apply_button.text(), 'Restart to update')
            w.input.setPlainText('Unsent draft')
            about.apply(); launch.assert_not_called()
            self.assertIn('draft', about.status.text())
            w.input.clear()
            with patch.object(w, 'is_busy', return_value=True):
                about.apply(); launch.assert_not_called()
                self.assertIn('active task', about.status.text())
            w.attachments = [{'name': 'not-sent.txt'}]
            about.apply(); launch.assert_not_called()
            w.attachments.clear()
            with patch.object(w, 'close') as close:
                about.apply(); launch.assert_called_once_with(release, staged); close.assert_called_once()

    def test_manual_404_stays_inline_and_stale_release_details_are_cleared(self):
        from ai_studio.updater import UpdateError
        about = self.window.about_page
        with patch('ai_studio.ui.about.check_for_updates', side_effect=UpdateError('The update repository or release has not been published yet.')), \
             patch.object(self.window, 'error') as popup:
            about.check()
            self.wait_for(lambda: not about.busy() and not self.window.background)
            self.assertIn('not been published', about.status.text())
            popup.assert_not_called()
        about.notes.show(); about.release_button.show(); about.staged = self.root / 'old'
        about.checked(None)
        self.assertIsNone(about.staged)
        self.assertTrue(about.notes.isHidden())
        self.assertTrue(about.release_button.isHidden())
