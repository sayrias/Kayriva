"""Stopped document work resumes verified actions without repeated research."""
import copy
import json
import os
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import Mock, patch

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from PySide6.QtWidgets import QApplication

from ai_studio.config import Config
from ai_studio.i18n import set_language
from ai_studio.mcp import tool_alias
from ai_studio.storage import History
from ai_studio.ui.workers import ChatWorker, inference_messages, resume_requested
from ai_studio.workspace import call_workspace


def tool(name, arguments, ident='call'):
    return {'id':ident, 'type':'function', 'function':{'name':name, 'arguments':json.dumps(arguments)}}


class TaskResumeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        set_language('tr')

    def config(self, root):
        config = Config(root)
        config.settings.language = 'tr'
        set_language('tr')
        path = root/'model.gguf'; path.write_bytes(b'GGUF')
        config.settings.model_path = str(path)
        config.settings.context = 16000
        config.settings.workspace = str(root)
        config.settings.task_rounds = 4
        return config

    def run_worker(self, worker):
        output = []
        worker.completed.connect(output.append)
        worker.run()
        self.assertEqual(len(output), 1)
        return output[0]

    def test_resume_request_recognizes_both_button_languages_and_avoids_unrelated_requests(self):
        for text in ('Devam et', 'Kaldığın yerden devam et.', 'Durdurulan çalışmaya kaldığın yerden devam et.',
                     'Continue the interrupted task from where you stopped.', 'Resume', 'yarım kalan göreve devam et'):
            self.assertTrue(resume_requested(text), text)
        for text in ('Yeni bir araştırma yap', 'Devamlı integral nedir?', 'Sunucu kurulumu hakkında belge yaz'):
            self.assertFalse(resume_requested(text), text)

    def test_stopped_write_checkpoint_survives_history_and_resume_skips_initial_research(self):
        class Engine:
            def stream(self, messages, tools, cancel, emit, status):
                return {'role':'assistant', 'content':'', 'tool_calls':[
                    tool('workspace_write', {'path':name, 'mode':'create', 'content':'A verified section'}, name)
                    for name in ('first.txt', 'second.txt')]}
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw); config = self.config(root)
            user = {'role':'user', 'content':'Sunucuları araştır ve first.txt ile second.txt dosyalarını oluştur.'}
            worker = ChatWorker(config, Engine(), [user], 'deep')
            def write_then_stop(*args):
                result = call_workspace(*args)
                worker.cancel.set()
                return result
            with patch('ai_studio.ui.workers.Research') as research, patch('ai_studio.ui.workers.call_workspace', side_effect=write_then_stop):
                research.return_value.run.return_value = [{'title':'Official guide', 'url':'https://example.org/docs',
                    'snippet':'Summary', 'text':'Actual source material'}]
                research.context.return_value = 'Verified research context https://example.org/docs'
                output = self.run_worker(worker)
            metadata = next(m['_studio'] for m in reversed(output) if '_studio' in m)
            checkpoint = metadata['checkpoint']
            self.assertEqual(checkpoint['state'], 'cancelled')
            self.assertTrue(checkpoint['research_complete'])
            self.assertEqual(checkpoint['completed_tools'][0]['path'], 'first.txt')
            self.assertEqual(checkpoint['pending_tools'][0]['path'], 'second.txt')
            self.assertLessEqual(len(json.dumps(checkpoint, ensure_ascii=False)), 64000)
            history = History(root/'runtime/history.db')
            chat = history.create()
            history.append(chat, [user, *output, {'role':'user','content':'Durdurulan çalışmaya kaldığın yerden devam et.'}])
            class ResumeEngine:
                calls = 0
                seen = []
                def stream(self, messages, tools, cancel, emit, status):
                    self.calls += 1
                    self.seen = copy.deepcopy(messages)
                    if self.calls == 1:
                        return {'role':'assistant', 'content':'', 'tool_calls':[
                            tool('workspace_write', {'path':'second.txt','mode':'create','content':'Remaining section'}, 'second') ]}
                    return {'role':'assistant','content':'İki dosya hazır.'}
            engine = ResumeEngine()
            resumed = ChatWorker(config, engine, history.messages(chat), 'deep')
            with patch('ai_studio.ui.workers.Research.run', side_effect=AssertionError('Research must not restart')):
                final = self.run_worker(resumed)
            self.assertTrue(resumed.resumed)
            self.assertTrue((root/'first.txt').is_file())
            self.assertTrue((root/'second.txt').is_file())
            self.assertIn('first.txt', engine.seen[0]['content'])
            self.assertIn('araştırmayı veya', engine.seen[0]['content'].casefold())
            self.assertIn('Verified research context', str(engine.seen))
            self.assertEqual(final[-1]['_studio']['state'], 'complete')
            history.close()

    def test_changed_workspace_does_not_replay_previous_project_checkpoint(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw); config = self.config(root)
            previous = {'role':'assistant', 'content':'', '_studio':{'state':'cancelled', 'checkpoint':{
                'schema':1, 'workspace':str(root/'other'), 'request':'Write private.txt', 'research_complete':True}}}
            worker = ChatWorker(config, Mock(), [previous, {'role':'user','content':'Devam et'}])
            self.assertIsNone(worker.restore_checkpoint('Devam et'))

    def test_long_successful_write_is_kept_in_history_but_not_fed_back_in_full(self):
        document = 'A long report section. '*3000
        class Engine:
            calls = 0
            received = []
            def stream(self, messages, tools, cancel, emit, status):
                self.calls += 1
                self.received.append(copy.deepcopy(messages))
                if self.calls == 1:
                    return {'role':'assistant', 'content':'', 'tool_calls':[
                        tool('workspace_write', {'path':'report.txt', 'mode':'create', 'content':document})]}
                return {'role':'assistant','content':'Dosya kaydedildi.'}
        with tempfile.TemporaryDirectory() as raw:
            config = self.config(Path(raw)); engine = Engine()
            worker = ChatWorker(config, engine, [{'role':'user','content':'Bir rapor dosyası oluştur.'}])
            output = self.run_worker(worker)
            self.assertEqual(engine.calls, 2)
            original = next(m for m in output if m.get('tool_calls'))
            self.assertEqual(json.loads(original['tool_calls'][0]['function']['arguments'])['content'], document)
            prepared = next(m for m in engine.received[1] if m.get('tool_calls'))
            self.assertLess(len(prepared['tool_calls'][0]['function']['arguments']), 1000)
            result = next(m for m in engine.received[1] if m['role'] == 'tool')
            self.assertEqual(json.loads(result['content'])['bytes'], len(document.encode()))
            self.assertIn('sha256', result['content'])

    def test_broken_enabled_mcp_does_not_block_healthy_tools_or_initial_search_failure(self):
        specs = [{'name':'Broken','enabled':True}, {'name':'Healthy','enabled':True}]
        clients = []
        class Client:
            def __init__(self, spec, offline):
                self.spec = spec; self.closed = False; clients.append(self)
            def open(self):
                if self.spec['name'] == 'Broken':
                    raise RuntimeError('server unavailable')
                return self
            def tools(self):
                return [{'name':'read_reference', 'description':'Read reference', 'inputSchema':{'type':'object','properties':{}}}]
            def call(self, name, args):
                return {'content':[{'type':'text','text':'Verified external result'}]}
            def close(self):
                self.closed = True
        class Engine:
            calls = 0
            names = []
            def stream(self, messages, tools, cancel, emit, status):
                self.calls += 1
                self.names = [t['function']['name'] for t in tools]
                if self.calls == 1:
                    return {'role':'assistant','content':'','tool_calls':[tool(tool_alias(1,'read_reference'),{})]}
                return {'role':'assistant','content':'Reference used.'}
        with tempfile.TemporaryDirectory() as raw:
            config = self.config(Path(raw)); config.settings.mcp_servers = specs; engine = Engine()
            worker = ChatWorker(config, engine, [{'role':'user','content':'Araştır'}], 'quick')
            events = []; worker.activity.connect(events.append)
            with patch('ai_studio.ui.workers.MCPClient', Client), patch('ai_studio.ui.workers.Research.run', side_effect=RuntimeError('Search provider denied')):
                output = self.run_worker(worker)
            self.assertEqual(output[-1]['_studio']['state'], 'complete')
            self.assertIn(tool_alias(1,'read_reference'), engine.names)
            self.assertTrue(clients[1].closed)
            actual = [event for event in events if event['key'] == 'call']
            self.assertEqual([event['state'] for event in actual], ['running','complete'])
            self.assertTrue(all(event['kind']=='integration' for event in actual))
            self.assertEqual(actual[-1]['provider'], 'Healthy')
            self.assertEqual(actual[-1]['tool_name'], 'read_reference')
            self.assertEqual(actual[-1]['title'], 'Healthy · read_reference')
            self.assertIn('Verified external result', actual[-1]['summary'])

    def test_slow_operation_cancel_is_fast_and_heartbeat_does_not_displace_trace(self):
        with tempfile.TemporaryDirectory() as raw:
            worker = ChatWorker(self.config(Path(raw)), Mock(), [{'role':'user','content':'Test'}])
            release = threading.Event()
            timer = threading.Timer(.1, worker.cancel.set)
            timer.start(); started = time.monotonic()
            try:
                with self.assertRaises(InterruptedError):
                    worker.wait_operation(lambda: release.wait(2), 10, 'MCP')
                self.assertLess(time.monotonic()-started, .7)
            finally:
                timer.cancel(); release.set()
            worker.activities = [{'kind':'tool','key':'important','text':'Verified file'}]
            for seconds in range(5, 600, 5):
                worker.report_status(f'Yerel motor isteği işliyor · {seconds} sn')
            self.assertEqual(len(worker.activities), 2)
            self.assertEqual(worker.activities[0]['key'], 'important')

    def test_activity_is_bounded_redacted_and_has_real_tool_duration(self):
        with tempfile.TemporaryDirectory() as raw:
            worker = ChatWorker(self.config(Path(raw)), Mock(), [{'role':'user','content':'Test'}])
            call = tool('workspace_write', {}, 'write')
            args = {'path':'report.txt', 'content':'x'*30000,
                    'headers':{'Authorization':'Bearer abc123'}, 'nested':{'api_key':'secret-value'}}
            worker.tool_activity(call, args, 'running')
            worker.tool_activity(call, args, 'complete', json.dumps({'token':'hidden-token','message':'ok'}))
            self.assertEqual(len(worker.activities),1)
            event = worker.activities[0]
            self.assertNotIn('abc123', event['detail'])
            self.assertNotIn('secret-value', event['detail'])
            self.assertNotIn('hidden-token', event['summary'])
            self.assertLessEqual(len(event['detail']),1800)
            self.assertLessEqual(len(event['summary']),1200)
            self.assertGreaterEqual(event['duration'],0)

    def test_search_checkpoint_survives_cancel_during_source_reading(self):
        class Engine:
            def stream(self, *args):
                raise AssertionError('Model must not run after cancellation')
        with tempfile.TemporaryDirectory() as raw:
            worker = ChatWorker(self.config(Path(raw)), Engine(), [{'role':'user','content':'Rehberi araştır.'}], 'deep')
            def stopped_research(research, query, mode, cancel, status):
                research.on_sources([{'title':'Guide','url':'https://example.org/guide','snippet':'Actual summary'}])
                cancel.set()
                raise InterruptedError('Stopped during reading')
            with patch('ai_studio.ui.workers.Research.run', stopped_research):
                output = self.run_worker(worker)
            checkpoint = output[-1]['_studio']['checkpoint']
            self.assertEqual(checkpoint['state'],'cancelled')
            self.assertTrue(checkpoint['research_complete'])
            self.assertIn('https://example.org/guide',checkpoint['research_context'])
