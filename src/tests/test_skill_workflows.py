"""Exercise real worker tool flows, announcements and persisted activity metadata."""
import copy
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from PySide6.QtWidgets import QApplication
from ai_studio.config import Config
from ai_studio.i18n import set_language
from ai_studio.storage import History
from ai_studio.ui.workers import ChatWorker
from test_task_resume import tool
from test_skills import package


class SkillWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.app=QApplication.instance() or QApplication([])
    def tearDown(self): set_language('en')
    def config(self, root, language='en'):
        config=Config(root); config.settings.language=language; set_language(language)
        path=root/'model.gguf'; path.write_bytes(b'GGUF'); config.settings.model_path=str(path)
        config.settings.context=16000; config.settings.task_rounds=4
        return config
    def run_worker(self, worker):
        output=[]; worker.completed.connect(output.append); worker.run()
        self.assertEqual(len(output),1); return output[0]

    def test_relevant_guides_are_read_before_use_announced_and_persisted_in_both_languages(self):
        class Engine:
            def stream(self,messages,tools,cancel,emit,status):
                self.seen=copy.deepcopy(messages)
                return {'role':'assistant','content':'Finished.'}
        for language, title in [('en','Documents'),('tr','Belgeler')]:
            with self.subTest(language=language), tempfile.TemporaryDirectory() as raw:
                root=Path(raw); config=self.config(root,language); engine=Engine()
                user={'role':'user','content':'Research server platforms and write a report.'}
                worker=ChatWorker(config,engine,[user]); output=self.run_worker(worker)
                activities=output[-1]['_studio']['activities']
                self.assertFalse(any(event.get('key')=='opening' for event in activities))
                used=[event for event in activities if event.get('kind')=='skill']
                self.assertEqual({event['skill_name'] for event in used}, {'Research',title} if language=='en' else {'Araştırma',title})
                self.assertTrue(all(event['state']=='complete' for event in used))
                self.assertTrue(any(event['key']=='skill-usage' and title in event['text'] for event in activities))
                self.assertEqual(len(worker.loaded_skills),2)
                self.assertNotIn('# Debugging workflow',engine.seen[0]['content'])
                history=History(config.runtime/'history.db'); chat=history.create(); history.append(chat,[user,*output])
                self.assertEqual(history.messages(chat)[-1]['_studio']['activities'],activities); history.close()

    def test_disabled_and_unrelated_skills_are_not_loaded_or_claimed_as_used(self):
        class Engine:
            def stream(self,*args): return {'role':'assistant','content':'Hello.'}
        with tempfile.TemporaryDirectory() as raw:
            config=self.config(Path(raw)); config.settings.skill_enabled={'research':False}
            for request in ('Hello!', '$research'):
                worker=ChatWorker(config,Engine(),[{'role':'user','content':request}]); output=self.run_worker(worker)
                self.assertEqual(worker.loaded_skills,{})
                self.assertFalse(any(e.get('kind')=='skill' for e in output[-1]['_studio']['activities']))
            self.assertIn('disabled',str(output[-1]['_studio']['activities']))

    def test_plan_mode_retains_passive_guidance_without_calling_mcp_or_writing_files(self):
        class Engine:
            def stream(self,messages,tools,cancel,emit,status):
                self.tools=tools; self.system=messages[0]['content']
                return {'role':'assistant','content':'Plan only.'}
        with tempfile.TemporaryDirectory() as raw:
            config=self.config(Path(raw)); config.settings.plan_mode=True; config.settings.workspace=raw
            config.settings.mcp_servers=[{'name':'Never connect','enabled':True}]; engine=Engine()
            worker=ChatWorker(config,engine,[{'role':'user','content':'$planning plan this project'}])
            with patch('ai_studio.ui.workers.MCPClient',side_effect=AssertionError('No plan mode connection')):
                output=self.run_worker(worker)
            self.assertEqual(engine.tools,[]); self.assertIn('Plan mode',engine.system)
            self.assertEqual(set(worker.loaded_skills),{('planning','SKILL.md')})
            self.assertEqual(output[-1]['_studio']['state'],'complete')

    def test_explicit_imported_guide_resources_and_duplicate_reads_are_tool_results(self):
        class Engine:
            def stream(self,messages,tools,cancel,emit,status):
                self.calls=getattr(self,'calls',0)+1
                if self.calls==1: return {'role':'assistant','content':'I’ll inspect the referenced checks.', 'tool_calls':[
                    tool('skill_read',{'id':self.ident,'path':'checks.md'},'resource'),
                    tool('skill_read',{'id':self.ident},'duplicate')]}
                self.seen=messages
                return {'role':'assistant','content':'Checks applied.'}
        with tempfile.TemporaryDirectory() as raw:
            root=Path(raw); config=self.config(root/'app'); engine=Engine()
            path=package(root/'incoming','Inspect [checks](checks.md).')
            (path.parent/'checks.md').write_text('Measure contrast using actual colors.')
            worker=ChatWorker(config,engine,[{'role':'user','content':'$interface-audit inspect this interface'}])
            entry=worker.skill_library.import_path(path); engine.ident=entry['id']
            output=self.run_worker(worker)
            results=[json.loads(m['content']) for m in output if m.get('role')=='tool']
            self.assertIn('actual colors',results[0]['content']); self.assertTrue(results[1]['already_loaded'])
            events=output[-1]['_studio']['activities']
            self.assertTrue(any(e.get('kind')=='message' and e['key']=='update-round-0' for e in events))
            self.assertTrue(any(e.get('kind')=='skill' and e['key']=='resource' and e['state']=='complete' for e in events))

    def test_only_two_guides_and_bounded_resource_text_can_be_loaded_per_turn(self):
        with tempfile.TemporaryDirectory() as raw:
            worker=ChatWorker(self.config(Path(raw)),None,[{'role':'user','content':'Test'}])
            for ident in ('research','documents'): worker.skill_tool('skill_read',{'id':ident})
            with self.assertRaises(ValueError): worker.skill_tool('skill_read',{'id':'debugging'})
            self.assertTrue(json.loads(worker.skill_tool('skill_read',{'id':'research'}))['already_loaded'])
        with tempfile.TemporaryDirectory() as raw:
            root=Path(raw); worker=ChatWorker(self.config(root/'app'),None,[{'role':'user','content':'Test'}])
            path=package(root/'incoming','[one](one.md) [two](two.md) [three](three.md)')
            for name in ('one.md','two.md','three.md'): (path.parent/name).write_text('x'*8500)
            entry=worker.skill_library.import_path(path)
            with self.assertRaises(ValueError): worker.skill_tool('skill_read',{'id':entry['id'],'path':'one.md'})
            worker.skill_tool('skill_read',{'id':entry['id']})
            worker.skill_tool('skill_read',{'id':entry['id'],'path':'one.md'})
            second=json.loads(worker.skill_tool('skill_read',{'id':entry['id'],'path':'two.md'}))
            self.assertTrue(second['limited']); self.assertEqual(worker.skill_characters,16000)
            with self.assertRaises(ValueError): worker.skill_tool('skill_read',{'id':entry['id'],'path':'three.md'})

    def test_auto_loading_respects_its_serialized_context_budget(self):
        with tempfile.TemporaryDirectory() as raw:
            root=Path(raw); worker=ChatWorker(self.config(root/'app'),None,[{'role':'user','content':'Test'}])
            guide=package(root/'incoming','Line with escaped JSON: "\\x"\n'*2000)
            entry=worker.skill_library.import_path(guide)
            context=worker.prepare_skills('$interface-audit',900)
            self.assertLessEqual(len(context),900)
            self.assertIn(entry['id'],context)
            self.assertTrue(worker.loaded_skills[(entry['id'],'SKILL.md')]['limited'])
            loaded = worker.loaded_skills[(entry['id'],'SKILL.md')]
            self.assertEqual(loaded['next_offset'], len(loaded['content']))
            tail = json.loads(worker.skill_tool('skill_read', {'id':entry['id'], 'offset':loaded['next_offset']}))
            original = worker.skill_library._path(entry['id']).read_text()
            from ai_studio.skills import parse_skill
            self.assertEqual(tail['content'], parse_skill(original)['content'][loaded['next_offset']:tail['next_offset']])
            self.assertTrue(json.loads(worker.skill_tool('skill_read', {'id':entry['id'], 'offset':loaded['next_offset']}))['already_loaded'])

    def test_first_actual_model_update_is_retained_instead_of_a_static_or_skill_opening(self):
        with tempfile.TemporaryDirectory() as raw:
            worker=ChatWorker(self.config(Path(raw)),None,[{'role':'user','content':'Test'}])
            worker.public_update('Using skill: Documents.','skill-usage')
            worker.public_update('I’ll inspect the report source files.','update-round-0',origin='assistant')
            for i in range(100): worker.public_update('Verified public result '+str(i),str(i),origin='assistant')
            worker.public_update('<think>Private reasoning</think>Public finding.','safe')
            self.assertEqual(len(worker.activities),80); self.assertEqual(worker.activities[0]['key'],'update-round-0')
            self.assertEqual(worker.activities[-1]['text'],'Public finding.')
            self.assertNotIn('Private reasoning',str(worker.activities))

    def test_different_requests_show_their_actual_model_progress_without_a_narration_call(self):
        class Engine:
            def __init__(self, progress): self.progress=progress; self.calls=0
            def stream(self,messages,tools,cancel,emit,status):
                self.calls+=1
                if self.calls==1:
                    self.system=messages[0]['content']
                    return {'role':'assistant','content':self.progress,'tool_calls':[tool('workspace_list',{'path':'.'},'files')]}
                return {'role':'assistant','content':'The requested file list is ready.'}
        requests=[('List my Python source files.', 'I’ll list the project files and identify the Python sources.'),
                  ('Find the project license file.', 'I’ll check the project files for its license.')]
        seen=[]
        for request, progress in requests:
            with self.subTest(request=request), tempfile.TemporaryDirectory() as raw:
                root=Path(raw); config=self.config(root); config.settings.workspace=raw
                engine=Engine(progress); worker=ChatWorker(config,engine,[{'role':'user','content':request}])
                output=self.run_worker(worker)
                updates=[event for event in output[-1]['_studio']['activities'] if event.get('kind')=='message']
                self.assertEqual([event['text'] for event in updates],[progress])
                self.assertEqual(updates[0]['origin'],'assistant'); self.assertEqual(engine.calls,2)
                self.assertIn('specific to the user',engine.system)
                self.assertEqual(sum(message.get('content')=='The requested file list is ready.' for message in output),1)
                self.assertNotIn('The requested file list is ready.',str(updates))
                seen.append(updates[0]['text'])
        self.assertNotEqual(*seen)

    def test_simple_greeting_has_only_the_model_reply_without_preflight_or_automatic_research(self):
        class Engine:
            calls=0
            def stream(self,messages,tools,cancel,emit,status):
                self.calls+=1
                return {'role':'assistant','content':'Merhaba! Sana nasıl yardımcı olabilirim?'}
        with tempfile.TemporaryDirectory() as raw:
            config=self.config(Path(raw)); engine=Engine()
            worker=ChatWorker(config,engine,[{'role':'user','content':'Merhaba'}])
            with patch('ai_studio.ui.workers.Research.run',side_effect=AssertionError('No selected research mode')):
                output=self.run_worker(worker)
            self.assertEqual(engine.calls,1); self.assertEqual(worker.loaded_skills,{})
            self.assertEqual([message['content'] for message in output],['Merhaba! Sana nasıl yardımcı olabilirim?'])
            self.assertFalse(any(event.get('kind')=='message' for event in output[-1]['_studio']['activities']))
