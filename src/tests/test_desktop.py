import json
import os
import shutil
import struct
import tempfile
import time
import unittest
from unittest.mock import patch
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtWidgets import QApplication, QComboBox, QPushButton
from PySide6.QtCore import Qt, QTimer
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QDialog, QLineEdit
from ai_studio.config import Config
from ai_studio.ui.window import Window


class FakeEngine:
    def stream(self, messages, tools, cancel, emit, status=lambda _: None):
        emit("Yerel ")
        emit("yanıt.")
        return {"role": "assistant", "content": "Yerel yanıt."}

    def stop(self):
        pass


class DesktopTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        (root / "models").mkdir()
        shutil.copy(Path(__file__).resolve().parents[2] / "models/catalog.json", root / "models/catalog.json")
        self.config = Config(root)
        self.config.settings.language = "tr"
        self.window = Window(self.config)
        self.window.show()
        self.window.timer.stop()
        self.window.usage_timer.stop()
        self.app.processEvents()

    def tearDown(self):
        self.window.preferences.close()
        self.window.composer_menu.hide()
        self.window.model_popup.hide()
        self.window.close()
        self.app.processEvents()
        self.temp.cleanup()

    def wait_worker(self, worker):
        deadline = time.monotonic() + 5
        while worker.isRunning() and time.monotonic() < deadline:
            self.app.processEvents()
            time.sleep(.01)
        self.app.processEvents()
        self.assertFalse(worker.isRunning())

    def test_search_in_project_messages_and_pin_order(self):
        window=self.window
        project=window.history.add_project('Deneme',self.temp.name)
        chat=window.history.create('Proje sohbeti',project)
        window.history.append(chat,[{'role':'assistant','content':'Bellek kullanımını iyileştir.'}])
        first=window.history.create('Birinci')
        window.history.create('İkinci')
        window.pin_chat(first)
        self.assertEqual(window.chat_list.item(0).data(Qt.ItemDataRole.UserRole),first)
        window.chat_search.setText('iyileştir')
        window.refresh_chats()
        self.assertEqual(window.chat_list.count(),0)
        self.assertEqual(window.project_tree.topLevelItem(0).childCount(),1)
        self.assertTrue(window.project_tree.topLevelItem(0).isExpanded())
        window.chat_search.setText('hiç yok')
        window.refresh_chats()
        self.assertTrue(window.search_empty.isVisible())
        self.assertTrue(window.project_tree.topLevelItem(0).isHidden())
        window.chat_search.clear()
        window.refresh_chats()
        self.assertFalse(window.search_empty.isVisible())

    def test_prompt_library_search_insert_preserves_draft(self):
        from ai_studio.ui.widgets import InlineDialog
        from PySide6.QtWidgets import QListWidget
        window=self.window
        window.input.setPlainText('Taslağım')
        window.history.save_prompt('Özel istem','Özel talimat')
        def choose():
            dialog=next(d for d in window.centralWidget().findChildren(InlineDialog) if d.isVisible())
            search=dialog.findChild(QLineEdit)
            search.setText('Özel istem')
            listing=dialog.findChild(QListWidget,'promptList')
            self.assertEqual(listing.count(),1)
            use=next(b for b in dialog.findChildren(QPushButton) if b.text()=='Sohbete ekle')
            use.click()
        QTimer.singleShot(40,choose)
        window.open_prompt_library()
        self.assertEqual(window.input.toPlainText(),'Taslağım\n\nÖzel talimat')
        self.assertFalse(window.prompt_library_open)
        self.assertTrue(all(s.isEnabled() for s in window.preferences.surfaces))

    def test_resident_model_budget_stays_stable_when_free_memory_falls(self):
        from unittest.mock import Mock
        from ai_studio.engine.memory import MemoryPlan
        from ai_studio.memory_units import GIB
        w=self.window;s=w.config.settings
        model=w.config.root/'models'/'test.gguf';model.write_bytes(b'GGUFtest')
        binary=w.config.root/'binary';binary.write_text('test')
        s.model_path=str(model);s.binary_path=str(binary)
        w.engine.process=Mock();w.engine.process.poll.return_value=None
        w.engine.memory_plan=MemoryPlan(20,3,3,10,4,4096,True)
        w.engine.signature=(str(model),str(binary),s.context,s.threads,s.acceleration,s.gpu_layers,s.kv_cache,s.ram_budget_gb,s.vram_budget_gb)
        w.apply_resources({'ram_total':16,'ram_used':13,'vram_total':6,'vram_used':5.8})
        self.assertEqual(w.settings_fields['vram_budget_gb'].auto_bytes(),4*GIB)
        self.assertEqual(w.settings_fields['ram_budget_gb'].auto_bytes(),10*GIB)
        self.assertIn('Model bellekte',w.settings_fields['vram_budget_gb'].details.text())
        self.assertNotIn('sığmıyor',w.memory_hint.text())
        w.apply_resources({'ram_total':16,'ram_used':14,'vram_total':6,'vram_used':5.9})
        self.assertEqual(w.settings_fields['vram_budget_gb'].auto_bytes(),4*GIB)
        w.engine.stop();w.refresh_memory_sliders()
        self.assertEqual(w.settings_fields['vram_budget_gb'].auto_bytes(),0)

    def test_research_source_button_survives_history_and_opens_source_list(self):
        from ai_studio.ui.widgets import InlineDialog
        from PySide6.QtWidgets import QListWidget
        w=self.window
        metadata={'state':'complete','sources':[{'title':'Python belgeleri','url':'https://docs.python.org/3/','snippet':'Python dili','read':True}]}
        chat=w.history.create('Araştırma')
        w.history.append(chat,[{'role':'assistant','content':'Araştırma sonucu','_studio':metadata}])
        w.refresh_chats();w.select_chat(w.chat_list.item(0))
        QTest.qWait(50)
        message=w.message_layout.itemAt(1).widget()
        self.assertTrue(message.sources_button.isVisible())
        def close():
            dialog=next(d for d in w.centralWidget().findChildren(InlineDialog) if d.isVisible())
            self.assertEqual(dialog.findChild(QListWidget).count(),1)
            dialog.reject()
        QTimer.singleShot(30,close);message.sources_requested.emit(metadata['sources'])

    def test_modal_controls_and_project_organization(self):
        window = self.window
        self.assertEqual(window.pages.count(), 2)
        self.assertFalse(hasattr(window, "nav"))
        window.open_preferences(3)
        self.assertTrue(window.preferences.isVisible())
        self.assertFalse(window.preferences.isWindow())
        self.assertEqual(window.preference_nav.count(), 6)
        self.assertFalse(window.pages.isEnabled())
        self.assertEqual(window.preferences.geometry(), window.centralWidget().rect())
        self.assertEqual(window.preference_tabs.currentIndex(), 2)
        window.resize(1000, 700)
        self.app.processEvents()
        self.assertEqual(window.preferences.geometry(), window.centralWidget().rect())
        QTest.keyClick(window.preference_nav, Qt.Key.Key_Escape)
        self.assertFalse(window.preferences.isVisible())
        self.assertTrue(window.pages.isEnabled())
        uid = window.history.add_project("Project", str(self.config.root))
        chat = window.history.create("Project chat", uid)
        window.refresh_chats()
        self.assertEqual(window.project_tree.topLevelItemCount(), 1)
        self.assertEqual(window.project_tree.topLevelItem(0).childCount(), 1)
        self.assertEqual(window.chat_list.count(), 0)

    def test_animation_stops_after_message_and_restarts_for_new_chat(self):
        window = self.window
        self.assertTrue(window.welcome.timer.isActive())
        window.add_message("user", "message")
        self.assertFalse(window.welcome.timer.isActive())
        window.new_chat()
        self.app.processEvents()
        self.assertTrue(window.welcome.timer.isActive())

    def test_sidebar_selection_survives_refresh_without_selecting_two_chats(self):
        w=self.window
        project=w.history.add_project('Notes',self.temp.name)
        project_chat=w.history.create('Project conversation',project)
        recent=w.history.create('Recent conversation')
        w.refresh_chats()
        child=w.project_tree.topLevelItem(0).child(0)
        w.select_project_item(child,0)
        w.refresh_chats()
        self.assertEqual(w.current,project_chat)
        self.assertEqual(len(w.project_tree.selectedItems()),1)
        self.assertFalse(w.chat_list.selectedItems())
        self.assertEqual(w.project_tree.selectedItems()[0].data(0,Qt.ItemDataRole.UserRole),('chat',project_chat))
        w.select_chat(w.chat_list.item(0))
        self.assertEqual(w.current,recent)
        self.assertFalse(w.project_tree.selectedItems())
        self.assertEqual(len(w.chat_list.selectedItems()),1)
        w.new_chat()
        self.assertFalse(w.chat_list.selectedItems())
        self.assertFalse(w.project_tree.selectedItems())

    def test_compact_sidebar_actions_and_native_dropdown_keyboard(self):
        w=self.window
        w.resize(940,680)
        self.app.processEvents()
        self.assertTrue(all(action.isVisible() for action in w.project_header.actions))
        self.assertLessEqual(w.welcome.minimumSizeHint().height(),w.chat_scroll.viewport().height())
        combo=w.settings_fields['acceleration']
        w.open_preferences(6)
        combo.setCurrentIndex(0)
        combo.setFocus()
        QTest.keyClick(combo,Qt.Key.Key_Down)
        self.assertEqual(combo.currentIndex(),1)
        self.assertFalse(combo.isEditable())
        self.assertEqual(w.width(),940)

    def test_popup_contains_web_and_tools_controls(self):
        window = self.window
        self.assertTrue(window.composer_menu.isAncestorOf(window.search_mode))
        self.assertTrue(window.composer_menu.isAncestorOf(window.use_tools))
        window.open_composer_menu()
        self.assertTrue(window.composer_menu.isVisible())
        self.assertLess(window.composer_menu.y(), window.plus_button.mapToGlobal(window.plus_button.rect().topLeft()).y())
        window.search_mode.setCurrentIndex(2)
        self.assertEqual(window.mode_hint.text(), "Detaylı araştırma")

    def test_streamed_chat_persists_under_selected_project(self):
        window = self.window
        model = self.config.root / "models/test.gguf"
        model.write_bytes(b"GGUFtest")
        self.config.settings.model_path = str(model)
        window.engine = FakeEngine()
        project = window.history.add_project("Code", str(self.config.root))
        window.new_project_chat(project)
        window.input.setPlainText("Merhaba")
        window.use_tools.setChecked(False)
        window.send()
        self.wait_worker(window.worker)
        messages = window.history.messages(window.current)
        self.assertEqual([m["role"] for m in messages], ["user", "assistant"])
        self.assertEqual(messages[-1]["content"], "Yerel yanıt.")
        self.assertEqual(window.history.project_for(window.current), project)
        self.assertTrue(window.send_button.isEnabled())

    def test_delegated_local_model_task_result_saved(self):
        window = self.window
        window.engine = FakeEngine()
        uid = window.jobs.create("Analyze this", kind="model")
        window.tick_jobs()
        self.wait_worker(window.job_worker)
        job = window.jobs.get(uid)
        self.assertEqual(job["state"], "complete")
        self.assertEqual(job["result"], "Yerel yanıt.")

    def test_model_library_and_memory_preset(self):
        window = self.window
        window.model_filter.setCurrentIndex(window.model_filter.findData("installed"))
        self.assertEqual(window.model_layout.itemAt(0).widget().text(), "Bu filtreye uygun model bulunamadı.")
        window.memory_preset()
        self.assertEqual(window.settings_fields["acceleration"].currentData(), "hybrid")
        self.assertEqual(window.settings_fields["context"].currentData(), 2048)
        self.assertEqual(self.config.settings.acceleration, "hybrid")
        # Switching back from the optional engine must also replace its adapter.
        self.config.settings.backend = "transformers"
        window.engine = FakeEngine()
        model = json.loads((self.config.root / "models/catalog.json").read_text())[0]
        window.select_model(model)
        from ai_studio.engine.local import LocalEngine
        self.assertIsInstance(window.engine, LocalEngine)
        self.assertEqual(self.config.settings.backend, "gguf")

    def test_settings_bounds_follow_cpu_and_selected_model(self):
        path = self.config.root / 'models/metadata.gguf'
        entries = [('qwen3.block_count', 28), ('qwen3.context_length', 8192)]
        data = b'GGUF' + struct.pack('<IQQ', 3, 0, len(entries))
        for key, value in entries:
            raw = key.encode()
            data += struct.pack('<Q', len(raw)) + raw + struct.pack('<II', 4, value)
        path.write_bytes(data)
        self.config.settings.model_path = str(path)
        with patch('ai_studio.ui.window.cpu_limit', return_value=12):
            self.window.refresh_hardware_choices()
            threads = self.window.settings_fields['threads']
            self.assertFalse(threads.isEditable())
            self.assertEqual(threads.itemData(threads.count()-1), 12)
            self.assertEqual(threads.findData(24), -1)
        layers = self.window.settings_fields['gpu_layers']
        self.assertEqual(layers.itemData(layers.count()-1), 28)
        context = self.window.settings_fields['context']
        self.assertEqual(context.itemData(context.count()-1), 8192)
        context.setCurrentIndex(context.findData(512))
        reply = self.window.settings_fields['max_tokens']
        self.assertTrue(all(reply.itemData(i) < 512 for i in range(reply.count())))
        self.config.settings.hardware_vram_gb = 6
        self.window.memory_preset()
        self.assertEqual(layers.currentData(), -1)
        self.assertEqual(self.window.settings_fields['acceleration'].currentData(), 'hybrid')

    def test_team_profile_applies_to_delegated_jobs_only(self):
        window = self.window
        window.team_name.setText('Editör')
        window.team_role.setText('Metin incele')
        window.team_instructions.setPlainText('Yazım hatalarını açıklayarak düzelt.')
        window.save_team_profile()
        normal_prompt = self.config.settings.system_prompt
        window.engine = FakeEngine()
        window.job_kind.setCurrentIndex(window.job_kind.findData('model'))
        window.job_prompt.setText('Metni incele')
        window.create_job()
        window.tick_jobs()
        self.wait_worker(window.job_worker)
        self.assertIn('Metin incele', window.job_worker.config.settings.system_prompt)
        self.assertIn('Yazım hatalarını', window.job_worker.config.settings.system_prompt)
        self.assertEqual(self.config.settings.system_prompt, normal_prompt)
        self.assertEqual(window.jobs.recent()[0]['kind'], 'model')
        restored = Config(self.config.root)
        self.assertEqual(restored.settings.team_name, 'Editör')


    def test_connection_edit_preserves_imported_http_options(self):
        spec = {'name': 'Local', 'transport': 'http', 'url': 'http://127.0.0.1:8000/mcp', 'headers': {'X-Example': 'value'}, 'enabled': True}
        self.config.settings.mcp_servers = [spec]
        with patch.object(QDialog, 'exec', return_value=QDialog.DialogCode.Accepted):
            self.window.add_mcp(0)
        self.assertEqual(self.config.settings.mcp_servers, [spec])
        self.assertFalse(self.window.mcp_output.isVisible())


    def test_unlimited_reply_selection_saves_and_worker_records_live_usage(self):
        window=self.window
        field=window.settings_fields['max_tokens']
        self.assertNotEqual(field.findData(-1),-1)
        field.setCurrentIndex(field.findData(-1))
        window.save_settings()
        self.assertEqual(self.config.settings.max_tokens,-1)
        model=self.config.root/'models/test.gguf'; model.write_bytes(b'GGUFtest')
        self.config.settings.model_path=str(model)
        window.engine=FakeEngine(); window.input.setPlainText('Merhaba'); window.use_tools.setChecked(False)
        window.send(); self.wait_worker(window.worker)
        self.assertFalse(window.live_event['active'])
        self.assertGreater(window.usage.report('day')[0]['output'],0)
        self.assertNotIn('_usage',window.history.messages(window.current)[-1])

    def test_plan_mode_never_connects_tools_or_searches(self):
        from ai_studio.ui.workers import ChatWorker
        self.config.settings.plan_mode=True
        self.config.settings.mcp_servers=[{'name':'Test','enabled':True,'command':'never-run'}]
        self.config.settings.workspace=str(self.config.root)
        engine=FakeEngine(); seen=[]
        def stream(messages,tools,cancel,emit,status=lambda _:None):
            seen.append((messages,tools)); return {'role':'assistant','content':'Plan hazır.'}
        engine.stream=stream
        worker=ChatWorker(self.config,engine,[{'role':'user','content':'Planla'}],'deep',True)
        with patch('ai_studio.ui.workers.MCPClient',side_effect=AssertionError('No MCP in plan mode')),patch('ai_studio.ui.workers.Research',side_effect=AssertionError('No web in plan mode')):
            worker.start(); self.wait_worker(worker)
        self.assertEqual(seen[0][1],[])
        self.assertIn('Plan modu',seen[0][0][0]['content'])

    def test_delegated_research_does_not_wait_for_unconnected_approval(self):
        from ai_studio.ui.workers import ChatWorker
        worker=ChatWorker(self.config,FakeEngine(),[{'role':'user','content':'Araştır'}],'quick',False)
        worker.usage_source='task'
        with patch.object(worker,'approval',side_effect=AssertionError('Task research is already authorized')),patch('ai_studio.ui.workers.Research') as research:
            research.return_value.run.return_value=[]
            research.context.return_value=''
            worker.start(); self.wait_worker(worker)
            research.return_value.run.assert_called_once()

    def test_hardware_dialog_is_embedded_and_escape_leaves_settings_open(self):
        window=self.window; window.open_preferences(2)
        def dismiss():
            dialog=window.hardware_dialog
            self.assertFalse(dialog.isWindow())
            self.assertFalse(window.preferences.panel.isEnabled())
            field=dialog.findChild(QComboBox); field.setFocus()
            QTest.keyClick(field,Qt.Key.Key_Escape)
        QTimer.singleShot(0,dismiss)
        window.edit_model_hardware()
        self.assertTrue(window.preferences.isVisible())
        self.assertTrue(window.preferences.panel.isEnabled())

    def test_live_usage_counters_resources_and_history_views(self):
        window=self.window
        event={'model':'Local','input':100,'output':20,'exact':True,'seconds':2,'active':True}
        window.record_live_usage(event)
        self.assertEqual(window.live_metrics['output'].text(),'20')
        self.assertEqual(window.live_quality.text(),'Ölçülen')
        window.live_sample=(time.monotonic()-1,10)
        window.tick_live_usage()
        self.assertGreater(window.live_chart.points[-1],0)
        window.record_live_usage({**event,'active':False,'state':'complete'})
        self.assertEqual(window.live_title.text(),'Son yanıt')
        self.assertEqual(window.usage.report('day')[0]['requests'],0)
        window.record_usage({**event,'state':'complete'})
        window.set_usage_period('day')
        self.assertEqual(window.usage_views.currentIndex(),1)
        self.assertEqual(window.usage_metrics['total'].text(),'120')
        window.resource_previous={'cpu_total':100,'cpu_idle':50}
        window.apply_resources({'cpu_total':200,'cpu_idle':75,'ram_used':4,'ram_total':16})
        self.assertEqual(window.resource_bars['cpu'].value(),750)
        self.assertEqual(window.resource_values['vram'].text(),'Algılanamadı')


    def test_quantization_selector_downloads_its_selected_file(self):
        window = self.window
        panel = window.model_layout.itemAt(0).widget()
        combo = panel.findChild(QComboBox, 'quantPicker')
        self.assertGreater(combo.count(), 1)
        combo.setCurrentIndex(combo.count()-1)
        chosen = combo.currentData()
        download = next(b for b in panel.findChildren(QPushButton) if b.text() == 'İndir')
        with patch.object(window, 'download') as call:
            download.click()
            self.assertEqual(call.call_args.args[0]['filename'],chosen['filename'])

    def test_list_menu_controls_web_and_tools(self):
        window = self.window
        window.open_composer_menu()
        window.web_row.click()
        self.assertEqual(window.composer_pages.currentIndex(),1)
        window.web_options[2].click()
        self.assertEqual(window.search_mode.currentData(),'detailed')
        self.assertFalse(window.composer_menu.isVisible())
        window.tools_row.click()
        self.assertFalse(window.use_tools.isChecked())


    def test_multiple_profiles_route_saved_role_and_export_toml(self):
        import tomllib
        window=self.window
        window.team_name.setText('Araştırmacı');window.team_role.setText('Kaynakları karşılaştır');window.save_team_profile()
        first=self.config.settings.team_selected
        window.job_prompt.setText('İlk görev');window.create_job()
        window.add_team_profile();second=self.config.settings.team_selected
        self.assertNotEqual(first,second)
        window.team_name.setText('Editör');window.team_role.setText('Yazımı düzelt')
        window.team_client.setCurrentIndex(window.team_client.findData('toml'))
        window.copy_bridge()
        spec=tomllib.loads(QApplication.clipboard().text())['mcp_servers']['ai-studio-'+second]
        self.assertEqual(spec['args'][-2:],['--profile',second])
        self.assertEqual(spec['env']['PYTHONPATH'],str(self.config.root/'src'))
        self.assertEqual(window.selected_team_profile()['client'], 'toml')
        window.load_team_profile()
        self.assertEqual(window.team_client.currentData(), 'toml')
        window.team_client.setCurrentIndex(window.team_client.findData('json'))
        window.copy_bridge()
        spec=json.loads(QApplication.clipboard().text())['mcpServers']['ai-studio-'+second]
        self.assertEqual(spec['args'][-2:],['--profile',second])
        self.assertEqual(window.selected_team_profile()['client'], 'json')
        self.assertEqual(window.job_list.item(0).text(),'Görev yok')
        engine=FakeEngine();engine.config=self.config;window.engine=engine
        window.tick_jobs();self.wait_worker(window.job_worker)
        self.assertIn('Kaynakları karşılaştır',window.job_worker.config.settings.system_prompt)
        self.assertNotIn('Yazımı düzelt',window.job_worker.config.settings.system_prompt)
        self.assertIs(engine.config,self.config)
        self.assertEqual(len(Config(self.config.root).settings.team_profiles),2)

    def test_missing_engine_preserves_message_and_opens_general(self):
        model=self.config.root/'models/test.gguf';model.write_bytes(b'GGUFtest')
        self.config.settings.model_path=str(model)
        with patch('ai_studio.engine.install.shutil.which',return_value=None):
            self.window.input.setPlainText('Merhaba');self.window.send()
        self.assertIsNone(self.window.current)
        self.assertEqual(self.window.input.toPlainText(),'Merhaba')
        self.assertIsNone(self.window.worker)
        self.assertTrue(self.window.preferences.isVisible())
        self.assertEqual(self.window.preference_tabs.currentIndex(),0)
        self.assertEqual(self.window.engine_picker.itemData(self.window.engine_picker.count()-1),'__file__')

    def test_message_bubble_fits_text_and_copy_fades_on_hover(self):
        from PySide6.QtCore import QEvent
        window=self.window;window.resize(1920,1000)
        user=window.add_message('user','merhaba')
        reply=window.add_message('assistant','Merhaba! Sana nasıl yardımcı olabilirim?')
        QTest.qWait(100)
        self.assertLess(user.height(),90);self.assertLess(user.width(),220)
        self.assertLess(reply.height(),120)
        self.assertGreaterEqual(user.view.viewport().height(),int(user.view.document().size().height()))
        self.assertEqual(user.copy_opacity.opacity(),0)
        QApplication.sendEvent(user,QEvent(QEvent.Type.Enter));QTest.qWait(200)
        self.assertAlmostEqual(user.copy_opacity.opacity(),1,places=2)
        user.copy_button.click();self.assertEqual(QApplication.clipboard().text(),'merhaba')
        QApplication.sendEvent(user,QEvent(QEvent.Type.Leave));QTest.qWait(200)
        self.assertAlmostEqual(user.copy_opacity.opacity(),0,places=2)

    def test_chat_error_status_is_not_overwritten_as_success(self):
        self.window.chat_error('Motor hatası');self.window.chat_finished()
        self.assertEqual(self.window.status_label.text(),'Motor hatası')

    def test_wrapped_user_bubble_does_not_clip_after_layout_changes(self):
        self.window.resize(1280,880)
        user=self.window.add_message('user','Merhaba, bugün birlikte bir proje geliştirelim.')
        self.window.add_message('assistant','Bu önceki yanıt.')
        QTest.qWait(100)
        self.assertGreaterEqual(user.view.viewport().height(),int(user.view.document().size().height()))
        self.assertGreater(user.view.document().size().height(),26)
        self.window.resize(920,700);QTest.qWait(100)
        self.assertGreaterEqual(user.view.viewport().height(),int(user.view.document().size().height()))


    def test_unlimited_context_and_output_choices_save_independently(self):
        window=self.window
        path=self.config.root/'models/context.gguf'
        entries=[('qwen3.block_count',28),('qwen3.context_length',8192)]
        data=b'GGUF'+struct.pack('<IQQ',3,0,len(entries))
        for key,value in entries:
            raw=key.encode();data+=struct.pack('<Q',len(raw))+raw+struct.pack('<II',4,value)
        path.write_bytes(data);self.config.settings.model_path=str(path)
        window.sync_settings()
        context=window.settings_fields['context'];reply=window.settings_fields['max_tokens']
        context.setCurrentIndex(context.findData(0));reply.setCurrentIndex(reply.findData(-1))
        window.save_settings()
        self.assertEqual(self.config.settings.context,0);self.assertEqual(self.config.settings.max_tokens,-1)
        self.assertEqual(window.settings_fields['acceleration'].currentData(),'hybrid')
        self.assertEqual(self.config.settings.ram_budget_gb,0)
        self.assertEqual(self.config.settings.vram_budget_gb,0)

    def test_delete_confirmation_is_inline_and_cancel_keeps_history(self):
        from ai_studio.ui.widgets import InlineDialog
        window=self.window
        uid=window.history.create('A chat');window.current=uid
        window.history.append(uid,[{'role':'user','content':'Keep me'}])
        checked=[]
        def cancel():
            dialog=window.findChild(InlineDialog,'deleteChatOverlay')
            checked.append(not dialog.isWindow() and dialog.isVisible())
            checked.append(not window.pages.isEnabled())
            QTest.keyClick(dialog,Qt.Key.Key_Escape)
        QTimer.singleShot(0,cancel)
        window.delete_chat()
        self.assertEqual(checked,[True,True])
        self.assertEqual(len(window.history.messages(uid)),1)
        self.assertTrue(window.pages.isEnabled())
        self.app.processEvents()
        other=window.history.create('Keep other chat')
        def accept():
            dialog=window.findChild(InlineDialog,'deleteChatOverlay')
            dialog.findChild(QPushButton,'destructiveButton').click()
        QTimer.singleShot(0,accept)
        window.confirm_delete_chat(uid,'A chat')
        self.assertEqual(window.history.messages(uid),[])
        self.assertIn(other,[row[0] for row in window.history.chats()])

    def test_memory_preset_restores_automatic_model_budgets(self):
        window=self.window
        window.refresh_hardware_choices()
        for name,value in [('ram_budget_gb',12.),('vram_budget_gb',4.)]:
            combo=window.settings_fields[name]
            combo.setValue(value)
        window.memory_preset()
        self.assertEqual(window.settings_fields['ram_budget_gb'].currentData(),0.)
        self.assertEqual(window.settings_fields['vram_budget_gb'].currentData(),0.)

    def test_reply_setting_changes_do_not_unload_warm_engine(self):
        from unittest.mock import Mock
        window=self.window
        window.engine.stop=Mock()
        field=window.settings_fields['temperature']
        field.setCurrentIndex(field.findData(.8))
        window.save_settings()
        window.engine.stop.assert_not_called()
        self.assertEqual(self.config.settings.temperature,.8)

    def test_model_memory_sliders_save_decimal_caps_and_follow_hardware(self):
        from ai_studio.hardware import Hardware
        from ai_studio.memory_units import GIB
        from ai_studio.ui.widgets import MemorySlider
        window=self.window
        with patch('ai_studio.ui.window.detect',return_value=Hardware(12,16,6,'GPU',16*GIB,6*GIB)):
            window.refresh_hardware_choices()
        ram=window.settings_fields['ram_budget_gb'];gpu=window.settings_fields['vram_budget_gb']
        self.assertIsInstance(ram,MemorySlider)
        self.assertTrue(ram.automatic.isChecked())
        self.assertEqual(gpu.total_bytes,6*GIB)
        ram.slider.setValue(120);gpu.slider.setValue(50)
        self.assertFalse(ram.automatic.isChecked());self.assertFalse(gpu.automatic.isChecked())
        self.assertIn('12,00 GB',ram.amount.text())
        self.assertIn('5,00 GB',gpu.amount.text())
        window.save_settings()
        self.assertAlmostEqual(self.config.settings.ram_budget_gb,12_000_000_000/GIB)
        self.assertAlmostEqual(self.config.settings.vram_budget_gb,5_000_000_000/GIB)
        saved=Config(self.config.root)
        self.assertEqual(saved.settings.ram_budget_gb,self.config.settings.ram_budget_gb)
        self.assertEqual(saved.settings.vram_budget_gb,self.config.settings.vram_budget_gb)

    def test_slider_live_free_memory_does_not_change_manual_budget(self):
        from ai_studio.memory_units import GIB
        window=self.window
        window.apply_resources({'ram_total':16,'ram_used':4,'vram_total':6,'vram_used':967/1024})
        gpu=window.settings_fields['vram_budget_gb']
        self.assertIn('Toplam 6,44 GB',gpu.details.text())
        self.assertIn('Boş 5,43 GB',gpu.details.text())
        gpu.slider.setValue(50);manual=gpu.value()
        window.apply_resources({'ram_total':16,'ram_used':8,'vram_total':6,'vram_used':3})
        self.assertEqual(gpu.value(),manual)
        self.assertIn('şu anki boş alanı aşıyor',gpu.details.text())
        gpu.slider.setValue(gpu.slider.maximum())
        self.assertEqual(gpu.value(),6)
        gpu.automatic.setChecked(True)
        self.assertEqual(gpu.value(),0)

    def test_unknown_vram_does_not_invent_capacity_or_lose_saved_limit(self):
        from ai_studio.ui.widgets import MemorySlider
        slider=MemorySlider('vram');slider.setValue(5)
        self.assertFalse(slider.slider.isEnabled())
        self.assertEqual(slider.value(),5)
        self.assertIn('algılanamadı',slider.details.text())
        slider.deleteLater()

    def test_multiple_replies_survive_sending_and_reopening_chat(self):
        from ai_studio.ui.widgets import Message
        window=self.window;window.engine=FakeEngine()
        path=self.config.root/'models/test.gguf';path.write_bytes(b'GGUFtest')
        self.config.settings.model_path=str(path)
        for text in ['Merhaba','Nasılsın?']:
            window.input.setPlainText(text);window.send();self.wait_worker(window.worker)
        records=window.history.messages(window.current)
        self.assertEqual([m['role'] for m in records],['user','assistant','user','assistant'])
        self.assertIn('seconds',records[-1]['_studio'])
        cards=[window.message_layout.itemAt(i).widget() for i in range(window.message_layout.count())]
        self.assertEqual(len([c for c in cards if isinstance(c,Message)]),4)
        window.select_chat(window.chat_list.item(0));self.app.processEvents()
        cards=[window.message_layout.itemAt(i).widget() for i in range(window.message_layout.count())]
        replies=[c for c in cards if isinstance(c,Message) and c.role=='assistant']
        self.assertEqual(len(replies),2)
        self.assertTrue(all(c.text=='Yerel yanıt.' and c.isVisible() for c in replies))
        self.assertTrue(all('çalıştı' in c.activity_button.text() for c in replies))

    def test_partial_failure_persists_and_metadata_is_not_sent_to_model(self):
        from ai_studio.ui.widgets import Message
        class FailingEngine:
            def stream(self,messages,tools,cancel,emit,status=lambda _:None):
                emit('Yarım yanıt');raise RuntimeError('Bağlantı kesildi')
            def stop(self):pass
        window=self.window;window.engine=FailingEngine()
        path=self.config.root/'models/test.gguf';path.write_bytes(b'GGUFtest')
        self.config.settings.model_path=str(path)
        window.input.setPlainText('Merhaba');window.send();self.wait_worker(window.worker)
        saved=window.history.messages(window.current)[-1]
        self.assertEqual(saved['content'],'Yarım yanıt')
        self.assertEqual(saved['_studio']['state'],'failed')
        window.select_chat(window.chat_list.item(0));self.app.processEvents()
        replies=[c for c in window.findChildren(Message) if c.role=='assistant' and c.isVisible()]
        self.assertTrue(any(c.text=='Yarım yanıt' and c.error_label.isVisible() for c in replies))
        received=[]
        class InspectEngine(FakeEngine):
            def stream(self,messages,tools,cancel,emit,status=lambda _:None):
                received.extend(messages)
                return super().stream(messages,tools,cancel,emit,status)
        window.engine=InspectEngine();window.input.setPlainText('Devam');window.send();self.wait_worker(window.worker)
        self.assertFalse(any('_studio' in m for m in received))
        self.assertFalse(any(m.get('content')=='Yarım yanıt' for m in received))

    def test_single_icon_button_cancels_and_keeps_partial_reply(self):
        class SlowEngine(FakeEngine):
            def stream(self,messages,tools,cancel,emit,status=lambda _:None):
                status('Yanıt hazırlanıyor');emit('Yarım yanıt')
                cancel.wait(3)
                return {'role':'assistant','content':'Yarım yanıt'}
        window=self.window;window.engine=SlowEngine()
        path=self.config.root/'models/test.gguf';path.write_bytes(b'GGUFtest')
        self.config.settings.model_path=str(path)
        window.input.setPlainText('Merhaba');window.send();QTest.qWait(50)
        self.assertFalse(hasattr(window,'stop_button'))
        self.assertEqual(window.send_button.text(),'')
        self.assertEqual(window.send_button.toolTip(),'Durdur')
        self.assertTrue(window.send_button.isEnabled())
        window.send_button.click();self.wait_worker(window.worker)
        self.assertEqual(window.send_button.toolTip(),'Gönder')
        self.assertEqual(window.history.messages(window.current)[-1]['_studio']['state'],'cancelled')

    def test_block_display_and_activity_footer(self):
        from ai_studio.ui.widgets import Message
        message=self.window.add_message('assistant','');message.begin('blocks')
        message.append('Merha');self.app.processEvents()
        self.assertEqual(message.shown_text,'')
        message.append('ba!');self.app.processEvents()
        self.assertEqual(message.shown_text,'Merhaba!')
        message.set_activity('Web sorgusu hazırlanıyor')
        self.assertIn('Web sorgusu',message.activity_button.text())
        self.assertIn('Web sorgusu',message.activity_details.toPlainText())
        message.apply_metadata({'seconds':93,'state':'complete','activities':[{'seconds':0,'text':'Model hazır'}]})
        self.assertEqual(message.activity_button.text(),'1 dk 33 sn çalıştı')
        self.assertTrue(message.footer.isVisible())
        self.assertTrue(message.footer.isAncestorOf(message.copy_button))
        message.copy();self.assertEqual(QApplication.clipboard().text(),'Merhaba!')
        self.window.follow_chat=False
        bar=self.window.chat_scroll.verticalScrollBar();bar.setValue(0)
        message.append(' Bir yanıt daha.');QTest.qWait(100)
        self.assertEqual(bar.value(),0)

    def test_complete_display_reveals_whole_reply_without_a_typewriter_queue(self):
        message=self.window.add_message('assistant','');message.begin('complete')
        reply='Merhaba!\n\n'+('Tamamlanmış yanıt hemen gösterilir. '*80)
        for char in reply:
            message.append(char)
        QTest.qWait(100)
        self.assertEqual(message.text,reply)
        self.assertEqual(message.shown_text,'')
        self.assertFalse(message.view.isVisible())
        self.assertFalse(message.pending)
        message.apply_metadata({'seconds':4,'state':'complete','activities':[]})
        self.assertEqual(message.shown_text,reply)
        self.assertTrue(message.view.isVisible())
        self.assertIn('Tamamlanmış yanıt hemen gösterilir.',message.view.toPlainText())
        self.assertFalse(message.progress_timer.isActive())

    def test_picker_fits_full_rows_and_selected_model_is_first(self):
        from ai_studio.ui.widgets import ModelOption
        catalog=json.loads((self.config.root/'models/catalog.json').read_text())
        chosen=catalog[1]
        for model in catalog[:6]:
            (self.config.root/'models'/model['filename']).write_bytes(b'GGUFtest')
        self.config.settings.model_path=str(self.config.root/'models'/chosen['filename'])
        self.window.open_model_picker();QTest.qWait(100)
        rows=[self.window.picker_items.itemAt(i).widget() for i in range(self.window.picker_items.count())]
        self.assertEqual(len(rows),6)
        self.assertTrue(all(isinstance(row,ModelOption) for row in rows))
        self.assertTrue(rows[0].property('selected'))
        self.assertEqual(rows[0].title.text(),chosen['name'])
        self.assertGreaterEqual(self.window.picker_scroll.height(),4*60)
        for row in rows:
            self.assertLessEqual(row.detail.geometry().bottom(),row.height())
        self.window.picker_search.setText(chosen['name']);QTest.qWait(60)
        self.assertGreaterEqual(self.window.picker_scroll.height(),62)
        self.window.picker_search.setText('no-such-model');QTest.qWait(60)
        self.assertIn('Eşleşen',self.window.picker_items.itemAt(0).widget().text())

    def test_activity_timeline_has_readable_explanations_and_full_width_divider(self):
        from ai_studio.ui.widgets import ActivityDetails
        from PySide6.QtWidgets import QLabel
        message=self.window.add_message('assistant','Merhaba!')
        events=[{'seconds':0,'text':'Bellek bütçesi kontrol ediliyor…'},
                {'seconds':1,'text':'Model belleğe yükleniyor · 4,096 token çalışma bağlamı…'},
                {'seconds':3,'text':'Yanıt oluşturuluyor…'}]
        message.apply_metadata({'seconds':4,'state':'complete','activities':events})
        message.toggle_activity();QTest.qWait(100)
        self.assertIsInstance(message.activity_details,ActivityDetails)
        self.assertLess(message.activity_details.height(),155)
        texts=[l.text() for l in message.activity_details.findChildren(QLabel)]
        self.assertIn('Modelin yanıt metnini üretmesi',texts)
        self.assertGreater(message.activity_divider.width(),message.activity_button.width())
        self.assertEqual(message.copy_button.objectName(),'messageAction')
        message.copy();self.assertEqual(QApplication.clipboard().text(),'Merhaba!')

    def test_public_brand_changes_without_relocating_existing_data(self):
        from ai_studio.brand import APP_NAME
        self.assertEqual(APP_NAME,'Kayriva')
        self.assertIn(APP_NAME,self.window.windowTitle())
        self.assertEqual(self.config.path,self.config.root/'runtime/settings.json')

    def test_project_list_height_tracks_visible_rows_instead_of_leaving_a_gap(self):
        window=self.window
        project=window.history.add_project('deneme',str(self.config.root))
        window.history.create('Proje sohbeti',project)
        window.history.create('Diğer sohbet')
        window.refresh_chats();QTest.qWait(100)
        self.assertLess(window.project_tree.height(),70)
        group=window.project_tree.topLevelItem(0);group.setExpanded(True);QTest.qWait(50)
        self.assertGreater(window.project_tree.height(),50)
        self.assertLess(window.project_tree.height(),100)
        self.assertFalse(window.project_tree.rootIsDecorated())

    def test_automatic_project_write_is_real_and_does_not_ask_each_time(self):
        class Writer(FakeEngine):
            calls=0
            def stream(self,messages,tools,cancel,emit,status=lambda _:None):
                self.calls+=1
                if self.calls==1:
                    assert any(t['function']['name']=='workspace_write' for t in tools)
                    return {'role':'assistant','content':'','tool_calls':[{'id':'write','type':'function','function':{'name':'workspace_write','arguments':json.dumps({'path':'notes/test.md','content':'Proje notu','mode':'create'})}}]}
                return {'role':'assistant','content':'Dosya oluşturuldu.'}
        window=self.window;window.engine=Writer()
        path=self.config.root/'models/test.gguf';path.write_bytes(b'GGUFtest')
        self.config.settings.model_path=str(path)
        self.config.settings.approval_mode='automatic'
        project=window.history.add_project('Proje',str(self.config.root));window.new_project_chat(project)
        window.input.setPlainText('notes/test.md oluştur');window.send()
        with patch.object(window,'approve_tool',side_effect=AssertionError('Automatic mode must not ask')):
            self.wait_worker(window.worker)
        self.assertEqual((self.config.root/'notes/test.md').read_text(),'Proje notu')
        self.assertEqual(window.history.messages(window.current)[-1]['content'],'Dosya oluşturuldu.')

    def test_residency_prepares_in_background_and_release_policy_stops_after_turn(self):
        from unittest.mock import Mock
        window=self.window;engine=FakeEngine();engine.ensure=Mock();engine.stop=Mock();window.engine=engine
        path=self.config.root/'models/test.gguf';path.write_bytes(b'GGUFtest');self.config.settings.model_path=str(path)
        self.config.settings.model_residency='always';window.apply_model_residency()
        self.wait_worker(window.preload_worker);engine.ensure.assert_called_once()
        self.assertEqual(window.send_button.toolTip(),'Gönder')
        self.config.settings.model_residency='lazy';window.release_model_after_turn();engine.stop.assert_not_called()
        self.config.settings.model_residency='release';window.release_model_after_turn();engine.stop.assert_called_once()

    def test_deep_research_uses_sources_without_an_extra_model_planning_call(self):
        from ai_studio.ui.workers import ChatWorker
        from unittest.mock import Mock
        engine=FakeEngine();engine.stream=Mock(wraps=engine.stream)
        worker=ChatWorker(self.config,engine,[{'role':'user','content':'Araştır'}],'deep',False)
        approvals=[];worker.approve.connect(lambda *args:approvals.append(args))
        with patch('ai_studio.ui.workers.Research') as research:
            research.return_value.run.return_value=[{'title':'Guide','url':'https://example.org/guide','snippet':'summary','text':'Actual page text'}]
            research.context.return_value='Read source material'
            worker.start();self.wait_worker(worker)
        self.assertEqual(engine.stream.call_count,1)
        self.assertEqual(approvals,[])
        self.assertIn('Read source material',engine.stream.call_args.args[0][-1]['content'])


if __name__ == "__main__":
    unittest.main()
