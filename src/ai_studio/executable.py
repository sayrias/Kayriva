"""Resolve the replaceable installation, including a mounted AppImage."""
import os
from pathlib import Path
import sys


def installed_executable() -> Path:
    executable = Path(sys.executable).resolve()
    outer, appdir = os.environ.get('APPIMAGE'), os.environ.get('APPDIR')
    if sys.platform.startswith('linux') and getattr(sys, 'frozen', False) and outer and appdir:
        candidate, mount = Path(outer), Path(appdir)
        if candidate.is_absolute() and mount.is_absolute() and executable.is_relative_to(mount.resolve()) and candidate.is_file():
            with candidate.open('rb') as stream:
                header = stream.read(12)
            if header[:4] == b'\x7fELF' and header[8:11] == b'AI\x02':
                return candidate.resolve()
    return executable
