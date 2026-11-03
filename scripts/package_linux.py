"""Package a verified Linux build and its measured ABI requirements."""
from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tarfile
import tempfile
import tomllib


def digest(path: Path) -> str:
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def glibc_requirements(executable: Path) -> dict:
    from PyInstaller.archive.readers import CArchiveReader
    tool = shutil.which('readelf')
    if not tool:
        raise ValueError('Linux archive inspection requires readelf from binutils')
    requirements = {}
    elf_count = 0
    with tempfile.TemporaryDirectory(prefix='kayriva-abi-') as directory:
        temporary = Path(directory) / 'library'

        def inspect(name, path):
            nonlocal elf_count
            elf_count += 1
            result = subprocess.run([tool, '--version-info', '--wide', str(path)],
                                    env={**os.environ, 'LC_ALL': 'C'},
                                    capture_output=True, text=True, check=True, timeout=30).stdout
            needs = result.split('Version needs section', 1)[1] if 'Version needs section' in result else ''
            versions = re.findall(r'Name: GLIBC_([0-9]+(?:\.[0-9]+)+)', needs)
            if versions:
                requirements[name] = max(versions, key=lambda v: tuple(map(int, v.split('.'))))

        def inspect_archive(path, prefix=''):
            reader = CArchiveReader(str(path))
            for name, entry in reader.toc.items():
                if entry[-1] not in ('b', 'x'):
                    continue
                data = reader.extract(name)
                if isinstance(data, bytes) and data.startswith(b'\x7fELF'):
                    temporary.write_bytes(data)
                    inspect(prefix + name, temporary)
                    if name == 'helpers/KayrivaBridge':
                        helper = Path(directory) / 'bridge'
                        helper.write_bytes(data)
                        inspect_archive(helper, prefix + name + '::')

        inspect('Kayriva payload', executable)
        inspect_archive(executable)
    maximum = max(requirements.values(), key=lambda v: tuple(map(int, v.split('.'))))
    return {'libc': 'glibc', 'required_glibc': maximum, 'inspected_elf_files': elf_count,
            'limiting_libraries': sorted(name for name, version in requirements.items() if version == maximum),
            'verification': 'ELF symbol requirements; not a cross-distribution runtime test'}


def package(root: Path) -> Path:
    root = root.resolve()
    version = tomllib.loads((root / 'pyproject.toml').read_text())['project']['version']
    if not re.fullmatch(r'[0-9A-Za-z][0-9A-Za-z.+-]*', version):
        raise ValueError('Invalid package version')
    info = json.loads((root/'dist/linux/build-info.json').read_text())
    architecture = info['architecture']
    filename = f'Kayriva-{architecture}.AppImage'
    binary = root/'dist/linux'/filename
    if (info['version'] != version or info['platform'] != 'linux' or info['filename'] != filename
            or binary.stat().st_size != info['size'] or digest(binary) != info['sha256']):
        raise ValueError('Linux build is stale or modified; run ./kayriva.sh build first')
    with binary.open('rb') as stream:
        header = stream.read(20)
    if header[:6] != b'\x7fELF\x02\x01' or header[8:11] != b'AI\x02':
        raise ValueError('Expected a genuine Type 2 AppImage')
    if {62:'x86_64',183:'aarch64'}.get(int.from_bytes(header[18:20],'little')) != architecture:
        raise ValueError('AppImage architecture does not match the build metadata')
    payload = root/'build/linux/payload/Kayriva'
    if digest(payload) != info['payload_sha256']:
        raise ValueError('AppImage payload changed; rebuild before packaging')
    compatibility = {'version':version,'platform':'linux','architecture':architecture,
                     'binary_sha256':info['sha256'], **glibc_requirements(payload)}
    name = f'Kayriva-{version}-linux-{architecture}'
    readme = f'''Kayriva {version} — Linux {architecture}

Extract this archive, open its folder and run:
  ./{filename}

If necessary, restore executable permission:
  chmod +x {filename}

Requirements for this build:
  - {architecture}, 64-bit GNU/Linux
  - glibc {compatibility['required_glibc']} or newer
  - A compatible X11/Wayland desktop, system libraries and graphics drivers

The glibc baseline is measured from all {compatibility['inspected_elf_files']} ELF files in
the package. It is a necessary requirement, not a guarantee for every distribution.
This is not a musl/Alpine, ARM32 or universal Linux build. A different architecture
requires its own build. Compressing the application does not change compatibility.

The first launch registers the application menu entry and the Kayriva file icon.
If FUSE mounting is unavailable: ./{filename} --appimage-extract-and-run
To register without opening a window: ./{filename} --install-desktop
Keep the AppImage filename for the dedicated file icon.

Models and inference runtimes are separate downloads. Conversations, settings
and downloaded models are stored in the user's Kayriva data directory, outside
this extracted folder. They are not included in this archive.

SHA256SUMS covers this archive's contents. compatibility.json records the measured
requirements. Source-code license: not yet selected; third-party licenses apply.
'''
    files = {
        'README.txt': readme.encode(),
        'compatibility.json': (json.dumps(compatibility, indent=2) + '\n').encode(),
        'kayriva.svg': (root / 'src/ai_studio/ui/assets/kayriva.svg').read_bytes(),
        '.directory': b'[Desktop Entry]\nType=Directory\nName=Kayriva\nIcon=./kayriva.svg\n',
        'licenses/NotoSans-LICENSE.txt': (root / 'src/ai_studio/ui/assets/NotoSans-LICENSE.txt').read_bytes(),
    }
    checksums = [f'{info["sha256"]}  {filename}']
    checksums += [f'{hashlib.sha256(data).hexdigest()}  {path}' for path, data in sorted(files.items())]
    files['SHA256SUMS'] = ('\n'.join(checksums) + '\n').encode()
    output = binary.parent / f'{name}.tar.gz'
    with tempfile.TemporaryDirectory(prefix='kayriva-archive-', dir=output.parent) as directory:
        temporary = Path(directory) / 'package.tar.gz'
        with temporary.open('wb') as stream, gzip.GzipFile(filename='', fileobj=stream, mode='wb', mtime=0) as compressed:
            with tarfile.open(fileobj=compressed, mode='w') as archive:
                for path in [filename, *sorted(files)]:
                    member = tarfile.TarInfo(f'{name}/{path}')
                    member.mode = 0o755 if path == filename else 0o644
                    member.size = binary.stat().st_size if path == filename else len(files[path])
                    if path == filename:
                        with binary.open('rb') as app:
                            archive.addfile(member, app)
                    else:
                        archive.addfile(member, io.BytesIO(files[path]))
        temporary.replace(output)
    print(json.dumps({'archive': str(output), 'size': output.stat().st_size,
                      'required_glibc': compatibility['required_glibc'], 'architecture': architecture}))
    return output


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    package(parser.parse_args().root)
