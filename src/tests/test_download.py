import hashlib
import json
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

import httpx

from ai_studio.engine.download import download_model


class DownloadTests(unittest.TestCase):
    def fixture(self, payload):
        digest = hashlib.sha256(payload).hexdigest()
        model = {"repo": "test/model", "filename": "model.gguf"}
        metadata = {"sha": "revision", "siblings": [{"rfilename": "model.gguf", "size": len(payload), "lfs": {"sha256": digest, "size": len(payload)}}]}
        return model, metadata

    def run_mock(self, directory, payload, resume=False, corrupt=False, ignore_range=False):
        model, metadata = self.fixture(payload)
        seen = []
        def handler(request):
            if "/api/models/" in str(request.url):
                return httpx.Response(200, json=metadata)
            seen.append(request)
            body = b"bad!" + payload[4:] if corrupt else payload
            if resume and not ignore_range:
                self.assertEqual(request.headers["range"], "bytes=9-")
                return httpx.Response(206, headers={"Content-Range": f"bytes 9-{len(body)-1}/{len(body)}"}, content=body[9:])
            return httpx.Response(200, content=body)
        original = httpx.Client
        with patch("ai_studio.engine.download.httpx.Client", side_effect=lambda **kw: original(transport=httpx.MockTransport(handler), **kw)):
            result = download_model(model, directory, threading.Event())
        return result, seen

    def test_verified_download_published_and_commit_pinned(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            payload = b"GGUF" + b"test-weight" * 100
            path, requests = self.run_mock(root, payload)
            self.assertEqual(path.read_bytes(), payload)
            self.assertIn("/resolve/revision/", str(requests[0].url))
            self.assertFalse((root / "model.gguf.part").exists())
            self.assertTrue((root / "model.gguf.metadata.json").exists())

    def test_resume_and_server_ignoring_range(self):
        for ignores in [False, True]:
            with self.subTest(ignores=ignores), tempfile.TemporaryDirectory() as raw:
                root = Path(raw)
                payload = b"GGUF" + b"test-weight" * 100
                model, meta = self.fixture(payload)
                info = {"repo": "test/model", "filename": "model.gguf", "revision": "revision", "sha256": meta["siblings"][0]["lfs"]["sha256"], "size": len(payload)}
                (root / "model.gguf.part").write_bytes(payload[:9])
                (root / "model.gguf.part.json").write_text(json.dumps(info))
                path, _ = self.run_mock(root, payload, resume=True, ignore_range=ignores)
                self.assertEqual(path.read_bytes(), payload)

    def test_corrupt_download_never_becomes_loadable(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            with self.assertRaises(ValueError):
                self.run_mock(root, b"GGUF" + b"weights" * 100, corrupt=True)
            self.assertFalse((root / "model.gguf").exists())
            self.assertFalse((root / "model.gguf.part").exists())

    def test_tls_retry_has_bounded_attempts_and_clear_failure(self):
        with tempfile.TemporaryDirectory() as raw:
            model,_=self.fixture(b'GGUFtest')
            calls=[]
            def handler(request):
                calls.append(request)
                raise httpx.ConnectError('SSL EOF',request=request)
            original=httpx.Client
            with patch('ai_studio.engine.download.pause'), patch('ai_studio.engine.download.httpx.Client', side_effect=lambda **kw: original(transport=httpx.MockTransport(handler), **kw)):
                with self.assertRaisesRegex(RuntimeError,'Güvenli bağlantı'):
                    download_model(model,Path(raw),threading.Event())
            self.assertEqual(len(calls),4)
            self.assertFalse((Path(raw)/model['filename']).exists())

    def test_interrupted_stream_resumes_with_verified_range(self):
        payload=b'GGUF'+b'weight'*300000
        model,meta=self.fixture(payload)
        seen=[]
        class BrokenStream(httpx.SyncByteStream):
            def __iter__(self):
                yield payload[:1_250_000]
                raise httpx.ReadError('SSL EOF')
        # More than one chunk reaches disk before EOF; retry must resume its exact offset.
        original=httpx.Client
        def handler(request):
            if '/api/models/' in str(request.url): return httpx.Response(200,json=meta)
            seen.append(request)
            if len(seen)==1: return httpx.Response(200,stream=BrokenStream())
            self.assertEqual(request.headers.get('range'),'bytes=1048576-')
            offset=int(request.headers.get('range','bytes=0-')[6:-1])
            return httpx.Response(206,headers={'Content-Range':f'bytes {offset}-{len(payload)-1}/{len(payload)}'},content=payload[offset:]) if offset else httpx.Response(200,content=payload)
        with tempfile.TemporaryDirectory() as raw, patch('ai_studio.engine.download.pause'), patch('ai_studio.engine.download.httpx.Client',side_effect=lambda **kw: original(transport=httpx.MockTransport(handler),**kw)):
            path=download_model(model,Path(raw),threading.Event())
            self.assertEqual(path.read_bytes(),payload)
            self.assertEqual(len(seen),2)

    def test_hash_progress_and_cancel_preserve_download(self):
        from ai_studio.engine.download import digest
        payload=b'GGUF'+b'x'*1000
        with tempfile.TemporaryDirectory() as raw:
            root=Path(raw)
            path,_=self.run_mock(root,payload)
            progress=[]
            self.assertEqual(digest(path,progress=lambda a,b:progress.append((a,b))),hashlib.sha256(payload).hexdigest())
            self.assertEqual(progress[-1],(len(payload),len(payload)))
            cancel=threading.Event(); cancel.set()
            with self.assertRaises(InterruptedError): digest(path,cancel)
            self.assertTrue(path.exists())

    def test_cached_manifest_skips_metadata_after_interruption(self):
        payload=b'GGUF'+b'x'*100
        model,meta=self.fixture(payload)
        with tempfile.TemporaryDirectory() as raw:
            root=Path(raw)
            info={'repo':model['repo'],'filename':model['filename'],'revision':meta['sha'],'sha256':meta['siblings'][0]['lfs']['sha256'],'size':len(payload)}
            (root/'model.gguf.part.json').write_text(json.dumps(info))
            (root/'model.gguf.part').write_bytes(payload)
            with patch('ai_studio.engine.download.metadata_info',side_effect=AssertionError('Metadata must not be refetched')):
                path=download_model(model,root,threading.Event())
            self.assertEqual(path.read_bytes(),payload)


    def test_metadata_cancel_and_http_permissions_are_not_retried(self):
        model,meta=self.fixture(b'GGUFtest')
        original=httpx.Client
        for code in [403,404]:
            seen=[]
            def handler(request):
                seen.append(request)
                return httpx.Response(code)
            with tempfile.TemporaryDirectory() as raw, patch('ai_studio.engine.download.httpx.Client',side_effect=lambda **kw:original(transport=httpx.MockTransport(handler),**kw)):
                with self.assertRaises(RuntimeError):download_model(model,Path(raw),threading.Event())
                self.assertEqual(len(seen),1)
        cancel=threading.Event(); cancel.set()
        with tempfile.TemporaryDirectory() as raw, patch('ai_studio.engine.download.metadata_info',side_effect=InterruptedError('Cancelled')):
            with self.assertRaises(InterruptedError): download_model(model,Path(raw),cancel)

    def test_repository_filename_cannot_escape_model_directory(self):
        with tempfile.TemporaryDirectory() as raw:
            with self.assertRaises(ValueError):
                download_model({"repo": "test/model", "filename": "../outside.gguf"}, Path(raw), threading.Event())

    def test_remote_folder_and_case_change_keep_local_filename_and_quant(self):
        payload = b'GGUFweights'
        model, meta = self.fixture(payload)
        meta['siblings'][0]['rfilename'] = 'Q4/MODEL.GGUF'
        requests = []
        original = httpx.Client
        def handler(request):
            requests.append(request)
            return httpx.Response(200, json=meta) if '/api/models/' in str(request.url) else httpx.Response(200, content=payload)
        with tempfile.TemporaryDirectory() as raw, patch('ai_studio.engine.download.httpx.Client', side_effect=lambda **kw: original(transport=httpx.MockTransport(handler), **kw)):
            path = download_model(model, Path(raw), threading.Event())
            self.assertEqual(path.name, 'model.gguf')
            self.assertIn('/resolve/revision/Q4/MODEL.GGUF', str(requests[-1].url))
            self.assertEqual(path.read_bytes(), payload)

    def test_removed_resume_commit_refreshes_and_does_not_mix_payloads(self):
        payload = b'GGUFnew weights'
        model, meta = self.fixture(payload)
        old = b'GGUFold weights'
        requests = []
        original = httpx.Client
        def handler(request):
            requests.append(request)
            if '/api/models/' in str(request.url):
                return httpx.Response(200, json=meta)
            if '/resolve/removed/' in str(request.url):
                return httpx.Response(404)
            self.assertNotIn('range', request.headers)
            return httpx.Response(200, content=payload)
        with tempfile.TemporaryDirectory() as raw, patch('ai_studio.engine.download.httpx.Client', side_effect=lambda **kw: original(transport=httpx.MockTransport(handler), **kw)):
            root = Path(raw)
            (root / 'model.gguf.part').write_bytes(old[:9])
            (root / 'model.gguf.part.json').write_text(json.dumps({'repo': model['repo'], 'filename': model['filename'],
                'revision': 'removed', 'sha256': hashlib.sha256(old).hexdigest(), 'size': len(old)}))
            result = download_model(model, root, threading.Event())
            self.assertEqual(result.read_bytes(), payload)
            self.assertEqual(len(requests), 3)

    def test_verified_existing_file_can_be_checked_offline(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            payload = b'GGUFweights'
            path, _ = self.run_mock(root, payload)
            model, _ = self.fixture(payload)
            with patch('ai_studio.engine.download.metadata_info', side_effect=AssertionError('No network needed')):
                self.assertEqual(download_model(model, root, threading.Event()), path)

    def test_missing_quant_never_substitutes_another_variant(self):
        payload = b'GGUFweights'
        model, meta = self.fixture(payload)
        meta['siblings'][0]['rfilename'] = 'different-Q8_0.gguf'
        original = httpx.Client
        with tempfile.TemporaryDirectory() as raw, patch('ai_studio.engine.download.httpx.Client', side_effect=lambda **kw: original(transport=httpx.MockTransport(lambda _: httpx.Response(200, json=meta)), **kw)):
            with self.assertRaisesRegex(ValueError, 'başka bir model otomatik seçilmedi'):
                download_model(model, Path(raw), threading.Event())
            self.assertFalse((Path(raw) / model['filename']).exists())

    def test_remote_filename_alias_has_separate_safe_local_name(self):
        payload = b'GGUFprojector'
        model, meta = self.fixture(payload)
        model.update(filename='mmproj-Qwen3.5-4B-F16.gguf', remote_filename='mmproj-F16.gguf')
        meta['siblings'][0]['rfilename'] = model['remote_filename']
        original = httpx.Client
        def handler(request):
            return httpx.Response(200, json=meta) if '/api/models/' in str(request.url) else httpx.Response(200, content=payload)
        with tempfile.TemporaryDirectory() as raw, patch('ai_studio.engine.download.httpx.Client', side_effect=lambda **kw: original(transport=httpx.MockTransport(handler), **kw)):
            path = download_model(model, Path(raw), threading.Event())
            self.assertEqual(path.name, model['filename'])
            self.assertEqual(path.read_bytes(), payload)


if __name__ == "__main__":
    unittest.main()
