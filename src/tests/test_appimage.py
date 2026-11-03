import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from ai_studio.executable import installed_executable
from ai_studio.desktop import install_launcher


class AppImagePaths(unittest.TestCase):
    def test_mounted_payload_uses_outer_appimage_for_launcher_and_updates(self):
        with tempfile.TemporaryDirectory() as raw:
            root=Path(raw);payload=root/'mount/usr/bin/Kayriva'
            payload.parent.mkdir(parents=True);payload.write_bytes(b'payload')
            outer=root/'Kayriva-x86_64.AppImage';outer.write_bytes(b'\x7fELF'+b'\0'*4+b'AI\x02\0');outer.chmod(0o755)
            with patch('sys.executable',str(payload)), patch('sys.frozen',True,create=True), patch('sys.platform','linux'), patch.dict(os.environ,{'APPIMAGE':str(outer),'APPDIR':str(root/'mount')}):
                self.assertEqual(installed_executable(),outer)
                entry=install_launcher(data_home=root/'data')
                self.assertIn(str(outer),entry.read_text())
                self.assertNotIn(str(payload),entry.read_text())
                # An unrelated APPIMAGE variable must never redirect an update.
                with patch.dict(os.environ,{'APPDIR':str(root/'other-mount')}):
                    self.assertEqual(installed_executable(),payload)
                outer.write_bytes(b'not an AppImage')
                self.assertEqual(installed_executable(),payload)

    def test_source_mode_ignores_inherited_appimage_environment(self):
        with patch('sys.frozen',False,create=True), patch.dict(os.environ,{'APPIMAGE':'/tmp/fake.AppImage','APPDIR':'/'}):
            import sys
            self.assertEqual(installed_executable(),Path(sys.executable).resolve())
