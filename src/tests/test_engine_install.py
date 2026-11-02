import io
import json
import tarfile
import stat
import tempfile
import threading
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

import httpx
from ai_studio.engine.install import unpack, install_engine, default_binary, engine_options
from ai_studio.engine.local import LocalEngine
from ai_studio.config import Config


def archive(path, unsafe=False):
    with tarfile.open(path,'w:gz') as tar:
        for name,data in [('package/llama-server',b'engine'),('package/libllama.so.1',b'library')]:
            member=tarfile.TarInfo(name);member.size=len(data);tar.addfile(member,io.BytesIO(data))
        link=tarfile.TarInfo('package/libllama.so');link.type=tarfile.SYMTYPE
        link.linkname='../../private' if unsafe else 'libllama.so.1';tar.addfile(link)


class InstallTests(unittest.TestCase):
    def test_private_libraries_internal_links_and_escape_rejection(self):
        with tempfile.TemporaryDirectory() as raw:
            root=Path(raw);(root/'safe').mkdir();(root/'unsafe').mkdir()
            archive(root/'a.tar.gz');binary=unpack(root/'a.tar.gz',root/'safe',threading.Event())
            self.assertEqual(binary.read_bytes(),b'engine')
            link=root/'safe/libllama.so'
            self.assertFalse(link.is_symlink());self.assertEqual(link.read_bytes(),b'library')
            archive(root/'a.tar.gz',unsafe=True)
            with self.assertRaises(ValueError):unpack(root/'a.tar.gz',root/'unsafe',threading.Event())
            self.assertFalse((root/'private').exists())

    def test_corrupt_package_never_publishes_engine(self):
        with tempfile.TemporaryDirectory() as raw:
            root=Path(raw)
            option={'path':str(root/'engine/bin/cpu/llama-server'),'package':{'version':'test','backend':'cpu','asset':'test.tar.gz','size':3,'sha256':'0'*64}}
            transport=httpx.MockTransport(lambda request:httpx.Response(200,content=b'bad'))
            client=httpx.Client(transport=transport)
            with patch('ai_studio.engine.install.httpx.Client',return_value=client):
                with self.assertRaisesRegex(ValueError,'SHA-256'):install_engine(root,option,threading.Event())
            self.assertFalse((root/'engine/bin/cpu').exists())
            self.assertEqual(list((root/'engine/bin').iterdir()),[])

    def test_default_discovers_app_managed_engine(self):
        with tempfile.TemporaryDirectory() as raw:
            root=Path(raw);binary=root/'engine/bin/cpu/llama-server';binary.parent.mkdir(parents=True);binary.write_text('test')
            self.assertEqual(default_binary(root),binary)
            self.assertEqual(LocalEngine(Config(root)).binary(),binary)

    def test_corrupt_cuda_runtime_never_publishes_engine(self):
        import hashlib
        with tempfile.TemporaryDirectory() as raw:
            root=Path(raw);archive(root/'main.tar.gz');data=(root/'main.tar.gz').read_bytes()
            package={'version':'test','backend':'cuda','asset':'main.tar.gz','size':len(data),'sha256':hashlib.sha256(data).hexdigest(),
                     'runtime':{'asset':'runtime.tar.gz','size':3,'sha256':'0'*64}}
            option={'path':str(root/'engine/bin/cuda/llama-server'),'package':package}
            transport=httpx.MockTransport(lambda request:httpx.Response(200,content=data if request.url.path.endswith('main.tar.gz') else b'bad'))
            original=httpx.Client
            with patch('ai_studio.engine.install.httpx.Client',side_effect=lambda **kw:original(transport=transport,**kw)):
                with self.assertRaisesRegex(ValueError,'SHA-256'):install_engine(root,option,threading.Event())
            self.assertFalse((root/'engine/bin/cuda').exists())

    def test_windows_zip_keeps_server_dlls_and_omits_other_executables(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            files = root / 'files'; files.mkdir()
            with zipfile.ZipFile(root / 'engine.zip', 'w') as archive:
                archive.writestr('llama/llama-server.exe', b'MZserver')
                archive.writestr('llama/ggml-cpu.dll', b'MZlibrary')
                archive.writestr('llama/llama-cli.exe', b'MZnot-needed')
                archive.writestr('LICENSE.txt', b'license')
            binary = unpack(root / 'engine.zip', files, threading.Event())
            self.assertEqual(binary.name, 'llama-server.exe')
            self.assertEqual({p.name for p in files.iterdir()}, {'llama-server.exe', 'ggml-cpu.dll'})

    def test_windows_zip_rejects_traversal_links_collisions_and_oversize(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            cases = [('unix-escape', '../outside.dll'), ('backslash-escape', '..\\outside.dll'),
                     ('drive', 'C:/outside.dll'), ('ads', 'folder.dll:secret'), ('absolute', '/outside.dll'),
                     ('reserved', 'CON.dll')]
            for title, unsafe in cases:
                with self.subTest(title=title):
                    files = root / title; files.mkdir()
                    with zipfile.ZipFile(root / 'engine.zip', 'w') as archive:
                        archive.writestr(unsafe, b'bad')
                    with self.assertRaisesRegex(ValueError, 'güvenli olmayan'):
                        unpack(root / 'engine.zip', files, threading.Event())
            files = root / 'links'; files.mkdir()
            with zipfile.ZipFile(root / 'engine.zip', 'w') as archive:
                link = zipfile.ZipInfo('symlink.dll')
                link.external_attr = (stat.S_IFLNK | 0o777) << 16
                archive.writestr(link, '../outside')
            with self.assertRaisesRegex(ValueError, 'bağlantı'):
                unpack(root / 'engine.zip', files, threading.Event())
            files = root / 'collisions'; files.mkdir()
            with zipfile.ZipFile(root / 'engine.zip', 'w') as archive:
                archive.writestr('first/GGML.dll', b'first')
                archive.writestr('second/ggml.dll', b'second')
            with self.assertRaisesRegex(ValueError, 'yinelenen'):
                unpack(root / 'engine.zip', files, threading.Event())
            files = root / 'oversize'; files.mkdir()
            with zipfile.ZipFile(root / 'engine.zip', 'w') as archive:
                archive.writestr('llama-server.exe', b'MZ' + b'x' * 100)
            with self.assertRaisesRegex(ValueError, 'boyut sınırını'):
                unpack(root / 'engine.zip', files, threading.Event(), size_limit=20)
            self.assertFalse((root / 'outside.dll').exists())

    def test_windows_manifest_and_exe_default_discovery(self):
        manifest = json.loads((Path(__file__).resolve().parents[2] / 'engine/releases.json').read_text())
        with tempfile.TemporaryDirectory() as raw, patch('ai_studio.engine.install.platform.system', return_value='Windows'), patch('ai_studio.engine.install.platform.machine', return_value='AMD64'):
            root = Path(raw)
            (root / 'engine').mkdir()
            (root / 'engine/releases.json').write_text(json.dumps(manifest))
            options = engine_options(root)
            self.assertEqual({o['package']['backend'] for o in options if o.get('package')}, {'cpu', 'vulkan', 'cuda'})
            self.assertTrue(all(o['path'].endswith('llama-server.exe') for o in options if o.get('package')))
            binary = root / 'engine/bin/vulkan/llama-server.exe'
            binary.parent.mkdir(parents=True); binary.write_bytes(b'MZtest')
            self.assertEqual(default_binary(root), binary)

    def test_windows_install_publishes_only_after_hash_runtime_and_executable_check(self):
        import hashlib
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            with zipfile.ZipFile(root / 'main.zip', 'w') as archive:
                archive.writestr('package/llama-server.exe', b'MZserver')
                archive.writestr('package/ggml-cuda.dll', b'MZggml')
            with zipfile.ZipFile(root / 'runtime.zip', 'w') as archive:
                archive.writestr('cublas64_12.dll', b'MZcublas')
            main, runtime = (root / 'main.zip').read_bytes(), (root / 'runtime.zip').read_bytes()
            package = {'version': 'test', 'backend': 'cuda', 'asset': 'main.zip', 'size': len(main),
                       'sha256': hashlib.sha256(main).hexdigest(), 'runtime': {'asset': 'runtime.zip',
                        'size': len(runtime), 'sha256': hashlib.sha256(runtime).hexdigest()}}
            option = {'path': str(root / 'engine/bin/cuda/llama-server.exe'), 'package': package}
            transport = httpx.MockTransport(lambda request: httpx.Response(200, content=main if request.url.path.endswith('main.zip') else runtime))
            original = httpx.Client
            with patch('ai_studio.engine.install.httpx.Client', side_effect=lambda **kw: original(transport=transport, **kw)), patch('ai_studio.engine.install.subprocess.run') as check:
                check.return_value.returncode = 0
                result = install_engine(root, option, threading.Event())
                self.assertEqual(Path(result).name, 'llama-server.exe')
                self.assertEqual(check.call_args[0][0][-1], '--version')
            self.assertTrue((root / 'engine/bin/cuda/cublas64_12.dll').is_file())
            self.assertTrue((root / 'engine/bin/cuda/build-info.json').is_file())
            self.assertEqual([p.name for p in (root / 'engine/bin').iterdir()], ['cuda'])

    def test_windows_executable_failure_never_publishes_or_overwrites_engine(self):
        import hashlib
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            with zipfile.ZipFile(root / 'main.zip', 'w') as archive:
                archive.writestr('llama-server.exe', b'MZinvalid-or-missing-runtime')
            data = (root / 'main.zip').read_bytes()
            option = {'path': str(root / 'engine/bin/cpu/llama-server.exe'), 'package': {
                'version': 'test', 'backend': 'cpu', 'asset': 'main.zip', 'size': len(data),
                'sha256': hashlib.sha256(data).hexdigest()}}
            original = httpx.Client
            transport = httpx.MockTransport(lambda request: httpx.Response(200, content=data))
            with patch('ai_studio.engine.install.httpx.Client', side_effect=lambda **kw: original(transport=transport, **kw)), patch('ai_studio.engine.install.subprocess.run') as check:
                check.return_value.returncode = 1
                with self.assertRaisesRegex(ValueError, 'bu sistemde çalışamadı'):
                    install_engine(root, option, threading.Event())
            self.assertFalse((root / 'engine/bin/cpu').exists())
            self.assertEqual(list((root / 'engine/bin').iterdir()), [])
