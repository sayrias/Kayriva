import sqlite3
import tempfile
import unittest
from pathlib import Path
from ai_studio.storage import History


class HistoryFeatureTests(unittest.TestCase):
    def test_old_database_migration_pin_search_and_export(self):
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / 'history.db'
            db = sqlite3.connect(path)
            db.executescript("CREATE TABLE chats(id TEXT PRIMARY KEY,title TEXT NOT NULL,updated TEXT DEFAULT CURRENT_TIMESTAMP); INSERT INTO chats(id,title) VALUES('old','Eski sohbet');")
            db.close()
            h = History(path)
            h.append('old', [{'role':'user','content':'İyileştir: % ve _ işaretleri'}, {'role':'assistant','content':'**Tamam**','_studio':{'secret':'hidden'}}, {'role':'tool','content':'hidden tool payload'}])
            newer = h.create('Yeni')
            h.pin('old',True)
            h.close()
            h = History(path)
            self.assertEqual(h.recent()[0][0], 'old')
            self.assertTrue(h.pinned('old'))
            self.assertEqual(h.search('iyileştir'), [('old','Eski sohbet')])
            self.assertEqual(h.search('%'), [('old','Eski sohbet')])
            self.assertEqual(h.search('hidden'), [])
            self.assertEqual(h.search('olmayan'), [])
            exported = h.export('old')
            self.assertIn('## Sen\n\nİyileştir',exported)
            self.assertIn('## Kayriva\n\n**Tamam**',exported)
            self.assertNotIn('secret',exported)
            self.assertNotIn('tool payload',exported)
            h.pin('old',False)
            self.assertEqual(h.recent()[0][0], newer)
            h.close()

    def test_prompt_library_persistence_update_and_delete(self):
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / 'history.db'
            h = History(path)
            uid = h.save_prompt('  İncele  ', '  Kodunu incele.  ')
            with self.assertRaises(ValueError):
                h.save_prompt('','metin')
            h.close()
            h = History(path)
            self.assertEqual(h.prompts(),[(uid,'İncele','Kodunu incele.')])
            h.save_prompt('Yeni ad','Yeni metin',uid)
            self.assertEqual(h.prompts(),[(uid,'Yeni ad','Yeni metin')])
            h.delete_prompt(uid)
            self.assertEqual(h.prompts(),[])
            h.close()
