import json
import re
import unittest
from pathlib import Path
from ai_studio.model_library import assess, matches


class ModelLibraryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.models = json.loads((cls.root/'models/catalog.json').read_text())

    def find(self, id):
        return next(m for m in self.models if m['id'] == id)

    def test_27b_is_hybrid_and_changes_with_available_hardware(self):
        model = self.find('qwen38-27b-iq2xxs')
        self.assertEqual(assess(model,16,6).label, 'RAM + GPU')
        self.assertTrue(assess(model,16,6).recommended)
        self.assertFalse(assess(model,8,2).recommended)
        self.assertEqual(assess(model,16,0).label, 'CPU + RAM')

    def test_extreme_compression_is_browsable_but_not_recommended(self):
        model = self.find('qwen38-27b-iq1s')
        self.assertFalse(matches(model,'recommended','',self.root,16,6))
        self.assertTrue(matches(model,'compact27','',self.root,16,6))
        self.assertIn('kalite', assess(model,16,6).reason)

    def test_large_quant_is_excluded_for_this_device(self):
        self.assertFalse(assess(self.find('qwen-27b-q4'),16,6).recommended)
        self.assertTrue(assess(self.find('qwen-4b-q4'),16,6).recommended)

    def test_catalog_integrity_and_different_licenses(self):
        self.assertEqual(len({m['id'] for m in self.models}),len(self.models))
        for model in self.models:
            self.assertEqual(Path(model['filename']).name,model['filename'])
            self.assertGreater(model['approx_gb'],0)
            self.assertIn(model['quality'],{'balanced','low','extreme'})
        self.assertEqual(self.find('gemma3-27b-iq2')['license'],'Gemma')

    def test_download_targets_cannot_overwrite_another_model_or_omit_split_parts(self):
        # Downloads share one directory, including on case-insensitive Windows
        # filesystems. A valid catalog must never map two models onto one file.
        names = [model['filename'].casefold() for model in self.models]
        self.assertEqual(len(names), len(set(names)))
        targets = [(model['repo'], model.get('remote_filename', model['filename']))
                   for model in self.models]
        self.assertEqual(len(targets), len(set(targets)))
        for model in self.models:
            remote = model.get('remote_filename', model['filename'])
            self.assertNotRegex(remote, r'-\d{5}-of-\d{5}\.gguf$')
            self.assertIsNotNone(re.fullmatch(r'[a-f0-9]{64}', model['sha256']))
            self.assertIsNotNone(re.fullmatch(r'[a-f0-9]{40}', model['verified_revision']))
            self.assertAlmostEqual(model['approx_gb'], model['size_bytes'] / 1e9, places=2)

    def test_nvidia_library_includes_small_and_large_models_with_source_licenses(self):
        models = [model for model in self.models if model.get('brand') == 'NVIDIA']
        self.assertTrue(any(model['params_b'] <= 4 and model['approx_gb'] < 3 for model in models))
        self.assertTrue(any(model['params_b'] >= 30 for model in models))
        self.assertTrue(any('reasoning' in model['capabilities'] for model in models))
        self.assertTrue(any('tools' in model['capabilities'] for model in models))
        for model in models:
            self.assertTrue(model['base_model'].startswith('nvidia/'))
            self.assertEqual(model['license_source'], 'https://huggingface.co/' + model['base_model'])
            self.assertNotIn(model['license'], {'', 'other', 'Apache 2.0'})
            self.assertNotIn('vision', model['capabilities'])
