"""Official skill texts remain original, opt-in and verifiable offline."""
import hashlib
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ai_studio.config import Config
from ai_studio.i18n import set_language
from ai_studio.skills import SkillLibrary, parse_skill

ROOT = Path(__file__).resolve().parents[2]

class CuratedSkillTests(unittest.TestCase):
    def setUp(self): set_language('en')
    def tearDown(self): set_language('en')

    def test_long_official_guide_can_be_read_in_bounded_contiguous_pages(self):
        with tempfile.TemporaryDirectory() as raw:
            library = SkillLibrary(Config(Path(raw)))
            library.install_curated('impeccable')
            first = library.read('impeccable')
            self.assertTrue(first['limited'])
            second = library.read('impeccable', offset=first['next_offset'])
            original = library.read_curated(library._curated('impeccable'), 'SKILL.md')
            self.assertEqual(first['content'] + second['content'], original)
            self.assertIsNone(second['next_offset'])
            for offset in (-1, True, '8000', len(original)+1):
                with self.assertRaises(ValueError): library.read('impeccable', offset=offset)

    def test_official_guides_are_available_by_original_name_but_not_active_until_added(self):
        with tempfile.TemporaryDirectory() as raw:
            config = Config(Path(raw))
            library = SkillLibrary(config)
            available = {e['id']:e for e in library.entries(include_available=True) if e.get('curated')}
            self.assertEqual(set(available), {'impeccable','frontend-design','mcp-builder','webapp-testing','skill-creator','theme-factory'})
            self.assertFalse(any(e.get('curated') for e in library.entries()))
            self.assertEqual(library.explicit('$impeccable'), [])
            for ident, entry in available.items():
                self.assertEqual(entry['name'], ident)
                self.assertFalse(entry['installed'])
                self.assertIn('github.com/', entry['source'])
                self.assertEqual(entry['license'], 'Apache-2.0')
                self.assertIn('content', library.read(ident, require_enabled=False))
            with self.assertRaises(ValueError):library.read('impeccable')
            library.install_curated('impeccable')
            persisted = SkillLibrary(Config(Path(raw)))
            loaded = persisted.read('impeccable')
            self.assertIn('craft-floor.md', ' '.join(loaded['resources']))
            self.assertIn('original text', loaded['note'].lower())
            self.assertEqual(persisted.explicit('$impeccable')[0]['name'], 'impeccable')
            self.assertEqual(persisted.matching('Hello, how are you?'), [])
            self.assertIn('impeccable', {e['id'] for e in persisted.matching('$impeccable improve the interface')})
            self.assertLessEqual(len(persisted.matching('$impeccable research document code review', limit=100)), 2)
            self.assertIn('contrast:', persisted.read('impeccable','reference/craft-floor.md')['content'].lower())
            persisted.set_enabled('impeccable', False)
            with self.assertRaises(ValueError):persisted.read('impeccable')
            persisted.remove('impeccable')
            self.assertFalse(any(e['id']=='impeccable' for e in persisted.entries()))
            self.assertTrue((persisted.curated_base()/'impeccable/SKILL.md').exists())

    def test_manifest_preserves_original_text_hashes_revisions_names_and_license_files(self):
        with tempfile.TemporaryDirectory() as raw:
            library = SkillLibrary(Config(Path(raw)))
            for record in library.curated_catalog():
                self.assertEqual(len(record['revision']),40)
                self.assertIn(record['revision'],record['source'])
                base=library.curated_base()/record['id']
                self.assertEqual(parse_skill((base/'SKILL.md').read_text())['name'], record['id'])
                self.assertIn('Apache License',(base/'LICENSE.txt').read_text())
                for relative, expected in record['files'].items():
                    self.assertEqual(hashlib.sha256((base/relative).read_bytes()).hexdigest(),expected)
                    self.assertNotIn('scripts/',relative)

    def test_curated_matching_requires_relevant_work_and_never_loads_every_available_guide(self):
        with tempfile.TemporaryDirectory() as raw:
            library=SkillLibrary(Config(Path(raw)))
            for entry in library.curated_catalog():library.install_curated(entry['id'])
            for request in ['Explain an Ethernet interface.', 'MCP server nedir?', 'Tema ne demek?', 'What is frontend?']:
                self.assertFalse(any(e.get('curated') for e in library.matching(request)),request)
            self.assertIn('mcp-builder',{e['id'] for e in library.matching('Create an MCP server for our API.')})
            self.assertIn('impeccable',{e['id'] for e in library.matching('Arayüz tasarımını iyileştir.')})
            self.assertEqual(library.matching('Hello!'),[])

    def test_frozen_bundle_is_used_instead_of_user_data_and_tampering_rejects_activation(self):
        with tempfile.TemporaryDirectory() as raw:
            root=Path(raw); bundle=root/'bundle'; app=root/'data'
            shutil.copytree(ROOT/'extensions/skills',bundle/'extensions/skills')
            with patch.object(sys,'_MEIPASS',str(bundle),create=True):
                library=SkillLibrary(Config(app))
                self.assertEqual(library.curated_base(),bundle/'extensions/skills')
                altered=bundle/'extensions/skills/impeccable/reference/craft-floor.md'
                altered.write_text('Tampered guide')
                with self.assertRaises(ValueError):library.install_curated('impeccable')
                self.assertNotIn('impeccable',library.config.settings.skill_enabled)
                with self.assertRaises(ValueError):library.read('impeccable','../frontend-design/SKILL.md',require_enabled=False)
