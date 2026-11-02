import json
import os
from pathlib import Path
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication, QLineEdit, QPushButton
from PySide6.QtTest import QTest

from ai_studio.config import Config
from ai_studio.ui.window import Window
from ai_studio.ui.widgets import ModelOption
from ai_studio.ui.model_filters import accepts, capacity_tier, capabilities


class ModelMetadataFilters(unittest.TestCase):
    def test_filters_are_metadata_and_size_limits_not_quality_scores(self):
        model = {'name': 'Qwen Model', 'brand': 'Qwen', 'capabilities': ['chat', 'code'], 'approx_gb': 4.5}
        self.assertTrue(accepts(model, maker='Qwen', capability='code', tier=1, maximum_gb=5))
        self.assertFalse(accepts(model, maker='Google'))
        self.assertFalse(accepts(model, capability='vision'))
        self.assertFalse(accepts(model, tier=0))
        self.assertFalse(accepts(model, maximum_gb=4))
        self.assertEqual(capacity_tier(model), 1)
        self.assertEqual(capabilities({'name': 'Vision-ish name'}), {'chat'})


class ModelLibraryUI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / 'models').mkdir()
        base = {'quant': 'Q4_K_M', 'note': 'Test metadata', 'category': 'standard',
                'source': 'https://example.com/model', 'license': 'Apache 2.0', 'quality': 'balanced'}
        catalog = [
            {**base, 'id': 'qwen-test', 'name': 'Qwen Test', 'brand': 'Qwen', 'filename': 'qwen.gguf',
             'repo': 'test/qwen', 'approx_gb': 1.5, 'params_b': 2, 'tier': 'low', 'capabilities': ['chat', 'code', 'tools']},
            {**base, 'id': 'google-test', 'name': 'Gemma Test', 'brand': 'Google', 'filename': 'gemma.gguf',
             'repo': 'test/gemma', 'approx_gb': 4.5, 'params_b': 4, 'tier': 'medium', 'capabilities': ['chat', 'vision'],
             'projector': {'filename': 'mmproj-gemma.gguf', 'repo': 'test/gemma', 'remote_filename': 'mmproj.gguf'}},
        ]
        (self.root / 'models/catalog.json').write_text(json.dumps(catalog))
        config = Config(self.root)
        config.settings.language = "tr"
        self.window = Window(config)
        self.window.timer.stop()
        self.window.usage_timer.stop()
        self.window.show()
        self.window.reset_model_filters()
        self.app.processEvents()

    def tearDown(self):
        self.window.preferences.close()
        self.window.model_popup.hide()
        self.window.close()
        self.app.processEvents()
        self.temp.cleanup()

    def wait_worker(self, worker):
        deadline = time.monotonic() + 4
        while worker.isRunning() and time.monotonic() < deadline:
            self.app.processEvents()
            time.sleep(.01)
        self.app.processEvents()
        self.assertFalse(worker.isRunning())

    def test_brand_task_tier_and_file_size_filters_compose_and_reset(self):
        w = self.window
        self.assertIn('2 model', w.model_count.text())
        qwen = next(i for i in range(w.model_brands.count()) if w.model_brands.itemData(i) == 'Qwen')
        w.model_brands.setCurrentIndex(qwen)
        self.assertIn('1 model', w.model_count.text())
        w.model_task.setCurrentIndex(w.model_task.findData('vision'))
        self.assertIn('0 model', w.model_count.text())
        self.assertIn('projektör', w.model_workflow_hint.text())
        w.reset_model_filters()
        w.model_tier.setValue(0)
        self.assertIn('1 model', w.model_count.text())
        w.model_size.setValue(1)
        self.assertIn('0 model', w.model_count.text())
        w.reset_model_filters()
        self.assertIn('2 model', w.model_count.text())
        self.assertEqual(w.model_size.value(), 128)

    def test_model_import_keeps_bad_path_recoverable_then_detects_uppercase_gguf(self):
        model = self.root / 'Büyük Yerel Model.GGUF'
        model.write_bytes(b'GGUFtest')
        checked = []
        def use():
            dialog = self.window.model_import_dialog
            self.assertFalse(dialog.isWindow())
            field = dialog.findChild(QLineEdit, 'modelImportPath')
            accept = next(b for b in dialog.findChildren(QPushButton) if b.text() == 'Modeli ekle')
            field.setText(str(self.root / 'missing.gguf'))
            accept.click()
            checked.append(dialog.isVisible())
            field.setText(model.as_uri())
            accept.click()
        QTimer.singleShot(30, use)
        self.window.import_model()
        self.assertEqual(checked, [True])
        self.assertEqual(self.window.config.model_path(), model)
        self.assertEqual(self.window.config.settings.backend, 'gguf')
        self.assertIn(str(model), self.window.config.settings.local_models)
        self.window.config.settings.model_path = ''
        self.window.open_model_picker()
        rows = self.window.model_popup.findChildren(ModelOption)
        self.assertTrue(any(row.title.text() == model.stem for row in rows))

    def test_refresh_checks_catalog_off_thread_without_downloading_weights(self):
        result = SimpleNamespace(available=2, checked=2, errors={})
        with patch('ai_studio.catalog_sync.refresh_catalog', return_value=result) as refresh:
            self.window.refresh_catalog_online()
            self.wait_worker(self.window.catalog_worker)
        self.assertEqual(refresh.call_args.args[1], self.root / 'runtime/catalog-cache.json')
        self.assertIn('Katalog güncel', self.window.model_count.text())
        self.assertEqual(self.window.catalog_refresh.text(), 'Kataloğu yenile')

    def test_projector_download_does_not_replace_active_chat_model(self):
        w = self.window
        model = w.model_catalog()[1]
        main = self.root / 'models' / model['filename']
        main.write_bytes(b'GGUFtest')
        w.config.settings.model_path = str(main)
        with patch.object(w, 'download') as download:
            w.download_projector(model)
        descriptor = download.call_args.args[0]
        self.assertEqual(descriptor['_projector_for'], main.name)
        projector = self.root / 'models' / descriptor['filename']
        projector.write_bytes(b'GGUFtest')
        w.download_complete(descriptor)
        self.assertEqual(w.config.model_path(), main)
        self.assertEqual(w.config.settings.mmproj_path, str(projector))

    def test_extension_and_github_actions_use_library_inside_existing_settings(self):
        w = self.window
        with patch('ai_studio.ui.integrations.show_extension_library') as library:
            w.open_extension_library()
            library.assert_called_once_with(w)
        with patch('ai_studio.ui.integrations.show_github_dialog') as github:
            w.open_github(self.root)
            github.assert_called_once_with(w, project_path=self.root)
        self.assertFalse(any(b.text() == '···' for b in w.findChildren(QPushButton)))

    def test_limited_task_is_not_presented_as_completed(self):
        message = self.window.add_message('assistant', 'Kısmi sonuç')
        message.apply_metadata({'state': 'limited', 'seconds': 30, 'activities': []})
        self.assertIn('çalışma sınırına ulaşıldı', message.activity_button.text())

    def test_document_and_image_attachments_use_named_records(self):
        from PySide6.QtGui import QImage, QColor
        document = self.root / 'note.md'
        document.write_text('Belge içeriği')
        image = self.root / 'image.png'
        picture = QImage(20, 20, QImage.Format.Format_RGB32)
        picture.fill(QColor('#aa99cc'))
        picture.save(str(image))
        with patch('ai_studio.ui.window.QFileDialog.getOpenFileNames', return_value=([str(document), str(image)], '')):
            self.window.attach()
        self.wait_worker(self.window.attachment_worker)
        self.assertEqual(self.window.attachments[0]['text'], 'Belge içeriği')
        self.assertEqual(self.window.attachments[1]['kind'], 'image')
        self.assertTrue((self.root / 'runtime/attachments' / self.window.attachments[1]['image_path']).is_file())
        self.assertIn('image.png', self.window.attachment_label.text())

    def test_attachment_preparation_can_be_cancelled_without_adding_partial_batch(self):
        document = self.root / 'large.pdf'
        document.write_bytes(b'test')
        def prepare(path, runtime, cancel=None):
            cancel.wait(3)
            raise InterruptedError('Cancelled')
        with patch('ai_studio.attachments.prepare_attachment', side_effect=prepare), \
             patch('ai_studio.ui.window.QFileDialog.getOpenFileNames', return_value=([str(document)], '')), \
             patch.object(self.window, 'error') as error:
            self.window.attach()
            self.assertTrue(self.window.is_busy())
            self.assertEqual(self.window.send_button.toolTip(), 'Durdur')
            self.window.send_button.click()
            self.wait_worker(self.window.attachment_worker)
            error.assert_not_called()
        self.assertEqual(self.window.attachments, [])
        self.assertEqual(self.window.send_button.toolTip(), 'Gönder')
        self.assertIn('durduruldu', self.window.status_label.text())

    def test_fifth_image_is_rejected_before_message_submission(self):
        image = self.root / 'photo.png'
        image.write_bytes(b'test')
        descriptor = {'name': image.name, 'kind': 'image', 'image_path': '0' * 64 + '.png', 'mime': 'image/png'}
        with patch('ai_studio.attachments.prepare_attachment', return_value=descriptor), \
             patch('ai_studio.ui.window.QFileDialog.getOpenFileNames', return_value=([str(image)] * 5, '')), \
             patch.object(self.window, 'error') as error:
            self.window.attach()
            self.wait_worker(self.window.attachment_worker)
            self.assertIn('dört görsel', error.call_args.args[0])
        self.assertEqual(len(self.window.attachments), 4)

    def test_small_window_keeps_settings_actions_and_projector_reachable(self):
        from PySide6.QtWidgets import QScrollArea
        w = self.window
        w.resize(940, 640)
        w.open_preferences(6)
        self.app.processEvents()
        self.assertEqual(w.size().height(), 640)
        projector = w.settings_fields['mmproj_path']
        scroll = next(s for s in w.preference_tabs.currentWidget().findChildren(QScrollArea) if s.isAncestorOf(projector))
        scroll.ensureWidgetVisible(projector)
        self.app.processEvents()
        self.assertTrue(scroll.viewport().rect().contains(projector.mapTo(scroll.viewport(), projector.rect().center())))
        save = next(b for b in w.preference_tabs.currentWidget().findChildren(QPushButton) if b.text() == 'Kaydet')
        self.assertTrue(w.preferences.panel.rect().contains(save.mapTo(w.preferences.panel, save.rect().center())))

    def test_github_publish_rechecks_offline_and_review_state(self):
        from ai_studio.ui.integrations import GitHubPanel
        from PySide6.QtCore import Qt
        from PySide6.QtWidgets import QListWidgetItem
        panel = GitHubPanel(self.window)
        panel.account_ready = True
        panel.name.setText('owner/test')
        panel.preview = object()
        item = QListWidgetItem('example.py')
        item.setData(Qt.ItemDataRole.UserRole, 'example.py')
        item.setCheckState(Qt.CheckState.Checked)
        panel.files.addItem(item)
        panel.confirm.setChecked(True)
        self.assertTrue(panel.publish_button.isEnabled())
        panel.private.setChecked(False)
        self.assertFalse(panel.confirm.isChecked())
        self.assertFalse(panel.publish_button.isEnabled())
        item.setCheckState(Qt.CheckState.Unchecked)
        panel.confirm.setChecked(True)
        self.assertFalse(panel.publish_button.isEnabled())
        panel.mode.setCurrentIndex(1)
        panel.confirm.setChecked(True)
        self.assertTrue(panel.publish_button.isEnabled())
        self.window.config.settings.offline = True
        with patch.object(panel.service, 'create') as create:
            panel.publish()
            create.assert_not_called()
        self.assertIn('çevrimdışı', panel.result.text())
        panel.deleteLater()

    def test_extension_cancel_is_not_reported_as_error_and_empty_search_recovers(self):
        import shutil
        from ai_studio.ui.integrations import ExtensionBrowser
        (self.root / 'extensions').mkdir()
        shutil.copy(Path(__file__).resolve().parents[2] / 'extensions/catalog.json', self.root / 'extensions/catalog.json')
        panel = ExtensionBrowser(self.window)
        panel.search.setText('no-such-extension')
        self.assertEqual(panel.list.count(), 0)
        self.assertIn('bulunamadı', panel.status.text())
        panel.search.clear()
        self.assertGreater(panel.list.count(), 0)
        self.assertNotIn('bulunamadı', panel.status.text())
        with patch.object(panel.library, 'install', side_effect=InterruptedError('Cancelled')), patch.object(self.window, 'error') as error:
            panel.install()
            self.wait_worker(panel.worker)
            error.assert_not_called()
        self.assertIn('durduruldu', panel.status.text())
        self.assertFalse(panel.cancel_button.isVisible())
        panel.deleteLater()

    def test_github_failed_task_keeps_error_visible_and_restores_controls(self):
        from ai_studio.ui.integrations import GitHubPanel
        panel = GitHubPanel(self.window)
        def fail(worker):
            raise ValueError('Yerel deneme hatası')
        with patch.object(self.window, 'error'):
            panel.task(fail, lambda _: self.fail('Must not succeed'))
            self.wait_worker(panel.worker)
        self.assertTrue(panel.refresh_button.isEnabled())
        self.assertTrue(panel.tabs.isEnabled())
        self.assertEqual(panel.result.text(), 'Yerel deneme hatası')
        panel.deleteLater()

    def test_memory_profile_and_nonpreset_task_budgets_roundtrip(self):
        w = self.window
        w.config.settings.task_rounds = 17
        w.config.settings.task_minutes = 37
        w.sync_settings()
        self.assertEqual(w.settings_fields['task_rounds'].currentData(), 17)
        self.assertEqual(w.settings_fields['task_minutes'].currentData(), 37)
        profile = w.settings_fields['memory_profile']
        profile.setCurrentIndex(profile.findData('low_memory'))
        w.save_settings()
        restored = Config(self.root).settings
        self.assertEqual(restored.memory_profile, 'low_memory')
        self.assertEqual(restored.task_rounds, 17)
        self.assertEqual(restored.task_minutes, 37)


if __name__ == '__main__':
    unittest.main()
