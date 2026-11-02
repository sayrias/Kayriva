from urllib.parse import urlparse
import hashlib
import json
import subprocess
import tempfile
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from ai_studio.extension_library import ExtensionLibrary, load_catalog
from ai_studio.github_service import GitHubService, github_url, repository_name
from ai_studio.integrations import export_configuration, import_configuration


ROOT = Path(__file__).resolve().parents[2]


class IntegrationTests(unittest.TestCase):
    def test_catalog_sources_and_installers_are_explicit(self):
        entries = load_catalog(ROOT)
        self.assertGreaterEqual(len(entries), 17)
        self.assertEqual(len({entry['id'] for entry in entries}), len(entries))
        for entry in entries:
            self.assertIn(urlparse(entry['source']).hostname, {'github.com', 'docs.devin.ai', 'learn.microsoft.com', 'developers.cloudflare.com', 'huggingface.co'})
            self.assertTrue(entry['permissions'])

    def test_import_preserves_argv_without_running_and_disables_servers(self):
        with patch('subprocess.Popen') as popen:
            specs = import_configuration(json.dumps({'mcpServers': {'test': {'command': 'python', 'args': ['literal;$(touch bad)', 'file with spaces'], 'enabled': True}}}))
        popen.assert_not_called()
        self.assertFalse(specs[0]['enabled'])
        self.assertEqual(specs[0]['args'][0], 'literal;$(touch bad)')

    def test_bad_import_and_credential_url_are_rejected(self):
        for spec in ({'command': 'python', 'args': 'shell code'}, {'url': 'https://user:password@example.com/mcp'}, {'url': 'file:///tmp/test'}, {'url': 'https://example.com', 'header_env': {'Authorization': 'not a name'}}):
            with self.subTest(spec=spec):
                with self.assertRaises(ValueError):
                    import_configuration(json.dumps({'mcpServers': {'test': spec}}))

    def test_export_does_not_copy_inline_credentials(self):
        raw = export_configuration([{'name': 'remote', 'url': 'https://example.com/mcp?api_key=secret&scope=read', 'headers': {'Authorization': 'Bearer secret'}, 'header_env': {'X-Api-Key': 'MY_API_KEY'}},
                                    {'name': 'local', 'command': 'python', 'args': ['--token', 'secret', '--api-key=secret'], 'env': {'GITHUB_TOKEN': 'secret', 'LANG': 'tr_TR'}}])
        self.assertNotIn('secret', raw)
        self.assertIn('MY_API_KEY', raw)
        self.assertIn('tr_TR', raw)
        self.assertIn('scope=read', raw)
        self.assertIn('REDACTED', raw)

    def test_catalog_rejects_path_and_package_option_injection(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / 'extensions').mkdir()
            for ident, package in [('../outside', 'mcp'), ('ok', '--ignore-scripts=false'), ('ok', 'https://evil.invalid/package.tgz')]:
                (root / 'extensions/catalog.json').write_text(json.dumps({'schema': 1, 'entries': [{'id': ident, 'package': package, 'kind': 'npm', 'source': 'https://example.com'}]}))
                with self.assertRaises(ValueError):
                    load_catalog(root)

    def test_remote_extension_is_opt_in_and_uses_environment_reference(self):
        library = ExtensionLibrary(ROOT)
        with patch('subprocess.Popen') as popen:
            spec = library.install('github')
        popen.assert_not_called()
        self.assertFalse(spec['enabled'])
        self.assertEqual(spec['header_env']['Authorization'], 'KAYRIVA_GITHUB_AUTHORIZATION')
        self.assertNotIn('headers', spec)

    def test_filesystem_install_requires_existing_project_and_cancel_is_honored(self):
        library = ExtensionLibrary(ROOT)
        with self.assertRaises(ValueError):
            library.install('filesystem', '/no-such-kayriva-project')
        cancel = threading.Event()
        cancel.set()
        with self.assertRaises(InterruptedError):
            library.install('github', cancel=cancel)

    def test_npm_install_is_isolated_no_scripts_and_direct_node_entry(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / 'extensions').mkdir()
            (root / 'extensions/catalog.json').write_text((ROOT / 'extensions/catalog.json').read_text())
            library = ExtensionLibrary(root)
            package = root / 'runtime/extensions/memory/node_modules/@modelcontextprotocol/server-memory'
            def execute(argv, **kwargs):
                package.mkdir(parents=True)
                (package / 'index.js').write_text('')
                (package / 'package.json').write_text(json.dumps({'version': '2.0.1', 'bin': {'mcp-server-memory': 'index.js'}}))
            with patch('ai_studio.extension_library.shutil.which', side_effect=lambda name: '/usr/bin/' + name), patch('ai_studio.extension_library._execute', side_effect=execute) as call:
                spec = library.install('memory')
            args = call.call_args.args[0]
            self.assertIn('--ignore-scripts', args)
            self.assertIn('--save-exact', args)
            self.assertEqual(args[-1], '@modelcontextprotocol/server-memory')
            self.assertEqual(spec['command'], '/usr/bin/node')
            self.assertTrue(Path(spec['args'][0]).is_file())
            self.assertEqual(spec['installed_version'], '2.0.1')
            self.assertTrue(spec['env']['MEMORY_FILE_PATH'].startswith(str(root)))

    def test_github_repository_and_url_option_injection_rejected(self):
        for name in ['--public', 'owner/repo; echo hello', 'x/../../outside', 'hello\n--public', '.', '..']:
            with self.assertRaises(ValueError):
                repository_name(name)
        self.assertEqual(repository_name('owner/my-project_1.0'), 'owner/my-project_1.0')
        for url in ['file:///tmp/a', 'https://github.com.evil.invalid/repo', 'https://token@github.com/repo', 'http://github.com/repo']:
            with self.assertRaises(ValueError):
                github_url(url)

    def test_create_is_private_by_default_and_uses_argument_array(self):
        seen = []
        def runner(argv, **kwargs):
            seen.append((argv, kwargs))
            return SimpleNamespace(returncode=0, stdout=json.dumps({'url': 'https://github.com/owner/repo'}), stderr='')
        service = GitHubService(runner)
        url = service.create('owner/repo', 'literal $(touch secret); & value')
        self.assertEqual(url, 'https://github.com/owner/repo')
        self.assertIn('--private', seen[0][0])
        self.assertNotIn('--public', seen[0][0])
        self.assertEqual(seen[0][0][-1], 'literal $(touch secret); & value')
        self.assertFalse(seen[0][1]['shell'])

    def test_preview_uses_real_gitignore_and_excludes_secrets_and_symlinks(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / '.gitignore').write_text('ignored/\n*.tmp\n')
            (root / 'main.py').write_text('print(1)')
            (root / '.env').write_text('API_KEY=private')
            (root / '.env.example').write_text('API_KEY=replace-me')
            (root / 'config.py').write_text('TOKEN = "ghp_' + 'a' * 35 + '"')
            (root / 'model.gguf').write_bytes(b'weights')
            (root / 'ignored').mkdir()
            (root / 'ignored/skip.py').write_text('private')
            (root / 'link.py').symlink_to(root / 'main.py')
            preview = GitHubService().preview(root)
            paths = {name for name, _, _ in preview.files}
            self.assertIn('main.py', paths)
            self.assertIn('.env.example', paths)
            self.assertNotIn('ignored/skip.py', paths)
            self.assertFalse(paths & {'.env', 'config.py', 'model.gguf', 'link.py'})
            self.assertFalse((root / '.git').exists())

    def test_publish_rechecks_reviewed_bytes_before_any_remote_action(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / 'main.py').write_text('print(1)')
            service = GitHubService()
            preview = service.preview(root)
            (root / 'main.py').write_text('changed')
            with patch.object(service, 'command') as command:
                with self.assertRaisesRegex(ValueError, 'değişti'):
                    service.publish(preview, 'project')
                command.assert_not_called()

    def test_publish_uploads_only_selected_snapshot_without_touching_project_git(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / 'main.py').write_text('print(1)')
            (root / 'omit.py').write_text('private code')
            service = GitHubService()
            preview = service.preview(root)
            seen = []
            def command(argv, **kwargs):
                seen.append(argv)
                if argv[:3] == ['gh', 'repo', 'create']:
                    snapshot = Path(argv[argv.index('--source') + 1])
                    self.assertTrue((snapshot / 'main.py').is_file())
                    self.assertFalse((snapshot / 'omit.py').exists())
                    self.assertNotEqual(snapshot, root)
                    self.assertIn('--private', argv)
                return SimpleNamespace(returncode=0, stdout=json.dumps({'url': 'https://github.com/owner/project'}))
            with patch.object(service, 'command', side_effect=command):
                self.assertEqual(service.publish(preview, 'owner/project', selected=['main.py']), 'https://github.com/owner/project')
            self.assertFalse((root / '.git').exists())
            self.assertEqual((root / 'omit.py').read_text(), 'private code')

    def test_github_error_omits_stderr_credentials(self):
        service = GitHubService(lambda *args, **kwargs: SimpleNamespace(returncode=1, stderr='secret-token', stdout=''))
        with self.assertRaises(RuntimeError) as raised:
            service.create('repo')
        self.assertNotIn('secret-token', str(raised.exception))


if __name__ == '__main__':
    unittest.main()
