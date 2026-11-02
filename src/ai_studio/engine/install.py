"""Explicit installation of pinned upstream engine packages, confined to engine/bin.

No model/chat data is sent. Package size and SHA-256 are pinned in releases.json.
Archives are flattened to a private directory; library links are copied as regular files.
"""
from __future__ import annotations
import hashlib
import json
import os
import platform
import posixpath
import re
import shutil
import stat
import subprocess
import tarfile
import tempfile
import time
import zipfile
from pathlib import Path, PurePosixPath

import httpx


def executable_name():
    return 'llama-server.exe' if platform.system().lower() == 'windows' else 'llama-server'


def engine_options(root: Path, selected=''):
    name = executable_name()
    manifest_path = root / 'engine/releases.json'
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {'packages': {}}
    machine = platform.machine().lower()
    machine = {'amd64': 'x86_64', 'arm64': 'aarch64'}.get(machine, machine)
    system = platform.system().lower()
    options = []
    legacy = root / 'engine/bin' / name
    if legacy.is_file():
        options.append({'label': 'llama.cpp · uygulama motoru', 'path': str(legacy.resolve()), 'package': None})
    for backend, title in [('cpu', 'llama.cpp · CPU'), ('vulkan', 'llama.cpp · Vulkan GPU'), ('cuda', 'llama.cpp · CUDA NVIDIA')]:
        package = manifest['packages'].get(f'{system}-{machine}-{backend}')
        path = root / 'engine/bin' / backend / name
        if package or path.is_file():
            options.append({'label': title + (' · hazır' if path.is_file() else ' · kurulum gerekli'),
                'path': str(path.resolve()), 'package': {**package, 'version': manifest['version'], 'backend': backend} if package else None})
    found = shutil.which(name)
    if found and not any(o['path']==str(Path(found).resolve()) for o in options):
        options.append({'label':'llama.cpp · sistemde kurulu', 'path': str(Path(found).resolve()), 'package': None})
    if selected and not any(o['path']==str(Path(selected).expanduser().resolve()) for o in options):
        options.append({'label': Path(selected).name + (' · özel motor' if Path(selected).is_file() else ' · bulunamadı'),
            'path': str(Path(selected).expanduser().resolve()), 'package': None})
    return options


def default_binary(root):
    options = engine_options(root)
    name = executable_name()
    vulkan = root / 'engine/bin/vulkan' / name
    legacy = root / 'engine/bin' / name
    if not legacy.is_file() and vulkan.is_file():
        return vulkan
    return next((Path(o['path']) for o in options if Path(o['path']).is_file()), legacy)


def unpack_zip(archive, destination, cancel, size_limit):
    """Flatten only the verified Windows server and DLLs, without extractall."""
    total, names, paths = 0, set(), set()
    with zipfile.ZipFile(archive) as bundle:
        members = bundle.infolist()
        if len(members) > 5000:
            raise ValueError('Motor arşivinde çok fazla dosya var')
        for member in members:
            if cancel.is_set():
                raise InterruptedError('Motor kurulumu durduruldu')
            normalized = member.filename.replace('\\', '/')
            path = PurePosixPath(normalized)
            mode = member.external_attr >> 16
            if (path.is_absolute() or '..' in path.parts or ':' in normalized
                    or any(ord(c) < 32 for c in normalized)
                    or any(part.endswith((' ', '.')) for part in path.parts)
                    or any(re.fullmatch(r'(?:con|prn|aux|nul|com[1-9]|lpt[1-9])(?:\..*)?', part, re.I) for part in path.parts)
                    or stat.S_ISLNK(mode) or stat.S_IFMT(mode) not in {0, stat.S_IFREG, stat.S_IFDIR}):
                raise ValueError('Motor ZIP arşivinde güvenli olmayan yol veya bağlantı var')
            key = normalized.rstrip('/').casefold()
            if key in paths:
                raise ValueError('Motor arşivinde yinelenen yol var')
            paths.add(key)
            if member.flag_bits & 1:
                raise ValueError('Şifreli motor arşivi desteklenmiyor')
            if member.is_dir():
                continue
            name = path.name
            if name.casefold() != 'llama-server.exe' and path.suffix.casefold() != '.dll':
                continue
            if name.casefold() in names or any(p.name.casefold() == name.casefold() for p in destination.iterdir()):
                raise ValueError('Motor arşivleri arasında yinelenen dosya var')
            names.add(name.casefold())
            total += member.file_size
            if member.file_size < 0 or total > size_limit:
                raise ValueError('Motor arşivi boyut sınırını aşıyor')
            # Windows file names are case-insensitive; keep the server spelling
            # stable for discovery on other platforms and staging tests too.
            output = destination / ('llama-server.exe' if name.casefold() == 'llama-server.exe' else name)
            written = 0
            with bundle.open(member) as source, output.open('wb') as out:
                while chunk := source.read(1024 * 1024):
                    if cancel.is_set():
                        raise InterruptedError('Motor kurulumu durduruldu')
                    written += len(chunk)
                    if written > member.file_size:
                        raise ValueError('Motor dosyası beklenen boyutu aşıyor')
                    out.write(chunk)
            if written != member.file_size:
                raise ValueError('Motor arşivi eksik')
    binary = destination / 'llama-server.exe'
    if not binary.is_file():
        raise ValueError('Arşivde llama-server.exe bulunamadı')
    return binary


def unpack(archive, destination, cancel, size_limit=512_000_000):
    if zipfile.is_zipfile(archive):
        return unpack_zip(archive, destination, cancel, size_limit)
    seen = set()
    total = 0
    sources = {}
    with tarfile.open(archive, 'r:gz') as bundle:
        members = bundle.getmembers()
        if len(members) > 5000:
            raise ValueError('Motor arşivinde çok fazla dosya var')
        entries = {}
        for member in members:
            path = Path(member.name)
            if path.is_absolute() or '..' in path.parts:
                raise ValueError('Motor arşivinde güvenli olmayan yol var')
            if not (member.isfile() or member.isdir() or member.issym() or member.islnk()):
                raise ValueError('Motor arşivinde geçersiz dosya var')
            key = posixpath.normpath(member.name)
            if key in entries:
                raise ValueError('Motor arşivinde yinelenen yol var')
            entries[key] = member
        def resolve(member, visited=None):
            visited = set() if visited is None else visited
            if member.name in visited or len(visited) > 10:
                raise ValueError('Motor arşivinde döngülü bağlantı var')
            visited.add(member.name)
            if member.issym() or member.islnk():
                target = member.linkname if member.islnk() else posixpath.join(posixpath.dirname(member.name), member.linkname)
                target = posixpath.normpath(target)
                if target.startswith('/') or target=='..' or target.startswith('../') or target not in entries:
                    raise ValueError('Motor arşivinde dışarıya yönelen bağlantı var')
                return resolve(entries[target], visited)
            if not member.isfile():
                raise ValueError('Motor kitaplığı bir dosya olmalı')
            return member
        for member in members:
            if cancel.is_set():
                raise InterruptedError('Motor kurulumu durduruldu')
            if member.isdir():
                continue
            if member.issym() or member.islnk():
                resolve(member)  # Reject external links even in omitted CLI/docs entries.
            name = Path(member.name).name
            if name != 'llama-server' and '.so' not in name:
                continue
            if name in seen:
                raise ValueError('Motor arşivinde yinelenen dosya var')
            if (destination / name).exists():
                raise ValueError('Motor arşivleri arasında yinelenen dosya var')
            seen.add(name)
            source_member = resolve(member)
            if source_member.name in sources:
                os.link(sources[source_member.name], destination / name)
                continue
            total += source_member.size
            if total > size_limit:
                raise ValueError('Motor arşivi boyut sınırını aşıyor')
            source = bundle.extractfile(source_member)
            with source, (destination / name).open('wb') as out:
                shutil.copyfileobj(source, out, length=1024*1024)
            (destination / name).chmod(0o755)
            sources[source_member.name] = destination / name
    binary = destination / 'llama-server'
    if not binary.is_file():
        raise ValueError('Arşivde llama-server bulunamadı')
    return binary


def fetch_package(package, archive, cancel, status):
    if (not re.fullmatch(r'[\w.-]+', str(package.get('version', '')))
            or not re.fullmatch(r'[\w.-]+', str(package.get('asset', '')))
            or not isinstance(package.get('size'), int) or not 0 < package['size'] <= 4_000_000_000
            or not re.fullmatch(r'[a-fA-F0-9]{64}', str(package.get('sha256', '')))):
        raise ValueError('Motor paketi doğrulama bilgileri geçersiz')
    url = f'https://github.com/ggml-org/llama.cpp/releases/download/{package["version"]}/{package["asset"]}'
    deadline = time.monotonic()+180
    for attempt in range(3):
        if cancel.is_set():
            raise InterruptedError('Motor kurulumu durduruldu')
        try:
            status('Resmi motor indiriliyor…')
            digest, received = hashlib.sha256(), 0
            with httpx.Client(timeout=httpx.Timeout(20,connect=10), follow_redirects=True, trust_env=True) as client:
                with client.stream('GET', url) as response:
                    response.raise_for_status()
                    with archive.open('wb') as out:
                        for chunk in response.iter_bytes(1024*1024):
                            if cancel.is_set(): raise InterruptedError('Motor kurulumu durduruldu')
                            if time.monotonic()>deadline: raise TimeoutError('Motor indirme süresi aşıldı; tekrar dene.')
                            received += len(chunk)
                            if received > package['size']: raise ValueError('Motor paketi beklenen boyutu aşıyor')
                            digest.update(chunk); out.write(chunk)
                            status(f'Motor indiriliyor · %{received*100//package["size"]}')
            if received != package['size'] or digest.hexdigest() != package['sha256']:
                raise ValueError('Motor paketinin SHA-256 doğrulaması başarısız')
            break
        except (httpx.TransportError, httpx.HTTPStatusError):
            if attempt==2 or time.monotonic()>deadline: raise
            status('Bağlantı yeniden deneniyor…')
            if cancel.wait(2**attempt): raise InterruptedError('Motor kurulumu durduruldu')


def install_engine(root, option, cancel, status=lambda _: None):
    package = option.get('package')
    if not package:
        raise ValueError('Bu motor için hazır kurulum paketi yok; Dosya seç ile llama-server seçebilirsin.')
    destination = Path(option['path']).parent
    binary_name = 'llama-server.exe' if package['asset'].lower().endswith('.zip') else 'llama-server'
    # Installation targets are application-owned slots, never a custom/system path.
    expected = root.resolve() / 'engine/bin' / package['backend']
    if destination.resolve() != expected or Path(option['path']).name != binary_name:
        raise ValueError('Geçersiz motor kurulum konumu')
    if (destination / binary_name).exists():
        return str(destination / binary_name)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.install-', dir=destination.parent) as raw:
        stage = Path(raw)
        archive = stage / ('package.zip' if binary_name.endswith('.exe') else 'package.tar.gz')
        fetch_package(package, archive, cancel, status)
        status('Motor doğrulanıyor…')
        files = stage / 'files'; files.mkdir()
        binary = unpack(archive, files, cancel, 2_000_000_000 if package['backend']=='cuda' else 512_000_000)
        if package.get('runtime'):
            runtime = {**package['runtime'],'version':package['version']}
            runtime_archive = stage / ('runtime.zip' if package['runtime']['asset'].lower().endswith('.zip') else 'runtime.tar.gz')
            fetch_package(runtime, runtime_archive, cancel, status)
            unpack(runtime_archive, files, cancel, 2_000_000_000)
        try:
            env={k:v for k,v in os.environ.items() if not k.startswith('LLAMA_ARG_')}
            check = subprocess.run([str(binary), '--version'], capture_output=True, text=True, timeout=20, cwd=files,env=env,
                                   creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0) if os.name == 'nt' else 0)
            if check.returncode:
                raise ValueError('Motor bu sistemde çalışamadı. Paylaşılan kitaplık veya işlemci uyumluluğunu kontrol et.')
        except OSError as exc:
            raise ValueError('Motor bu sistemde çalışamadı; işletim sistemi/kitaplık uyumluluğunu kontrol et.') from exc
        (files / 'build-info.json').write_text(json.dumps(package, indent=2))
        if cancel.is_set(): raise InterruptedError('Motor kurulumu durduruldu')
        # A validated staging directory is published in one operation.
        if destination.exists():
            raise ValueError('Motor klasörü zaten var; özel dosyaları korumak için kurulum durduruldu.')
        files.replace(destination)
    status('Yerel motor hazır')
    return str(destination / binary_name)
