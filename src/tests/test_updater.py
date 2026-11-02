import hashlib
import json
import os
from pathlib import Path
import shlex
import struct
import subprocess
import tempfile
import threading
import unittest
from unittest.mock import patch
import zlib

import httpx
from ai_studio import updater as u


def sha(data):
    return hashlib.sha256(data).hexdigest()


class UpdaterTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.repository = 'example/Kayriva'
        self.source = u.UpdateSource(self.repository)
        self.requests = []

    def tearDown(self):
        self.temp.cleanup()

    def release(self, version='1.0.0-beta.2', *, body=b'new executable', target=('linux', 'x86_64'), deltas=()):
        name = 'Kayriva-Setup.exe' if target[0] == 'windows' else 'Kayriva'
        url = f'https://github.com/{self.repository}/releases/download/v{version}/'
        row = {'name': name, 'size': len(body), 'sha256': sha(body), 'platform': target[0], 'arch': target[1],
               'kind': 'installer' if target[0] == 'windows' else 'portable', 'deltas': list(deltas)}
        manifest = {'schema': 1, 'version': version, 'files': [row]}
        assets = [{'name': x, 'size': len(body) if x == name else 100,
                   'browser_download_url': url + x, 'state': 'uploaded'} for x in [name, u.MANIFEST_NAME]]
        for delta in deltas:
            assets.append({'name': delta['name'], 'size': delta['size'], 'browser_download_url': url + delta['name']})
        release = {'tag_name': 'v' + version, 'prerelease': '-' in version, 'draft': False,
                   'html_url': f'https://github.com/{self.repository}/releases/tag/v{version}',
                   'body': 'Release notes', 'published_at': '2026-11-02T00:00:00Z', 'assets': assets}
        return release, manifest, url, body

    def client(self, packages, extra=None):
        def handle(request):
            self.requests.append(str(request.url))
            if request.url.host == 'api.github.com':
                return httpx.Response(200, json=[p[0] for p in packages])
            for release, manifest, prefix, body in packages:
                if str(request.url) == prefix + u.MANIFEST_NAME:
                    return httpx.Response(200, json=manifest)
                if str(request.url) == prefix + manifest['files'][0]['name']:
                    return httpx.Response(200, content=body)
            if extra:
                return extra(request)
            return httpx.Response(404)
        return httpx.Client(transport=httpx.MockTransport(handle))

    def check(self, packages, current='1.0.0-beta.1', **kwargs):
        with self.client(packages) as client:
            return u.check_for_updates(self.source, current, client=client, target=('linux', 'x86_64'), **kwargs)

    def test_semver_prerelease_order_and_stable_channel(self):
        versions = ['1.0.0-beta.10', '1.0.0-beta.2', '1.0.0', '1.0.1', '1.0.0-rc.1']
        self.assertEqual([v.text for v in sorted(map(u.Version, versions))],
                         ['1.0.0-beta.2', '1.0.0-beta.10', '1.0.0-rc.1', '1.0.0', '1.0.1'])
        self.assertIsNone(self.check([self.release('1.1.0-beta.2')], current='1.0.0'))
        self.assertEqual(self.check([self.release('1.1.0-beta.2')]).version, '1.1.0-beta.2')
        self.assertEqual(self.check([self.release('1.0.0')]).version, '1.0.0')
        self.assertIsNone(self.check([self.release('1.0.0-beta.1')]))
        with self.assertRaises(u.UpdateError):
            u.Version('1.0.0-beta.01')

    def test_unpublished_repository_and_unconfigured_source_are_readable(self):
        with httpx.Client(transport=httpx.MockTransport(lambda req: httpx.Response(404))) as client:
            with self.assertRaisesRegex(u.UpdateError, 'not been published'):
                u.check_for_updates(self.source, client=client)
        with self.assertRaises(u.UpdateNotConfiguredError):
            u.check_for_updates(u.UpdateSource(''))
        with self.assertRaises(u.UpdateError):
            u.check_for_updates(u.UpdateSource('../bad'))

    def test_wrong_platform_drafts_and_downgrades_are_ignored(self):
        package = self.release(target=('windows', 'x86_64'))
        self.assertIsNone(self.check([package]))
        package = self.release()
        package[0]['draft'] = True
        self.assertIsNone(self.check([package]))
        self.assertIsNone(self.check([self.release('0.3.0')]))

    def test_manifest_traversal_hash_version_and_repository_mismatches_fail_closed(self):
        for field, value in [('name', '../Kayriva'), ('sha256', '0' * 63), ('size', u.MAX_ASSET + 1)]:
            package = self.release()
            package[1]['files'][0][field] = value
            with self.subTest(field=field), self.assertRaises(u.UpdateError):
                self.check([package])
        package = self.release()
        package[1]['version'] = '9.0.0'
        with self.assertRaises(u.UpdateError):
            self.check([package])
        package = self.release()
        package[0]['assets'][0]['browser_download_url'] = 'https://github.com/evil/app/releases/download/v1/Kayriva'
        with self.assertRaises(u.UpdateError):
            self.check([package])

    def test_verified_download_reuses_cache_and_corrupt_transfer_never_replaces_stage(self):
        package = self.release()
        with self.client([package]) as client:
            info = u.check_for_updates(self.source, client=client, target=('linux', 'x86_64'))
            progress = []
            path = u.download_update(info, self.root, lambda done, total: progress.append((done, total)), client=client)
            self.assertEqual(path.read_bytes(), package[3])
            before = len(self.requests)
            self.assertEqual(u.download_update(info, self.root, client=client), path)
            self.assertEqual(len(self.requests), before)
            self.assertTrue(progress)
        path.unlink()
        with httpx.Client(transport=httpx.MockTransport(lambda req: httpx.Response(200, content=b'wrong'))) as client:
            with self.assertRaises(u.UpdateError):
                u.download_update(info, self.root, client=client)
        self.assertFalse(path.exists())
        self.assertFalse(list(self.root.glob('*.part')))

    def test_cancellation_and_untrusted_redirect_do_not_leave_downloads(self):
        package = self.release()
        info = self.check([package])
        cancel = threading.Event()
        cancel.set()
        with self.client([package]) as client, self.assertRaises(InterruptedError):
            u.download_update(info, self.root, cancel=cancel, client=client)
        def redirect(req):
            return httpx.Response(302, headers={'Location': 'https://127.0.0.1/private'})
        with httpx.Client(transport=httpx.MockTransport(redirect)) as client, self.assertRaises(u.UpdateError):
            u.download_update(info, self.root, client=client)
        self.assertFalse(list(self.root.glob('*.part')))

    def test_delta_roundtrip_needs_exact_base_and_target_and_bounds_literals(self):
        base = self.root / 'base'
        target = self.root / 'target'
        base.write_bytes(os.urandom(u.BLOCK_SIZE * 3))
        target.write_bytes(base.read_bytes()[:u.BLOCK_SIZE] + b'x' * u.BLOCK_SIZE + base.read_bytes()[u.BLOCK_SIZE * 2:])
        patch_path = self.root / 'change.kdelta'
        metadata = u.build_delta(base, target, patch_path)
        destination = self.root / 'result'
        u.apply_delta(base, patch_path, destination, expected_base=metadata['from_sha256'],
                      expected_target=u.file_sha256(target), expected_size=target.stat().st_size)
        self.assertEqual(destination.read_bytes(), target.read_bytes())
        self.assertLess(patch_path.stat().st_size, target.stat().st_size / 3)
        base.write_bytes(b'changed')
        with self.assertRaises(u.UpdateError):
            u.apply_delta(base, patch_path, destination, expected_base=metadata['from_sha256'],
                          expected_target=u.file_sha256(target), expected_size=target.stat().st_size)
        header = {'schema': 1, 'base_sha256': u.file_sha256(base), 'target_sha256': sha(b'x'), 'target_size': 1,
                  'ops': [['data', 1, len(zlib.compress(b'x' * 100000))]]}
        encoded = json.dumps(header).encode()
        patch_path.write_bytes(u.DELTA_MAGIC + struct.pack('>I', len(encoded)) + encoded + zlib.compress(b'x' * 100000))
        with self.assertRaisesRegex(u.UpdateError, 'decompression exceeded'):
            u.apply_delta(base, patch_path, destination, expected_base=u.file_sha256(base), expected_target=sha(b'x'), expected_size=1)
        self.assertEqual(destination.read_bytes(), target.read_bytes())

    def test_corrupt_delta_falls_back_to_full_and_cached_installer_can_be_the_base(self):
        base = self.root / '1.0.0-beta.1-Kayriva-Setup.exe'
        base.write_bytes(b'a' * u.BLOCK_SIZE)
        target = b'a' * u.BLOCK_SIZE + b'new'
        patch_data = b'corrupt'
        delta = {'name': 'change.kdelta', 'size': len(patch_data), 'sha256': sha(patch_data),
                 'from_version': '1.0.0-beta.1', 'from_sha256': u.file_sha256(base), 'algorithm': 'kayriva-block-v1'}
        package = self.release(body=target, target=('windows', 'x86_64'), deltas=[delta])
        with self.client([package], lambda req: httpx.Response(200, content=patch_data)) as client:
            info = u.check_for_updates(self.source, client=client, target=('windows', 'x86_64'))
            result = u.download_update(info, self.root, current_version='1.0.0-beta.1', client=client)
        self.assertEqual(result.read_bytes(), target)
        self.assertTrue(any(url.endswith('change.kdelta') for url in self.requests))

    def test_manifest_builder_publishes_useful_delta_only(self):
        base, target = self.root / 'old', self.root / 'Kayriva'
        base.write_bytes(os.urandom(u.BLOCK_SIZE * 3))
        target.write_bytes(base.read_bytes()[:-3] + b'new')
        output = self.root / u.MANIFEST_NAME
        data = u.generate_manifest('1.0.0-beta.2', [('linux', 'x86_64', 'portable', target)], output,
                                   previous={('linux', 'x86_64'): ('1.0.0-beta.1', base)})
        self.assertTrue(data['files'][0]['deltas'])
        target.write_bytes(os.urandom(u.BLOCK_SIZE * 3))
        data = u.generate_manifest('1.0.0-beta.2', [('linux', 'x86_64', 'portable', target)], output,
                                   previous={('linux', 'x86_64'): ('1.0.0-beta.1', base)})
        self.assertNotIn('deltas', data['files'][0])

    def test_valid_delta_download_reconstructs_without_requesting_full_binary(self):
        base, new = self.root / 'installed', self.root / 'new'
        base.write_bytes(os.urandom(u.BLOCK_SIZE * 3))
        new.write_bytes(base.read_bytes()[:-5] + b'hello')
        patch_path = self.root / 'useful.kdelta'
        delta = u.build_delta(base, new, patch_path)
        delta['from_version'] = '1.0.0-beta.1'
        patch_bytes = patch_path.read_bytes()
        package = self.release(body=new.read_bytes(), deltas=[delta])
        with self.client([package], lambda req: httpx.Response(200, content=patch_bytes)) as client:
            info = u.check_for_updates(self.source, client=client, target=('linux', 'x86_64'))
            result = u.download_update(info, self.root, base_path=base, current_version='1.0.0-beta.1', client=client)
        self.assertEqual(result.read_bytes(), new.read_bytes())
        self.assertNotIn(package[2] + 'Kayriva', self.requests)

    def test_delta_cancellation_propagates_without_warning_or_full_fallback(self):
        base = self.root / 'installed'
        base.write_bytes(b'old executable')
        delta = {'name': 'change.kdelta', 'size': 1, 'sha256': sha(b'x'),
                 'from_version': '1.0.0-beta.1', 'from_sha256': u.file_sha256(base),
                 'algorithm': 'kayriva-block-v1'}
        package = self.release(body=b'new executable', deltas=[delta])
        info = self.check([package])
        with self.client([package]) as client, patch.object(u, '_download', side_effect=InterruptedError('cancel')) as download:
            with patch.object(u.LOG, 'warning') as warning, self.assertRaises(InterruptedError):
                u.download_update(info, self.root, base_path=base,
                                  current_version='1.0.0-beta.1', client=client)
            download.assert_called_once()
            warning.assert_not_called()

    @unittest.skipUnless(u.host_target()[0] == 'linux', 'Linux portable replacement helper')
    def test_linux_helper_replaces_after_exit_and_rolls_back_failed_start(self):
        for fail_start in (False, True):
            with self.subTest(fail_start=fail_start):
                folder = self.root / ("test 'quoted' " + str(fail_start))
                folder.mkdir()
                executable, staged, marker = folder / 'Kayriva', folder / 'stage', folder / 'marker'
                old = '#!/bin/sh\nprintf old > ' + shlex.quote(str(marker)) + '\n'
                new = '#!/bin/sh\nexit 42\n' if fail_start else '#!/bin/sh\nprintf new > ' + shlex.quote(str(marker)) + '\n'
                executable.write_text(old)
                executable.chmod(0o700)
                staged.write_text(new)
                package = self.release(body=staged.read_bytes())
                info = self.check([package])
                with patch.object(u.os, 'getpid', return_value=2147483647), patch.object(u.subprocess, 'Popen') as popen:
                    u.launch_update(info, staged, current_executable=executable)
                command = popen.call_args.args[0]
                subprocess.run(command, check=True, timeout=10, env=popen.call_args.kwargs['env'])
                self.assertEqual(executable.read_text(), old if fail_start else new)
                self.assertEqual(marker.read_text(), 'old' if fail_start else 'new')

    def test_apply_refuses_source_and_tampered_stage_before_spawning(self):
        package = self.release()
        info = self.check([package])
        stage, executable = self.root / 'stage', self.root / 'installed'
        stage.write_bytes(b'tampered')
        executable.write_bytes(b'old')
        with patch.object(u.subprocess, 'Popen') as popen:
            with self.assertRaisesRegex(u.UpdateError, 'Source installations'):
                u.launch_update(info, stage)
            with self.assertRaisesRegex(u.UpdateError, 'has changed'):
                u.launch_update(info, stage, current_executable=executable)
            popen.assert_not_called()
        stage.write_bytes(package[3])
        with patch.object(u, 'host_target', return_value=('linux', 'x86_64')), patch.object(u.subprocess, 'Popen') as popen:
            result = u.launch_update(info, stage, current_executable=executable)
        self.assertTrue(result.requires_exit)
        self.assertEqual(executable.read_bytes(), b'old')
        arguments = popen.call_args.args[0]
        self.assertIn('kill -0', arguments[2])
        self.assertIn('mv -f -- "$backup" "$target"', arguments[2])
        self.assertEqual(popen.call_args.kwargs['env']['PYINSTALLER_RESET_ENVIRONMENT'], '1')
