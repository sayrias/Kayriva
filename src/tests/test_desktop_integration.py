import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

from ai_studio.brand import APP_ID
from ai_studio.desktop import ICON_PATH, install_file_icon, install_launcher


@unittest.skipUnless(sys.platform.startswith('linux'), 'Linux desktop integration')
class DesktopIntegrationTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which('update-mime-database'), 'Desktop MIME utility unavailable')
    def test_file_manager_identifies_the_published_binary_and_resolves_its_icon(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            data = root / 'desktop data'
            shutil.copy2(sys.executable, root / 'Kayriva-x86_64.AppImage')
            shutil.copy2(sys.executable, root / 'OtherProgram')
            original = (root / 'Kayriva-x86_64.AppImage').read_bytes()
            self.assertTrue(install_file_icon(data))
            self.assertEqual((root / 'Kayriva-x86_64.AppImage').read_bytes(), original)
            self.assertFalse((data / 'applications').exists())
            script = '''
import sys
from pathlib import Path
from PySide6.QtCore import QMimeDatabase, QStandardPaths
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication
app=QApplication([])
db=QMimeDatabase()
mime=db.mimeTypeForFile(sys.argv[1])
assert mime.name()=='application/x-kayriva-executable', mime.name()
assert mime.inherits('application/x-executable')
assert mime.iconName()=='io.github.sayrias.Kayriva'
assert mime.comment() in {'Kayriva application','Kayriva uygulaması'},mime.comment()
QIcon.setThemeName('hicolor')
# Offscreen Qt has no platform theme; use the desktop's standard icon roots.
QIcon.setThemeSearchPaths([str(Path(p)/'icons') for p in QStandardPaths.standardLocations(QStandardPaths.GenericDataLocation)])
assert not QIcon.fromTheme(mime.iconName()).isNull()
other=db.mimeTypeForFile(sys.argv[2])
assert other.name()!='application/x-kayriva-executable',other.name()
'''
            result = subprocess.run([sys.executable, '-c', script, str(root / 'Kayriva-x86_64.AppImage'), str(root / 'OtherProgram')],
                env={**os.environ, 'XDG_DATA_HOME': str(data), 'QT_QPA_PLATFORM': 'offscreen'}, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            with patch('ai_studio.desktop.subprocess.run') as rebuild:
                self.assertTrue(install_file_icon(data))
                rebuild.assert_not_called()

    def test_missing_mime_utility_does_not_prevent_launcher_creation(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            executable = self.make_executable(root / 'Kayriva')
            with patch('ai_studio.desktop.shutil.which', return_value=None):
                entry = install_launcher(executable, root / 'desktop data')
            self.assertTrue(entry.is_file())
            self.assertFalse((root / 'desktop data/mime/mime.cache').exists())

    def make_executable(self, path):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('#!/usr/bin/python3\nimport json,sys\nfrom pathlib import Path\n'
                        'Path(__file__).with_name("launched.json").write_text(json.dumps(sys.argv))\n')
        path.chmod(0o755)
        return path

    def test_launcher_survives_bundle_cleanup_and_tracks_moved_executable(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            executable = self.make_executable(root / 'Türkçe klasör/Kayriva')
            data = root / 'user data'
            entry = install_launcher(executable, data)
            icon = data / f'icons/hicolor/scalable/apps/{APP_ID}.svg'
            self.assertEqual(icon.read_bytes(), ICON_PATH.read_bytes())
            self.assertIn('Name=Kayriva\n', entry.read_text())
            self.assertIn('StartupWMClass=Kayriva\n', entry.read_text())
            self.assertNotIn('_MEI', entry.read_text())
            first = entry.stat().st_mtime_ns
            self.assertEqual(install_launcher(executable, data), entry)
            self.assertEqual(entry.stat().st_mtime_ns, first)
            executable = self.make_executable(root / 'Moved application/Kayriva')
            install_launcher(executable, data)
            self.assertIn(str(executable), entry.read_text())
            self.assertEqual(len(list(entry.parent.glob('*.desktop'))), 1)
            validator = shutil.which('desktop-file-validate')
            if validator:
                subprocess.run([validator, str(entry)], check=True, capture_output=True)

    def test_real_desktop_parser_launches_reserved_characters_without_shell_expansion(self):
        system_python = Path('/usr/bin/python3')
        if not system_python.exists() or subprocess.run(
                [str(system_python), '-c', 'from gi.repository import Gio'], capture_output=True).returncode:
            self.skipTest('System GIO bindings unavailable')
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            executable = self.make_executable(root / 'Türkçe space' / 'Kayriva %f "quote" $money `tick` \\slash')
            entry = install_launcher(executable, root / 'desktop data')
            launched = subprocess.run([str(system_python), '-c',
                'import sys; from gi.repository import Gio; '
                'app=Gio.DesktopAppInfo.new_from_filename(sys.argv[1]); '
                'assert app is not None; assert app.get_name()=="Kayriva"; '
                'assert app.launch([],None)', str(entry)], capture_output=True, text=True)
            self.assertEqual(launched.returncode, 0, launched.stderr)
            result = executable.with_name('launched.json')
            deadline = time.monotonic() + 3
            while not result.exists() and time.monotonic() < deadline:
                time.sleep(.01)
            self.assertEqual(json.loads(result.read_text()), [str(executable)])

    def test_xdg_fallback_and_invalid_paths_do_not_write_bad_launchers(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            executable = self.make_executable(root / 'Kayriva')
            with patch.dict(os.environ, {'XDG_DATA_HOME': 'relative/path'}), patch('pathlib.Path.home', return_value=root):
                entry = install_launcher(executable)
            self.assertEqual(entry, root / f'.local/share/applications/{APP_ID}.desktop')
            for name in ['bad\nentry', 'bad=entry']:
                with self.subTest(name=name), self.assertRaises(ValueError):
                    install_launcher(self.make_executable(root / name), root / 'invalid')
            self.assertFalse((root / 'invalid').exists())

    def test_main_sets_linux_identity_and_default_icon_without_source_registration(self):
        script = '''
import sys
from unittest.mock import patch
from PySide6.QtWidgets import QApplication
from ai_studio.brand import APP_ID
from ai_studio.__main__ import main
class Window:
    def show(self):
        app=QApplication.instance()
        assert app.applicationName()=='Kayriva'
        assert app.applicationDisplayName()=='Kayriva'
        assert app.desktopFileName()==APP_ID
        assert not app.windowIcon().pixmap(256,256).isNull()
with patch.object(sys, 'argv', ['renamed-binary']), patch('ai_studio.ui.window.Window', Window), patch.object(QApplication, 'exec', return_value=0), patch('ai_studio.desktop.install_launcher') as install:
    assert main()==0
    install.assert_not_called()
'''
        subprocess.run([sys.executable, '-c', script], env={**os.environ, 'QT_QPA_PLATFORM': 'offscreen'},
                       check=True, capture_output=True)


if __name__ == '__main__':
    unittest.main()
