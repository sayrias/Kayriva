import json
import os
import struct
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPainter, QPdfWriter
from PySide6.QtWidgets import QApplication
from ai_studio.attachments import prepare_attachment, attachment_prompt, image_descriptors, apply_images, prompt_size, extract_document
from ai_studio.i18n import set_language
from ai_studio.config import Config, Settings
from ai_studio.engine.memory import allocation_context, plan_memory, effective_cache
from ai_studio.engine.local import LocalEngine
from ai_studio.workspace import call_workspace
from ai_studio.ui.workers import ChatWorker


class WorkflowFeatureTests(unittest.TestCase):
    def setUp(self):
        set_language("tr")

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_image_is_persisted_privately_and_expanded_only_for_inference(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            source = root / 'Ekran.PNG'
            image = QImage(60, 40, QImage.Format.Format_RGB32)
            image.fill(Qt.GlobalColor.red)
            image.save(str(source))
            attachment = prepare_attachment(source, root / 'runtime')
            message = {'role':'user','content':'İncele' + attachment_prompt([attachment]),'_attachments':image_descriptors([attachment])}
            self.assertNotIn('base64', json.dumps(message))
            source.unlink()
            actual = apply_images([message], root / 'runtime')[0]
            self.assertNotIn('_attachments', actual)
            self.assertTrue(actual['content'][1]['image_url']['url'].startswith('data:image/png;base64,'))
            huge = [{'role':'user','content':[{'type':'image_url','image_url':{'url':'data:image/png;base64,'+'a'*200000}}]}]
            self.assertLess(prompt_size(huge), 5000)
            message['_attachments'][0]['image_path'] = '../outside.png'
            with self.assertRaises(ValueError):
                apply_images([message], root / 'runtime')

    def test_office_extraction_and_project_line_search(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            source = root / 'notes.docx'
            with zipfile.ZipFile(source, 'w') as archive:
                archive.writestr('word/document.xml','<document><p><t>Kod inceleme talimatı</t></p></document>')
            self.assertIn('Kod inceleme', extract_document(source))
            self.assertTrue(json.loads(call_workspace(root, 'workspace_read', {'path':'notes.docx'}))['document'])
            (root / 'large.py').write_text('\n'.join('def item_'+str(n)+'(): pass' for n in range(10000)))
            (root / '.env').write_text('private-api-key')
            matches=json.loads(call_workspace(root,'workspace_search',{'query':'ITEM_195()'}))
            self.assertEqual(matches['matches'][0]['line'],196)
            secret=json.loads(call_workspace(root,'workspace_search',{'query':'private-api-key'}))
            self.assertEqual(secret['matches'],[])
            section=json.loads(call_workspace(root,'workspace_read_lines',{'path':'large.py','start_line':196,'count':2}))
            self.assertTrue(section['content'].startswith('196: def item_195'))
            with self.assertRaises(ValueError):call_workspace(root,'workspace_read_lines',{'path':'large.py','start_line':0})

    def test_pdf_text_and_untrusted_office_xml(self):
        with tempfile.TemporaryDirectory() as raw:
            path=Path(raw)/'guide.pdf'
            writer=QPdfWriter(str(path))
            painter=QPainter(writer);painter.drawText(120,300,'Kayriva PDF document inspection');painter.end()
            self.assertIn('PDF document',extract_document(path))
            bad=path.with_suffix('.docx')
            with zipfile.ZipFile(bad,'w') as archive:
                archive.writestr('word/document.xml','<!DOCTYPE document [<!ENTITY a "bad">]><document>&a;</document>')
            with self.assertRaises(ValueError):extract_document(bad)

    def test_low_memory_profile_reduces_cache_context_and_microbatch(self):
        with tempfile.TemporaryDirectory() as raw:
            path=Path(raw)/'test.gguf'
            data=b'GGUF'+struct.pack('<IQQ',3,0,2)
            for key,value in [('qwen3.block_count',32),('qwen3.context_length',32768)]:
                key=key.encode();data+=struct.pack('<Q',len(key))+key+struct.pack('<II',4,value)
            path.write_bytes(data)
            config=Config(Path(raw));settings=config.settings;settings.model_path=str(path);settings.context=0;settings.max_tokens=-1
            counters={'ram_total':16,'ram_used':2,'vram_total':6,'vram_used':1}
            normal=plan_memory(settings,path,counters,context=4096)
            settings.memory_profile='low_memory'
            compact=plan_memory(settings,path,counters,context=4096)
            self.assertLess(compact.ram+compact.vram,normal.ram+normal.vram)
            self.assertEqual(effective_cache(settings),'q8_0')
            self.assertEqual(allocation_context(settings,path,[{'role':'user','content':'Merhaba'}]),2048)
            engine=LocalEngine(config);engine.memory_plan=compact
            command=engine.command(Path('llama-server'),path,8000)
            self.assertEqual(command[command.index('--ubatch-size')+1],'32')
            self.assertEqual(command[command.index('--cache-type-v')+1],'q8_0')
            with self.assertRaisesRegex(ValueError,'mmproj'):
                engine.stream([{'role':'user','content':[{'type':'image_url','image_url':{'url':'data:image/png;base64,AA'}}]}],[],__import__('threading').Event(),lambda _:None)

    def test_long_task_plan_persists_and_round_limit_is_explicit(self):
        class Engine:
            config=None
            def stream(self,messages,tools,cancel,emit,status):
                return {'role':'assistant','content':'','tool_calls':[{'id':'step','type':'function','function':{'name':'task_plan','arguments':json.dumps({'steps':[{'title':'Dosyaları incele','state':'in_progress'}]})}}]}
        with tempfile.TemporaryDirectory() as raw:
            config=Config(Path(raw));config.settings.task_rounds=4;config.settings.context=16000
            path=Path(raw)/'model.gguf';path.write_bytes(b'GGUF')
            config.settings.model_path=str(path)
            engine=Engine();worker=ChatWorker(config,engine,[{'role':'user','content':'İncele'}],use_tools=True)
            outputs=[];worker.completed.connect(outputs.append)
            worker.run()
            self.assertEqual(outputs[0][-2]['_studio']['state'],'limited')
            metadata=next(m['_studio'] for m in reversed(outputs[0]) if '_studio' in m)
            self.assertEqual(metadata['plan'][0]['title'],'Dosyaları incele')
            self.assertTrue(any('4 araç turu' in a['text'] for a in metadata['activities']))
