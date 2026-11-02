"""Regressions for tool authorization, stopping, and persistent document input."""
import json
import os
import tempfile
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QImage
from ai_studio.i18n import set_language
from ai_studio.config import Config
from ai_studio.attachments import prepare_attachment, extract_document, apply_images
from ai_studio.ui.workers import ChatWorker
from ai_studio.workspace import call_workspace


def tool(name, arguments, ident='tool'):
    return {'id':ident,'type':'function','function':{'name':name,'arguments':json.dumps(arguments)}}


class WorkflowSafetyTests(unittest.TestCase):
    def setUp(self):
        set_language("tr")

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def config(self, root):
        config = Config(root)
        path = root / 'fake.gguf';path.write_bytes(b'GGUF')
        config.settings.model_path = str(path)
        config.settings.workspace = str(root)
        config.settings.context = 50000
        config.settings.task_rounds = 4
        return config

    def worker(self, config, first, *, use_tools=True):
        class Engine:
            calls=0
            def stream(self, messages, tools, cancel, emit, status):
                self.calls += 1
                return first if self.calls == 1 else {'role':'assistant','content':'Done'}
        worker = ChatWorker(config, Engine(), [{'role':'user','content':'İncele'}], use_tools=use_tools)
        output=[];worker.completed.connect(output.append)
        return worker, output

    def test_unadvertised_tool_never_writes_in_plan_or_tools_off(self):
        for plan in (True, False):
            with self.subTest(plan=plan), tempfile.TemporaryDirectory() as raw:
                root=Path(raw);config=self.config(root);config.settings.plan_mode=plan
                first={'role':'assistant','content':'','tool_calls':[tool('workspace_write',{'path':'unauthorized.txt','mode':'create','content':'bad'})]}
                worker,output=self.worker(config, first, use_tools=plan)
                worker.run()
                self.assertFalse((root/'unauthorized.txt').exists())
                response=next(m for m in output[0] if m['role']=='tool')
                self.assertIn('bu turda etkin değil',response['content'])

    def test_cancel_between_two_writes_skips_remaining_call(self):
        with tempfile.TemporaryDirectory() as raw:
            root=Path(raw);config=self.config(root)
            first={'role':'assistant','content':'','tool_calls':[tool('workspace_write',{'path':name,'mode':'create','content':'safe'},name) for name in ('first.txt','second.txt')]}
            worker,output=self.worker(config,first)
            def write_then_stop(*args):
                value=call_workspace(*args);worker.cancel.set();return value
            with patch('ai_studio.ui.workers.call_workspace',side_effect=write_then_stop):worker.run()
            self.assertTrue((root/'first.txt').is_file())
            self.assertFalse((root/'second.txt').exists())
            self.assertEqual(next(m['_studio']['state'] for m in reversed(output[0]) if '_studio' in m),'cancelled')

    def test_complete_json_tool_reply_is_preserved_and_length_state_is_limited(self):
        with tempfile.TemporaryDirectory() as raw:
            root=Path(raw);config=self.config(root);(root/'large.txt').write_text('x'*15000)
            first={'role':'assistant','content':'','tool_calls':[tool('workspace_read',{'path':'large.txt'})]}
            worker,output=self.worker(config,first);worker.run()
            response=next(m for m in output[0] if m['role']=='tool')
            self.assertEqual(len(json.loads(response['content'])['content']),15000)
            worker,output=self.worker(config,{'role':'assistant','content':'Kısmi yanıt','_finish_reason':'length'})
            worker.run()
            self.assertEqual(output[0][-1]['_studio']['state'],'limited')

    def test_utf16_and_image_integrity_and_cancel(self):
        with tempfile.TemporaryDirectory() as raw:
            root=Path(raw);path=root/'note.txt';path.write_text('Türkçe UTF16',encoding='utf-16')
            self.assertEqual(extract_document(path),'Türkçe UTF16')
            cancel=threading.Event();cancel.set()
            with self.assertRaises(InterruptedError):prepare_attachment(path,root/'runtime',cancel)
            path=root/'image.png';image=QImage(40,40,QImage.Format.Format_RGB32);image.fill(0xFF112233);image.save(str(path))
            descriptor=prepare_attachment(path,root/'runtime')
            cache=root/'runtime/attachments'/descriptor['image_path']
            cache.write_bytes(b'corrupted')
            with self.assertRaisesRegex(ValueError,'bozulmuş'):
                apply_images([{'role':'user','content':'İncele','_attachments':[descriptor]}],root/'runtime')

    def test_transformers_hybrid_passes_bounded_auto_placement_without_remote_code(self):
        from ai_studio.engine.transformers_backend import TransformersEngine
        with tempfile.TemporaryDirectory() as raw:
            root=Path(raw);path=root/'transformers';path.mkdir();(path/'config.json').write_text('{}')
            config=Config(root);config.settings.model_path=str(path);config.settings.acceleration='hybrid'
            fake_model=Mock();fake_config=Mock();fake_config.from_pretrained.return_value=SimpleNamespace()
            loader=Mock();loader.from_pretrained.return_value=fake_model
            torch=SimpleNamespace(cuda=SimpleNamespace(is_available=lambda:True,empty_cache=lambda:None),float16='float16')
            transformers=SimpleNamespace(AutoConfig=fake_config,AutoTokenizer=Mock(),AutoModelForCausalLM=loader,AutoModelForImageTextToText=Mock(),BitsAndBytesConfig=Mock())
            plan=SimpleNamespace(vram_budget=3.5,ram_budget=6)
            with patch.dict('sys.modules',{'torch':torch,'transformers':transformers}),patch('ai_studio.engine.transformers_backend.plan_memory',return_value=plan):
                engine=TransformersEngine(config);engine.ensure(threading.Event())
            kwargs=loader.from_pretrained.call_args.kwargs
            self.assertEqual(kwargs['device_map'],'auto')
            self.assertEqual(kwargs['max_memory'],{0:'3584MiB','cpu':'6144MiB'})
            self.assertTrue(kwargs['local_files_only']);self.assertFalse(kwargs['trust_remote_code'])
