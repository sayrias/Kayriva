"""User-level Linux launcher integration for the portable executable."""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

from .brand import APP_ID, APP_NAME
from .executable import installed_executable
from .distribution import _update_asset

ICON_PATH = Path(__file__).parent / 'ui/assets/kayriva.svg'
MIME_PATH = Path(__file__).parent / 'ui/assets/kayriva-mime.xml'


def _data_home(directory: Path | None = None) -> Path:
    if directory is None:
        configured = Path(os.environ.get('XDG_DATA_HOME', ''))
        directory = configured if configured.is_absolute() else Path.home() / '.local/share'
    directory = Path(directory)
    if not directory.is_absolute():
        raise ValueError('Desktop data directory must be absolute')
    return directory


def _install_icon(data_home: Path) -> Path:
    icon = data_home / 'icons/hicolor/scalable/apps' / f'{APP_ID}.svg'
    _update_asset(ICON_PATH, icon)
    icon.chmod(0o644)
    return icon


def install_file_icon(data_home: Path | None = None) -> bool:
    """Give the published Kayriva filename its own desktop MIME type and icon."""
    data_home = _data_home(data_home)
    _install_icon(data_home)
    mime = data_home / 'mime'
    definition = mime / 'packages/io.github.sayrias.Kayriva.xml'
    _update_asset(MIME_PATH, definition)
    definition.chmod(0o644)
    cache = mime / 'mime.cache'
    if cache.is_file() and cache.stat().st_mtime_ns >= definition.stat().st_mtime_ns:
        return True
    tool = shutil.which('update-mime-database', path=os.defpath)
    if not tool:
        return False
    # A bundled app must run the system utility with system shared libraries.
    env = os.environ.copy()
    if 'LD_LIBRARY_PATH_ORIG' in env:
        env['LD_LIBRARY_PATH'] = env.pop('LD_LIBRARY_PATH_ORIG')
    else:
        env.pop('LD_LIBRARY_PATH', None)
    env['XDG_DATA_HOME'] = str(data_home)
    try:
        subprocess.run([tool, str(mime)], env=env, capture_output=True, check=True, timeout=15)
    except (OSError, subprocess.SubprocessError) as exc:
        from .local_logging import failure
        failure('Linux file icon registration', exc)
        return False
    return True


def _value(value: str) -> str:
    if any(ord(char) < 32 for char in value):
        raise ValueError('Desktop entry paths cannot contain control characters')
    return value.replace('\\', '\\\\')


def _exec_argument(value: str) -> str:
    # Desktop entries have string escaping, command quoting and field codes.
    # This is not shell quoting; no shell interprets the executable path.
    quoted = ''.join('\\' + char if char in '\\"`$' else char for char in value)
    return _value('"' + quoted.replace('%', '%%') + '"')


def install_launcher(executable: Path | None = None, data_home: Path | None = None) -> Path:
    """Register a persistent icon and launcher, never the temporary bundle path."""
    executable = Path(executable or installed_executable()).resolve()
    if not executable.is_file() or not os.access(executable, os.X_OK):
        raise ValueError('The launcher requires an executable application file')
    if '=' in str(executable):
        raise ValueError('Desktop entry executable paths cannot contain an equals sign')
    data_home = _data_home(data_home)
    icon = data_home / 'icons/hicolor/scalable/apps' / f'{APP_ID}.svg'
    entry = data_home / 'applications' / f'{APP_ID}.desktop'
    contents = '\n'.join([
        '[Desktop Entry]', 'Type=Application', f'Name={APP_NAME}',
        'GenericName=Local AI workspace', 'GenericName[tr]=Yerel yapay zekâ çalışma alanı',
        'Comment=Conversations, project files and research with local models',
        'Comment[tr]=Yerel modellerle sohbet, proje dosyaları ve araştırma',
        # A fixed launcher also lets desktop parsers validate Exec before
        # expanding literal percent signs in the portable executable's name.
        f'Exec=/usr/bin/env -- {_exec_argument(str(executable))}', f'TryExec={_value(str(executable))}',
        f'Icon={_value(str(icon))}', f'StartupWMClass={APP_NAME}',
        'Terminal=false', 'StartupNotify=true', 'Categories=Utility;',
        'Keywords=AI;Chat;Models;Research;', '',
    ])
    _install_icon(data_home)
    # Use the same atomic/no-op writer as the distribution asset copier.
    import tempfile
    with tempfile.TemporaryDirectory(prefix='kayriva-desktop-') as folder:
        source = Path(folder) / 'launcher.desktop'
        source.write_text(contents, encoding='utf-8')
        _update_asset(source, entry)
    entry.chmod(0o644)
    install_file_icon(data_home)
    return entry
