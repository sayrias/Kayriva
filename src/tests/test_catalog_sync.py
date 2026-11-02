import hashlib
import json
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

import httpx

from ai_studio.catalog_sync import refresh_catalog, load_catalog


class CatalogSyncTests(unittest.TestCase):
    def fixture(self):
        model = {'id': 'model-q4', 'name': 'Model', 'repo': 'test/model', 'filename': 'Model-Q4.gguf',
                 'approx_gb': 4.2, 'capabilities': ['code'], 'brand': 'Example', 'revision': 'main'}
        file = {'rfilename': 'quant/Model-Q4.gguf', 'size': 1234,
                'lfs': {'sha256': hashlib.sha256(b'GGUF').hexdigest(), 'size': 1234}}
        return model, {'sha': 'commit-sha', 'siblings': [file]}

    def test_refresh_one_request_per_repo_keeps_identity_and_atomic_cache(self):
        model, metadata = self.fixture()
        another = {**model, 'id': 'other-entry'}
        seen = []
        def handler(request):
            seen.append(request)
            self.assertEqual(request.url.host, 'huggingface.co')
            self.assertEqual(request.url.params['blobs'], 'true')
            return httpx.Response(200, json=metadata)
        original = httpx.Client
        with tempfile.TemporaryDirectory() as raw, patch('ai_studio.catalog_sync.httpx.Client', side_effect=lambda **kw: original(transport=httpx.MockTransport(handler), **kw)):
            cache = Path(raw) / 'catalog-cache.json'
            result = refresh_catalog([model, another], cache)
            self.assertEqual((result.checked, result.available, len(result.errors)), (2, 2, 0))
            self.assertEqual(len(seen), 1)
            refreshed = load_catalog([model], cache)[0]
            self.assertEqual(refreshed['filename'], model['filename'])
            self.assertEqual(refreshed['remote_filename'], 'quant/Model-Q4.gguf')
            self.assertEqual(refreshed['verified_revision'], 'commit-sha')
            self.assertEqual(refreshed['capabilities'], ['code'])
            self.assertEqual(refreshed['size_bytes'], 1234)
            self.assertFalse(cache.with_suffix('.json.tmp').exists())

    def test_api_unavailable_preserves_known_metadata_and_distinguishes_removed(self):
        model, metadata = self.fixture()
        original = httpx.Client
        with tempfile.TemporaryDirectory() as raw:
            cache = Path(raw) / 'catalog-cache.json'
            with patch('ai_studio.catalog_sync.httpx.Client', side_effect=lambda **kw: original(transport=httpx.MockTransport(lambda _: httpx.Response(200, json=metadata)), **kw)):
                refresh_catalog([model], cache)
            def offline(request):
                raise httpx.ConnectError('offline', request=request)
            with patch('ai_studio.engine.download.pause'), patch('ai_studio.catalog_sync.httpx.Client', side_effect=lambda **kw: original(transport=httpx.MockTransport(offline), **kw)):
                result = refresh_catalog([model], cache)
            self.assertEqual(result.models[0]['availability'], 'unreachable')
            self.assertEqual(result.models[0]['size_bytes'], 1234)
            with patch('ai_studio.catalog_sync.httpx.Client', side_effect=lambda **kw: original(transport=httpx.MockTransport(lambda _: httpx.Response(404)), **kw)):
                result = refresh_catalog([model], cache)
            self.assertEqual(result.models[0]['availability'], 'unavailable')
            self.assertEqual(result.models[0]['filename'], model['filename'])

    def test_cache_cannot_override_curated_identity_capabilities_or_new_release(self):
        model, _ = self.fixture()
        with tempfile.TemporaryDirectory() as raw:
            cache = Path(raw) / 'cache.json'
            cache.write_text(json.dumps({'models': {model['id']: {**model, 'brand': 'Injected', 'capabilities': ['vision'],
                                                                  'remote_filename': 'new-path.gguf'}}}))
            loaded = load_catalog([model], cache)[0]
            self.assertEqual(loaded['brand'], model['brand'])
            self.assertEqual(loaded['capabilities'], ['code'])
            self.assertEqual(loaded['remote_filename'], 'new-path.gguf')
            changed_identity = {**model, 'repo': 'different/publisher'}
            self.assertNotIn('remote_filename', load_catalog([changed_identity], cache)[0])

    def test_cancel_does_not_publish_partial_catalog(self):
        model, _ = self.fixture()
        cancel = threading.Event()
        cancel.set()
        with tempfile.TemporaryDirectory() as raw:
            cache = Path(raw) / 'cache.json'
            cache.write_text('{"previous":true}')
            with self.assertRaises(InterruptedError):
                refresh_catalog([model], cache, cancel)
            self.assertEqual(cache.read_text(), '{"previous":true}')

    def test_cancel_returns_without_waiting_for_blocked_metadata_and_no_late_cache_write(self):
        model, metadata = self.fixture()
        cancel, release = threading.Event(), threading.Event()
        def blocked_metadata(*args, **kwargs):
            release.wait(2)
            return metadata
        timer = threading.Timer(.1, cancel.set)
        with tempfile.TemporaryDirectory() as raw:
            cache = Path(raw) / 'cache.json'
            cache.write_text('{"previous":true}')
            timer.start()
            started = time.monotonic()
            try:
                with patch('ai_studio.catalog_sync.repository_metadata', side_effect=blocked_metadata):
                    with self.assertRaises(InterruptedError):
                        refresh_catalog([model], cache, cancel)
                self.assertLess(time.monotonic() - started, .7)
                self.assertEqual(cache.read_text(), '{"previous":true}')
                release.set()
                time.sleep(.05)
                self.assertEqual(cache.read_text(), '{"previous":true}')
                self.assertFalse(cache.with_suffix('.json.tmp').exists())
            finally:
                release.set()
                timer.cancel()

    def test_catalog_schema_has_verified_diverse_models_and_honest_projector_requirements(self):
        models = json.loads((Path(__file__).resolve().parents[2] / 'models/catalog.json').read_text())
        self.assertGreaterEqual(len(models), 50)
        self.assertGreaterEqual(len({m['brand'] for m in models}), 8)
        self.assertTrue({'low', 'medium', 'high', 'very_high', 'ultra'}.issubset({m['tier'] for m in models}))
        for model in models:
            self.assertEqual(model['availability'], 'available')
            self.assertGreater(model['size_bytes'], 0)
            self.assertEqual(len(model['sha256']), 64)
            self.assertEqual(len(model['verified_revision']), 40)
            self.assertFalse(model['size_estimated'])
            if 'vision' in model['capabilities']:
                self.assertTrue(model['vision_requires_projector'])
                self.assertTrue(model['projector']['filename'].startswith('mmproj-'))
