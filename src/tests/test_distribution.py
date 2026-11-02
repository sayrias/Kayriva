import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ai_studio.distribution import initialize_bundle


class DistributionTests(unittest.TestCase):
    def test_onefile_assets_survive_extraction_cleanup_and_keep_user_data(self):
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            bundle, data = base / 'extraction', base / 'data'
            for name, content in [('models/catalog.json', b'[]'), ('engine/releases.json', b'{}'), ('extensions/catalog.json', b'{}'), ('helpers/KayrivaBridge', b'helper')]:
                source = bundle / name
                source.parent.mkdir(parents=True, exist_ok=True)
                source.write_bytes(content)
            (data / 'runtime').mkdir(parents=True)
            (data / 'runtime/settings.json').write_text('personal settings')
            with patch.object(sys, 'frozen', True, create=True), patch.object(sys, '_MEIPASS', str(bundle), create=True), patch.dict(os.environ, {'AI_STUDIO_ROOT': str(data)}):
                self.assertEqual(initialize_bundle(), data)
                first = (data / 'bin/KayrivaBridge').stat().st_mtime_ns
                initialize_bundle()
                self.assertEqual((data / 'bin/KayrivaBridge').stat().st_mtime_ns, first)
                (bundle / 'models/catalog.json').write_bytes(b'[1]')
                initialize_bundle()
            import shutil
            shutil.rmtree(bundle)
            self.assertEqual((data / 'models/catalog.json').read_bytes(), b'[1]')
            self.assertEqual((data / 'bin/KayrivaBridge').read_bytes(), b'helper')
            self.assertEqual((data / 'runtime/settings.json').read_text(), 'personal settings')
            self.assertTrue(os.access(data / 'bin/KayrivaBridge', os.X_OK))

    def test_default_data_directory_is_outside_installation_and_temp_bundle(self):
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            bundle = base / 'extraction'
            for name in ('models/catalog.json', 'engine/releases.json', 'extensions/catalog.json'):
                source = bundle / name
                source.parent.mkdir(parents=True, exist_ok=True)
                source.write_text('{}')
            for platform, env_key in [('linux', 'XDG_DATA_HOME'), ('win32', 'LOCALAPPDATA')]:
                with self.subTest(platform=platform), patch.object(sys, 'frozen', True, create=True), patch.object(sys, '_MEIPASS', str(bundle), create=True), patch.object(sys, 'platform', platform), patch.dict(os.environ, {env_key: str(base / platform)}, clear=True):
                    self.assertEqual(initialize_bundle(), base / platform / 'Kayriva')


if __name__ == '__main__':
    unittest.main()
