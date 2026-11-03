"""Real Qt interactions for paste, growing composer, timeline and file selection."""
import os
from pathlib import Path
import shutil
import tempfile
import time
import unittest
from unittest.mock import patch
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from PySide6.QtCore import Qt,QMimeData,QUrl,QTimer
from PySide6.QtGui import QImage,QColor
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication,QFileDialog as NativeDialog,QLineEdit,QFileSystemModel,QListView,QPushButton,QScrollArea
from ai_studio.config import Config
from ai_studio.ui.window import Window
from ai_studio.ui.widgets import Message,BrandPicker
from ai_studio.ui.file_dialogs import QFileDialog
from ai_studio.ui.image_viewer import ImagePreview,AttachmentImage


class ComposerActivityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        (self.root/'models').mkdir();shutil.copy(Path(__file__).resolve().parents[2]/'models/catalog.json',self.root/'models/catalog.json')
        config=Config(self.root);config.settings.language='en';config.settings.offline=True
        self.w=Window(config);self.w.timer.stop();self.w.usage_timer.stop();self.w.resize(1100,800);self.w.show();QTest.qWait(30)
    def tearDown(self):
        self.w.input.clear();self.w.attachments.clear();self.w.preferences.close();self.w.close();self.app.processEvents();self.temp.cleanup()
    def wait(self, predicate):
        deadline=time.monotonic()+5
        while not predicate() and time.monotonic()<deadline:QTest.qWait(20)
        self.app.processEvents()
        self.assertTrue(predicate())

    def test_long_text_grows_then_scrolls_and_clearing_shrinks(self):
        field=self.w.input;minimum=field.height()
        field.setPlainText('one\ntwo\nthree\nfour\nfive\nsix');QTest.qWait(60)
        self.assertGreater(field.height(),minimum)
        field.setPlainText('A long paragraph with wrapping words. '*900);QTest.qWait(80)
        self.assertLessEqual(field.height(),440)
        self.assertGreater(field.verticalScrollBar().maximum(),0)
        field.clear();QTest.qWait(40);self.assertEqual(field.height(),minimum)

    def test_paste_image_previews_and_can_be_removed_without_changing_draft(self):
        self.w.input.setPlainText('Inspect the layout')
        image=QImage(80,60,QImage.Format.Format_RGB32);image.fill(QColor('#aabbee'))
        mime=QMimeData();mime.setImageData(image)
        self.w.input.insertFromMimeData(mime)
        self.wait(lambda:self.w.attachment_worker and not self.w.attachment_worker.isRunning())
        self.assertEqual(self.w.input.toPlainText(),'Inspect the layout')
        self.assertEqual(len(self.w.attachments),1)
        self.assertTrue(self.w.attachment_strip.isVisible())
        self.assertTrue((self.w.config.runtime/'attachments'/self.w.attachments[0]['image_path']).is_file())
        self.w.remove_attachment(self.w.attachments[0]);self.assertFalse(self.w.attachment_strip.isVisible())

    def test_long_draft_with_attachment_does_not_overlap_composer_controls(self):
        self.w.resize(940,640)
        self.w.attachments.append({'name':'notes.txt','text':'Example'})
        self.w.refresh_attachment_previews()
        self.w.input.setPlainText('A long draft with wrapping words. '*900)
        QTest.qWait(120)
        field=self.w.input
        self.assertLess(field.geometry().bottom(),self.w.send_button.geometry().top())
        self.assertLess(self.w.send_button.geometry().bottom(),self.w.composer.height())
        self.assertLess(self.w.attachment_strip.geometry().bottom(),field.geometry().top())
        self.assertGreater(field.verticalScrollBar().maximum(),0)
        bottom=self.w.send_button.mapTo(self.w,self.w.send_button.rect().bottomRight()).y()
        self.assertLess(bottom,self.w.status_label.mapTo(self.w,self.w.status_label.rect().topLeft()).y())

    def test_file_urls_paste_as_attachments_plain_text_stays_text(self):
        path=self.root/'example.md';path.write_text('# Example')
        mime=QMimeData();mime.setUrls([QUrl.fromLocalFile(str(path))]);self.w.input.insertFromMimeData(mime)
        self.wait(lambda:self.w.attachment_worker and not self.w.attachment_worker.isRunning())
        self.assertEqual(self.w.attachments[0]['name'],'example.md')
        text=QMimeData();text.setText('a draft');self.w.input.insertFromMimeData(text)
        self.assertEqual(self.w.input.toPlainText(),'a draft')

    def test_readonly_brand_trigger_has_search_only_inside_popup(self):
        picker=self.w.model_brands
        self.assertFalse(picker.isEditable());self.assertIsNone(picker.lineEdit())
        picker.showPopup();self.app.processEvents();picker.search.setText('vid')
        self.assertEqual(picker.results.count(),1)
        self.assertEqual(picker.results.item(0).text(),'NVIDIA')
        picker.choose_current();self.assertEqual(picker.currentData(),'NVIDIA');self.assertFalse(picker.popup.isVisible())

    def test_activity_visible_while_running_and_real_tool_details_expand(self):
        m=self.w.add_message('assistant','');m.begin('stream');QTest.qWait(30)
        self.assertTrue(m.activity_details.isVisible());self.assertNotIsInstance(m.activity_details,QScrollArea)
        event={'key':'call-1','kind':'tool','title':'Read project file','detail':'{"path":"notes.md"}','seconds':1,'state':'running'}
        m.add_activity(event);m.add_activity({**event,'state':'complete','summary':'12 lines read'})
        self.assertEqual(sum(a.get('key')=='call-1' for a in m.live_activities),1)
        control=next(b for b in m.activity_details.findChildren(QPushButton) if b.text()=='Read project file')
        control.click();QTest.qWait(20)
        self.assertIn('call-1',m.activity_details.expanded_keys)
        m.apply_metadata({'state':'cancelled','seconds':4,'activities':m.live_activities,'checkpoint':{'schema':1}})
        self.assertTrue(m.resume_button.isVisible())
        with patch.object(self.w,'send') as send:
            m.resume_button.click();send.assert_called_once()
            self.assertIn('interrupted task',self.w.input.toPlainText())

    def test_new_chat_context_shows_and_preserves_the_selected_project(self):
        project=self.root/'Example Project';project.mkdir()
        uid=self.w.history.add_project('Example Project',str(project))
        self.w.new_project_chat(uid);QTest.qWait(20)
        self.assertEqual(self.w.chat_project.currentData(),uid)
        self.assertEqual(self.w.chat_project.currentText(),'Example Project')
        self.assertEqual(self.w.chat_project.toolTip(),str(project))
        self.w.new_chat();self.assertEqual(self.w.active_project,uid)
        self.w.input.setPlainText('Keep this draft')
        self.w.chat_project.setCurrentIndex(0)
        self.assertIsNone(self.w.active_project);self.assertIsNone(self.w.chat_project.currentData())
        self.assertEqual(self.w.input.toPlainText(),'Keep this draft')
        self.assertFalse(self.w.chat_project_files.isEnabled())

    def test_resume_only_on_last_interrupted_reply_after_history_load(self):
        uid=self.w.history.create('Interrupted work')
        self.w.history.append(uid,[{'role':'user','content':'Write a guide'},
            {'role':'assistant','content':'Partial','_studio':{'state':'cancelled','seconds':3}},
            {'role':'user','content':'Continue'},
            {'role':'assistant','content':'Another partial','_studio':{'state':'limited','seconds':2}}])
        self.w.refresh_chats()
        item=next(self.w.chat_list.item(i) for i in range(self.w.chat_list.count()) if self.w.chat_list.item(i).data(Qt.ItemDataRole.UserRole)==uid)
        self.w.select_chat(item)
        replies=[self.w.message_layout.itemAt(i).widget() for i in range(self.w.message_layout.count())]
        replies=[m for m in replies if isinstance(m,Message) and m.role=='assistant']
        self.assertTrue(replies[0].resume_button.isHidden());self.assertFalse(replies[1].resume_button.isHidden())
        self.w.add_message('user','A different follow-up')
        self.assertTrue(all(m.resume_button.isHidden() for m in replies))
        final=self.w.add_message('assistant','Finished')
        final.apply_metadata({'state':'complete'});self.w.sync_resume_actions()
        self.assertTrue(all(m.resume_button.isHidden() for m in [*replies,final]))

    def test_image_thumbnail_opens_zoomable_preview_in_composer_and_history(self):
        image=QImage(400,200,QImage.Format.Format_RGB32);image.fill(QColor('#aabbee'))
        self.w.paste_image(image);self.wait(lambda:self.w.attachment_worker and not self.w.attachment_worker.isRunning())
        thumbnail=self.w.attachment_items.findChild(AttachmentImage)
        thumbnail.click();QTest.qWait(20)
        viewer=self.w.findChild(ImagePreview);self.assertIsNotNone(viewer);self.assertTrue(viewer.isVisible())
        self.assertEqual(viewer.pixmap.size(),image.size());viewer.original();self.assertEqual(viewer.scale,1)
        viewer.zoom(1.25);self.assertGreater(viewer.scale,1);viewer.close();self.app.processEvents()
        m=self.w.add_message('user','Inspect this')
        m.set_attachments(self.w.attachments,self.w.config.runtime)
        history_thumbnail=m.findChild(AttachmentImage);self.assertIsNotNone(history_thumbnail)
        history_thumbnail.click();QTest.qWait(20)
        opened=[v for v in self.w.findChildren(ImagePreview) if v.isVisible()]
        self.assertEqual(len(opened),1);opened[0].close();self.app.processEvents()

    def test_nested_activity_groups_preserve_public_updates_and_payload_expansion(self):
        m=self.w.add_message('assistant','');m.begin('stream')
        intro={'kind':'message','key':'intro','text':'First I will inspect the source files.','seconds':0}
        m.add_activity(intro)
        for n in range(5):m.add_activity({'kind':'tool','key':str(n),'title':'Read file '+str(n),'state':'complete','detail':'actual arguments','summary':'Actual result','seconds':n})
        m.add_activity({'kind':'message','key':'finding','text':'The configuration explains the failure.','seconds':6})
        m.add_activity({'kind':'integration','provider':'Documentation','tool_name':'search','key':'search','title':'Documentation · search','state':'running','detail':'query','seconds':7})
        QTest.qWait(30)
        groups=m.activity_details.findChildren(QPushButton,'activityGroupToggle')
        self.assertEqual(len(groups),2)
        self.assertTrue(all(not g.isChecked() for g in groups))
        self.assertEqual(m.activity_details.batches(m.live_activities)[0]['kind'],'message')
        groups[0].click();QTest.qWait(20)
        child=next(c for c in m.activity_details.findChildren(QPushButton,'activityTool') if c.text()=='Read file 0')
        self.assertTrue(child.isVisible());child.click();self.assertIn('0',m.activity_details.expanded_keys)
        for n in range(100):m.add_activity({'kind':'tool','key':'tail'+str(n),'title':'Read file','seconds':n})
        self.assertEqual(len(m.live_activities),80);self.assertEqual(m.live_activities[0],intro)

    def test_real_qt_picker_lists_folders_and_uppercase_images_with_blank_filename(self):
        (self.root/'Visible folder').mkdir();image=self.root/'PHOTO.PNG';image.write_bytes(b'fixture')
        checks=[]
        def inspect():
            dialog=QApplication.activeModalWidget()
            if not isinstance(dialog,NativeDialog):QTimer.singleShot(10,inspect);return
            field=dialog.findChild(QLineEdit,'fileNameEdit')
            checks.append(field.text())
            model=dialog.findChild(QFileSystemModel)
            root=model.index(str(self.root))
            def loaded():
                if not model.rowCount(root):QTimer.singleShot(10,loaded);return
                names={model.fileName(model.index(row,0,root)) for row in range(model.rowCount(root))}
                checks.append(names)
                dialog.reject()
            loaded()
        QTimer.singleShot(10,inspect)
        files,_=QFileDialog.getOpenFileNames(self.w,'Choose files',str(self.root),'Images (*.png *.PNG);;All files (*)')
        self.assertEqual(files,[]);self.assertEqual(checks[0],'')
        self.assertIn('Visible folder',checks[1]);self.assertIn('PHOTO.PNG',checks[1])

    def test_document_preview_does_not_rewrite_editor_content(self):
        from PySide6.QtWidgets import QListWidgetItem
        guide=self.root/'guide.md';guide.write_text('# A clear guide\n\nAn explanatory paragraph.\n\n## Examples\n\n- First example\n')
        self.w.config.settings.workspace=str(self.root)
        self.w.open_file(QListWidgetItem('guide.md'))
        self.w.workspace_preview_toggle.setChecked(True);self.w.toggle_document_preview()
        self.assertEqual(self.w.document_views.currentIndex(),1)
        self.assertIn('A clear guide',self.w.document_preview.toPlainText())
        self.assertEqual(self.w.editor.toPlainText(),guide.read_text())
        self.w.workspace_preview_toggle.setChecked(False);self.w.toggle_document_preview()
        self.assertEqual(self.w.document_views.currentIndex(),0)

    def test_verified_download_hides_after_delay_but_errors_remain_retryable(self):
        self.w.open_preferences(2)
        self.w.download_panel.show()
        with patch.object(self.w,'select_model'),patch.object(self.w,'refresh_models'):
            self.w.download_complete({'filename':'fixture.gguf'})
        self.assertTrue(self.w.download_hide_timer.isActive())
        self.w.download_hide_timer.setInterval(10);QTest.qWait(30)
        self.assertFalse(self.w.download_panel.isVisible())
        self.w.download_panel.show();self.w.download_failed('A recoverable network error')
        self.assertTrue(self.w.download_retry.isVisible())
