"""Initialize persistent user data from read-only, bundled distribution assets."""
from __future__ import annotations

import os
import sys
from pathlib import Path


def initialize_bundle() -> Path | None:
    if not getattr(sys, 'frozen', False):
        return None
    bundle = Path(sys._MEIPASS)
    if os.environ.get('AI_STUDIO_ROOT'):
        root = Path(os.environ['AI_STUDIO_ROOT']).expanduser().resolve()
    elif sys.platform == 'win32':
        root = Path(os.environ.get('LOCALAPPDATA', Path.home() / 'AppData/Local')) / 'Kayriva'
    else:
        root = Path(os.environ.get('XDG_DATA_HOME', Path.home() / '.local/share')) / 'Kayriva'
    root.mkdir(parents=True, exist_ok=True)
    os.environ['AI_STUDIO_ROOT'] = str(root)
    for relative in ('models/catalog.json', 'engine/releases.json', 'extensions/catalog.json'):
        source, destination = bundle / relative, root / relative
        _update_asset(source, destination)
    helper = bundle / 'helpers/KayrivaBridge'
    if helper.is_file():
        destination = root / 'bin/KayrivaBridge'
        _update_asset(helper, destination)
        destination.chmod(0o700)
    return root


def _update_asset(source: Path, destination: Path) -> None:
    incoming = source.read_bytes()
    if destination.is_file() and destination.read_bytes() == incoming:
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    # Separate temporary files allow simultaneous app starts without collisions.
    import tempfile
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=destination.parent, delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(incoming)
        temporary.replace(destination)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
