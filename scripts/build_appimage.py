"""Build a genuine Type 2 AppImage with verified upstream packaging tools."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import tempfile
import tomllib
import urllib.request
from package_linux import digest


def verified_download(spec, destination):
    if destination.is_file() and destination.stat().st_size == spec['size'] and digest(destination) == spec['sha256']:
        return destination
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=destination.parent, delete=False) as stream:
        pending = Path(stream.name)
        try:
            with urllib.request.urlopen(spec['url'], timeout=45) as response:
                size = 0
                while chunk := response.read(1024 * 1024):
                    size += len(chunk)
                    if size > spec['size']:
                        raise ValueError('Upstream AppImage tool size changed; review scripts/appimage-tools.json')
                    stream.write(chunk)
            stream.flush()
            if size != spec['size'] or digest(pending) != spec['sha256']:
                raise ValueError('AppImage tool SHA-256 mismatch; review the upstream release before updating its pin')
            pending.replace(destination)
        finally:
            pending.unlink(missing_ok=True)
    destination.chmod(0o755)
    return destination


def build(root):
    root = root.resolve()
    arch = {'amd64': 'x86_64', 'arm64': 'aarch64'}.get(platform.machine().lower(), platform.machine().lower())
    pins = json.loads((root/'scripts/appimage-tools.json').read_text())
    if arch not in pins:
        raise ValueError('No verified AppImage toolchain configured for ' + arch)
    cache = root/'build/appimage-tools'
    tool = verified_download(pins[arch]['tool'], cache/('appimagetool-'+arch+'.AppImage'))
    runtime = verified_download(pins[arch]['runtime'], cache/('runtime-'+arch))
    payload = root/'build/linux/payload/Kayriva'
    appdir = root/'build/linux/Kayriva.AppDir'
    (appdir/'usr/bin').mkdir(parents=True, exist_ok=True)
    shutil.copy2(payload, appdir/'usr/bin/Kayriva')
    assets = root/'src/ai_studio/ui/assets'
    shutil.copy2(assets/'kayriva.svg', appdir/'kayriva.svg')
    shutil.copy2(assets/'kayriva.svg', appdir/'.DirIcon')
    (appdir/'kayriva.desktop').write_text('''[Desktop Entry]
Type=Application
Name=Kayriva
Comment=Your local AI workspace
Exec=Kayriva
Icon=kayriva
Terminal=false
Categories=Utility;
StartupWMClass=Kayriva
''')
    apprun = appdir/'AppRun'
    apprun.write_text('''#!/bin/sh
set -eu
app_dir=${APPDIR:-$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)}
# Preserve the AppImage runtime's outer path across the bundled application.
exec "$app_dir/usr/bin/Kayriva" "$@"
''')
    apprun.chmod(0o755)
    validator = shutil.which('desktop-file-validate')
    if validator:
        subprocess.run([validator,str(appdir/'kayriva.desktop')],check=True)
    output = root/'dist/linux'/f'Kayriva-{arch}.AppImage'
    output.parent.mkdir(parents=True, exist_ok=True)
    version = tomllib.loads((root/'pyproject.toml').read_text())['project']['version']
    env = {**os.environ, 'APPIMAGE_EXTRACT_AND_RUN':'1', 'ARCH':arch, 'VERSION':version, 'SOURCE_DATE_EPOCH':'0', 'LC_ALL':'C.UTF-8'}
    # Fixed runtime avoids appimagetool downloading a mutable runtime itself.
    subprocess.run([str(tool),'--runtime-file','../appimage-tools/'+runtime.name,
                    '--mksquashfs-opt','-processors','--mksquashfs-opt','2',
                    appdir.name,'../../dist/linux/'+output.name],
                   cwd=root/'build/linux',env=env,check=True)
    output.chmod(0o755)
    with output.open('rb') as stream:
        header = stream.read(12)
    if header[:4] != b'\x7fELF' or header[8:11] != b'AI\x02':
        raise ValueError('Output is not a Type 2 AppImage')
    info = {'version':version,'platform':'linux','architecture':arch,'filename':output.name,
            'size':output.stat().st_size,'sha256':digest(output),'payload_sha256':digest(payload),
            'format':'appimage-type2','runtime_sha256':pins[arch]['runtime']['sha256']}
    (output.parent/'build-info.json').write_text(json.dumps(info,indent=2)+'\n')
    print('AppImage ready: '+str(output))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1])
    build(parser.parse_args().root)
