"""Skill packages preserve user preferences without importing executable content."""
import json
import tempfile
import unittest
from pathlib import Path

from ai_studio.config import Config
from ai_studio.i18n import set_language
from ai_studio.skills import BUILTIN_SKILLS, MAX_READ_CHARACTERS, SkillLibrary, parse_skill


def package(root, content='Use concrete evidence.', name='interface-audit', description='Review interface hierarchy and contrast.'):
    root.mkdir(parents=True, exist_ok=True)
    path = root/'SKILL.md'
    path.write_text(f'---\nname: {name}\ndescription: {description}\n---\n{content}', encoding='utf-8')
    return path


class SkillTests(unittest.TestCase):
    def tearDown(self):
        set_language('en')

    def test_bundled_catalog_chooses_relevant_guides_only_in_both_languages(self):
        with tempfile.TemporaryDirectory() as raw:
            config = Config(Path(raw)); library = SkillLibrary(config)
            self.assertEqual(len(library.entries()), 8)
            self.assertEqual(library.matching('Hello, how are you?'), [])
            for request, expected in [('Research server platforms and write a report.', {'research','documents'}),
                                      ('Sunucu platformlarını araştır ve bir belge hazırla.', {'research','documents'}),
                                      ('Review code changes.', {'code-review'}),
                                      ('Arayüz tasarımını iyileştir.', {'ui-design'})]:
                self.assertEqual({entry['id'] for entry in library.matching(request)}, expected)
            config.settings.language='tr'
            self.assertEqual(library.read('research')['name'], 'Araştırma')
            library.set_enabled('research', False)
            reloaded = SkillLibrary(Config(Path(raw)))
            self.assertNotIn('research', {e['id'] for e in reloaded.matching('Research operating systems.')})
            with self.assertRaises(ValueError):
                reloaded.read('research')

    def test_explicit_skill_takes_priority_and_limit_is_two_even_when_larger_requested(self):
        with tempfile.TemporaryDirectory() as raw:
            library = SkillLibrary(Config(Path(raw)))
            result=library.matching('$writing $debugging research report code review planlama', limit=99)
            self.assertEqual([e['id'] for e in result], ['writing','debugging'])
            self.assertEqual(library.matching('$not-installed'), [])

    def test_import_copies_only_referenced_text_resources_and_survives_source_removal(self):
        with tempfile.TemporaryDirectory() as raw:
            root=Path(raw); config=Config(root/'app'); library=SkillLibrary(config)
            path=package(root/'incoming', 'Read [checks](references/checks.md), then inspect `scripts/run.py`.')
            (path.parent/'references').mkdir(); (path.parent/'scripts').mkdir()
            (path.parent/'references/checks.md').write_text('Review contrast. Read [extra](extra.json).')
            (path.parent/'references/extra.json').write_text('{"unit":"px"}')
            (path.parent/'scripts/run.py').write_text("raise RuntimeError('must never execute')")
            (path.parent/'unrelated.txt').write_text('Do not copy')
            entry=library.import_path(path.parent)
            path.unlink()
            loaded=SkillLibrary(Config(root/'app'))
            data=loaded.read(entry['id'])
            self.assertEqual(set(data['resources']), {'references/checks.md','references/extra.json'})
            self.assertIn('contrast', loaded.read(entry['id'],'references/checks.md')['content'])
            self.assertEqual(json.loads(loaded.read(entry['id'],'references/extra.json')['content']), {'unit':'px'})
            target=config.runtime/'skills'/entry['id']
            self.assertFalse((target/'scripts').exists()); self.assertFalse((target/'unrelated.txt').exists())
            self.assertEqual((target/'SKILL.md').stat().st_mode & 0o777,0o600)
            loaded.remove(entry['id'])
            self.assertNotIn(entry['id'], {item['id'] for item in loaded.entries()})

    def test_traversal_symlinks_hidden_credentials_and_scripts_cannot_be_read_as_resources(self):
        with tempfile.TemporaryDirectory() as raw:
            root=Path(raw); config=Config(root/'app'); library=SkillLibrary(config)
            outside=root/'outside.md'; outside.write_text('Outside private data')
            path=package(root/'incoming', '[a](../outside.md) [b](link.md) [c](.env.json) [d](secret.json) [e](run.py)')
            (path.parent/'link.md').symlink_to(outside)
            (path.parent/'.env.json').write_text('private'); (path.parent/'secret.json').write_text('private')
            entry=library.import_path(path)
            self.assertEqual(library.read(entry['id'])['resources'], [])
            for resource in ('../outside.md','link.md','.env.json','secret.json','run.py','/etc/passwd'):
                with self.assertRaises(ValueError, msg=resource): library.read(entry['id'],resource)
            link=root/'linked-package'; link.symlink_to(path.parent, target_is_directory=True)
            with self.assertRaises(ValueError): library.import_path(link/'SKILL.md')
            stored=config.runtime/'skills'/entry['id']/'SKILL.md'; stored.unlink(); stored.symlink_to(outside)
            with self.assertRaises(ValueError): library.read(entry['id'])

    def test_metadata_validation_and_integrity_hash_reject_changed_guides(self):
        for text in ('name: bad', '---\nname: "!evil"\ndescription: text\n---\nbody',
                     '---\nname: okay\nname: twice\ndescription: text\n---\nbody',
                     '---\nname: okay\ndescription: !!python/object:thing\n---\nbody'):
            with self.assertRaises(ValueError): parse_skill(text)
        parsed=parse_skill('---\nname: checks\ndescription: >-\n  Review concrete\n  examples.\n---\nInstructions')
        self.assertEqual(parsed['description'],'Review concrete examples.')
        with tempfile.TemporaryDirectory() as raw:
            root=Path(raw); config=Config(root/'app'); library=SkillLibrary(config)
            entry=library.import_path(package(root/'incoming', 'x'*(MAX_READ_CHARACTERS+10)))
            self.assertTrue(library.read(entry['id'])['limited'])
            (config.runtime/'skills'/entry['id']/'SKILL.md').write_text('changed')
            with self.assertRaises(ValueError): library.read(entry['id'])

    def test_nested_resources_and_package_limits_are_bounded(self):
        with tempfile.TemporaryDirectory() as raw:
            root=Path(raw); library=SkillLibrary(Config(root/'app'))
            path=package(root/'incoming','[large](large.md) [next](next.md)')
            (path.parent/'large.md').write_text('x'*70000)
            (path.parent/'next.md').write_text('[self](next.md)\nValid resource.')
            entry=library.import_path(path)
            data=library.read(entry['id'])
            self.assertEqual(data['resources'], ['next.md'])
            self.assertIn('large.md', data['missing_resources'])
            path=package(root/'another',' '.join(f'[part](part{i}.md)' for i in range(5)),name='bounded-guide')
            for i in range(5): (path.parent/f'part{i}.md').write_text('x'*60000)
            entry=library.import_path(path)
            data=library.read(entry['id'])
            self.assertEqual(len(data['resources']),4)
            self.assertEqual(data['missing_resources'],['part4.md'])
