import json
import os
import sqlite3
import tempfile
import unittest
from pathlib import Path

from ai_studio.jobs import Jobs
from ai_studio.bridge import handle
from ai_studio.config import Config


class ProfileTests(unittest.TestCase):
    def test_existing_queue_migration_preserves_tasks(self):
        with tempfile.TemporaryDirectory() as raw:
            path=Path(raw)/'jobs.sqlite'
            db=sqlite3.connect(path)
            db.execute("CREATE TABLE jobs(id TEXT PRIMARY KEY,prompt TEXT,kind TEXT,mode TEXT,state TEXT,result TEXT,created REAL,updated REAL,cancelled INTEGER)")
            db.execute("INSERT INTO jobs VALUES('old','keep','model','quick','complete','result',1,1,0)")
            db.commit();db.close()
            jobs=Jobs(path)
            self.assertEqual(jobs.get('old')['result'],'result')
            self.assertEqual(jobs.get('old')['profile_id'],'default')
            jobs.close()

    def test_profile_routing_snapshot_and_connection_isolation(self):
        with tempfile.TemporaryDirectory() as raw:
            jobs=Jobs(Path(raw)/'jobs.sqlite')
            profiles=[{'id':'a','name':'Research','role':'Compare','instructions':'Cite','enabled':True},
                      {'id':'b','name':'Edit','role':'Review','enabled':True}]
            jobs.heartbeat(True,profiles)
            response=handle(jobs,'tools/call',{'name':'ask_local_model','arguments':{'prompt':'One'}},'a')
            uid=json.loads(response['content'][0]['text'])['task_id']
            profiles[0]['role']='Changed'
            jobs.heartbeat(True,profiles)
            self.assertEqual(json.loads(jobs.claim()['profile'])['role'],'Compare')
            result=handle(jobs,'tools/call',{'name':'get_task_result','arguments':{'task_id':uid}},'b')
            self.assertTrue(result['isError'])
            result=handle(jobs,'tools/call',{'name':'cancel_task','arguments':{'task_id':uid}},'b')
            self.assertTrue(result['isError']);self.assertFalse(jobs.get(uid)['cancelled'])
            listed=handle(jobs,'tools/call',{'name':'list_tasks'},'b')
            self.assertEqual(json.loads(listed['content'][0]['text'])['tasks'],[])
            profiles[0]['enabled']=False;jobs.heartbeat(True,profiles)
            with self.assertRaises(ValueError):jobs.create('Denied',external=True,profile_id='a')
            with self.assertRaises(ValueError):jobs.create('Deleted',external=True,profile_id='unknown')
            jobs.heartbeat(False,profiles)
            with self.assertRaises(ValueError):jobs.create('Offline',external=True,profile_id='b')
            jobs.close()

    def test_legacy_single_profile_settings_are_migrated(self):
        with tempfile.TemporaryDirectory() as raw:
            root=Path(raw);(root/'runtime').mkdir()
            (root/'runtime/settings.json').write_text(json.dumps({'team_name':'Old','team_role':'Editor','team_instructions':'Keep this'}))
            config=Config(root)
            self.assertEqual(config.settings.team_profiles[0]['instructions'],'Keep this')
            config.save()
            self.assertEqual(Config(root).settings.team_profiles[0]['name'],'Old')
