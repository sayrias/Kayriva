import json
from pathlib import Path
import tempfile
import unittest

from ai_studio.model_import import resolve_model_path, discover_local_models, find_projector, model_file_filter


class ModelImportTests(unittest.TestCase):
    def test_pasted_uri_quoted_relative_and_uppercase_paths(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            path = root / 'Türkçe model #1.GGUF'
            path.write_bytes(b'GGUF' + b'weights')
            for value in (path.as_uri(), f'"{path}"', path.name):
                selected = resolve_model_path(value, root)
                self.assertEqual(selected.path, path)
                self.assertEqual(selected.backend, 'gguf')
            self.assertIn('*.GGUF', model_file_filter())
            self.assertIn('Tüm dosyalar (*)', model_file_filter())

    def test_missing_archive_invalid_and_remote_paths_have_explanations(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            for name, text in [('not-model.gguf', 'GGUF biçiminde değil'), ('model.zip', 'arşiv')]:
                path = root / name
                path.write_bytes(b'not model')
                with self.assertRaisesRegex(ValueError, text):
                    resolve_model_path(path)
            with self.assertRaisesRegex(ValueError, 'bulunamadı'):
                resolve_model_path(root / 'missing.gguf')
            with self.assertRaisesRegex(ValueError, 'yerel|bilgisayarındaki'):
                resolve_model_path('https://example.com/model.gguf')
            with self.assertRaisesRegex(ValueError, 'bu bilgisayardaki'):
                resolve_model_path('file://other-machine/model.gguf')

    def test_safetensors_config_or_weights_select_directory_and_missing_parts_fail(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / 'config.json').write_text(json.dumps({'model_type': 'qwen3'}))
            weight = root / 'model-00001-of-00002.safetensors'
            weight.write_bytes(b'fake weights; loader not invoked')
            (root / 'tokenizer.json').write_text('{}')
            index = root / 'model.safetensors.index.json'
            index.write_text(json.dumps({'weight_map': {'first': weight.name, 'second': 'model-00002-of-00002.safetensors'}}))
            with self.assertRaisesRegex(ValueError, 'parçaları eksik'):
                resolve_model_path(root)
            (root / 'model-00002-of-00002.safetensors').write_bytes(b'weights')
            for path in (root, root / 'config.json', weight):
                model = resolve_model_path(path)
                self.assertEqual(model.path, root)
                self.assertEqual(model.backend, 'transformers')

    def test_projectors_are_matched_and_never_chosen_as_chat_models(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            model = root / 'Qwen3.5-4B-Q4_K_M.GGUF'
            projector = root / 'mmproj-Qwen3.5-4B-F16.gguf'
            other = root / 'mmproj-Gemma3-4B-F16.gguf'
            for path in (model, projector, other):
                path.write_bytes(b'GGUFweights')
            self.assertEqual(find_projector(model), projector)
            self.assertEqual(resolve_model_path(root).path, model)
            self.assertEqual(resolve_model_path(model).projector, projector)
            with self.assertRaisesRegex(ValueError, 'yardımcı'):
                resolve_model_path(projector)
            self.assertEqual([m.path for m in discover_local_models(root)], [model])

    def test_split_files_resolve_first_piece_only_when_complete(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            first = root / 'model-Q4_K_M-00001-of-00002.gguf'
            second = root / 'model-Q4_K_M-00002-of-00002.gguf'
            first.write_bytes(b'GGUFweights')
            with self.assertRaisesRegex(ValueError, 'parçaları eksik'):
                resolve_model_path(first)
            second.write_bytes(b'GGUFweights')
            self.assertEqual(resolve_model_path(second).path, first)

    def test_importing_does_not_modify_copy_or_rename_user_file(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            path = root / 'extensionless-model'
            path.write_bytes(b'GGUFtest')
            before = path.stat().st_mtime_ns
            self.assertEqual(resolve_model_path(path).path, path)
            self.assertEqual(path.stat().st_mtime_ns, before)
            self.assertEqual(list(root.iterdir()), [path])
