"""Bounded GitHub release updates, verified staging and optional block deltas.

A release publisher controls both manifest and binaries. HTTPS and SHA-256
protect transport/content consistency; this is not independent code signing.
No repository credentials, chat contents or local file paths are sent.
"""
from __future__ import annotations

import argparse
from contextlib import nullcontext
from dataclasses import dataclass
from functools import total_ordering
import hashlib
import json
import logging
import os
from pathlib import Path
import platform as system_platform
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import threading
from urllib.parse import quote, urlsplit
import uuid
import zlib

import httpx
from . import __version__

LOG = logging.getLogger('ai_studio.updater')
DEFAULT_REPOSITORY = 'sayrias/Kayriva'
MANIFEST_NAME = 'update-manifest.json'
MAX_METADATA = 2 * 1024 * 1024
MAX_ASSET = 512 * 1024 * 1024
BLOCK_SIZE = 64 * 1024
DELTA_MAGIC = b'KAYDELTA1\n'
SHA = re.compile(r'[a-f0-9]{64}')
REPO = re.compile(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+')
SAFE_NAME = re.compile(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,179}')


class UpdateError(ValueError):
    pass


class UpdateNotConfiguredError(UpdateError):
    pass


@total_ordering
class Version:
    """SemVer ordering, including numeric prerelease identifiers (beta.10 > beta.2)."""
    def __init__(self, text):
        if len(str(text)) > 120:
            raise UpdateError('The release version is too long.')
        match = re.fullmatch(r'v?(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-([0-9A-Za-z.-]+))?(?:\+([0-9A-Za-z.-]+))?', str(text))
        if not match:
            raise UpdateError('The release version is not valid SemVer.')
        self.core = tuple(int(match[i]) for i in (1, 2, 3))
        self.pre = tuple(match[4].split('.')) if match[4] else ()
        if any(not item or (item.isdigit() and len(item) > 1 and item.startswith('0')) for item in self.pre):
            raise UpdateError('The prerelease version is invalid.')
        if match[5] and any(not item for item in match[5].split('.')):
            raise UpdateError('The version build metadata is invalid.')
        self.text = str(text).removeprefix('v')

    def __eq__(self, other):
        return isinstance(other, Version) and (self.core, self.pre) == (other.core, other.pre)

    def __lt__(self, other):
        if not isinstance(other, Version):
            return NotImplemented
        if self.core != other.core:
            return self.core < other.core
        if not self.pre or not other.pre:
            return bool(self.pre) and not other.pre
        for left, right in zip(self.pre, other.pre):
            if left == right:
                continue
            if left.isdigit() and right.isdigit():
                return int(left) < int(right)
            if left.isdigit() != right.isdigit():
                return left.isdigit()
            return left < right
        return len(self.pre) < len(other.pre)


@dataclass(frozen=True)
class UpdateSource:
    repository: str = DEFAULT_REPOSITORY

    def validated(self):
        if not self.repository:
            raise UpdateNotConfiguredError('An update repository has not been configured.')
        if not REPO.fullmatch(self.repository) or any(x in {'.', '..'} for x in self.repository.split('/')):
            raise UpdateError('The update repository must have the form owner/repository.')
        return self.repository


@dataclass(frozen=True)
class DeltaAsset:
    name: str
    url: str
    size: int
    sha256: str
    from_version: str
    from_sha256: str
    algorithm: str = 'kayriva-block-v1'


@dataclass(frozen=True)
class UpdateAsset:
    name: str
    url: str
    size: int
    sha256: str
    platform: str
    arch: str
    kind: str
    deltas: tuple[DeltaAsset, ...] = ()


@dataclass(frozen=True)
class ReleaseInfo:
    version: str
    page_url: str
    notes: str
    published_at: str
    asset: UpdateAsset
    prerelease: bool = False

    @property
    def latest_version(self):
        return self.version

    @property
    def release_url(self):
        return self.page_url

    @property
    def asset_url(self):
        return self.asset.url

    @property
    def sha256(self):
        return self.asset.sha256

    @property
    def size(self):
        return self.asset.size


@dataclass(frozen=True)
class ApplyResult:
    requires_exit: bool
    message: str


def host_target():
    os_name = 'windows' if sys.platform == 'win32' else 'linux' if sys.platform.startswith('linux') else sys.platform
    machine = system_platform.machine().lower()
    arch = {'amd64': 'x86_64', 'x64': 'x86_64', 'arm64': 'aarch64'}.get(machine, machine)
    return os_name, arch


def _cancel(cancel):
    if cancel is not None and cancel.is_set():
        raise InterruptedError('Update cancelled; the installed application was not changed.')


def file_sha256(path, cancel=None):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        while chunk := stream.read(1024 * 1024):
            _cancel(cancel)
            digest.update(chunk)
    return digest.hexdigest()


def _client(client):
    return nullcontext(client) if client is not None else httpx.Client(
        timeout=httpx.Timeout(20, connect=10), follow_redirects=False, trust_env=True,
        headers={'User-Agent': 'Kayriva/' + __version__, 'Accept': 'application/vnd.github+json',
                 'X-GitHub-Api-Version': '2022-11-28'})


def _url(url):
    parsed = urlsplit(url)
    if parsed.scheme != 'https' or parsed.username or parsed.password or parsed.port not in {None, 443}:
        raise UpdateError('Updates require a trusted HTTPS GitHub URL.')
    if parsed.hostname not in {'api.github.com', 'github.com', 'release-assets.githubusercontent.com',
                               'objects.githubusercontent.com', 'github-releases.githubusercontent.com'}:
        raise UpdateError('The update host is not an allowed GitHub release host.')
    return url


def _response(client, url, limit, cancel, sink=None, progress=lambda done, total: None, total=None):
    """Stream with bounded redirects and body size; validate every redirect host."""
    for _ in range(6):
        _cancel(cancel)
        _url(url)
        with client.stream('GET', url) as response:
            if response.is_redirect:
                url = str(response.url.join(response.headers.get('location', '')))
                continue
            if response.status_code == 404:
                raise UpdateError('The update repository or release has not been published yet.')
            if response.status_code in {403, 429}:
                raise UpdateError('GitHub update checks are temporarily limited. Please try again later.')
            response.raise_for_status()
            length = response.headers.get('content-length')
            if length:
                try:
                    if not 0 <= int(length) <= limit:
                        raise UpdateError('The update response exceeds its allowed size.')
                except ValueError as exc:
                    raise UpdateError('The update response has an invalid content length.') from exc
            data, received = bytearray(), 0
            for chunk in response.iter_bytes(64 * 1024):
                _cancel(cancel)
                received += len(chunk)
                if received > limit:
                    raise UpdateError('The update response exceeds its allowed size.')
                if sink is None:
                    data.extend(chunk)
                else:
                    sink.write(chunk)
                progress(received, total or limit)
            _cancel(cancel)
            return bytes(data) if sink is None else received
    raise UpdateError('The update download redirected too many times.')


def _json(client, url, cancel):
    try:
        return json.loads(_response(client, url, MAX_METADATA, cancel))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise UpdateError('The release metadata is not valid JSON.') from exc


def _name(value):
    if not isinstance(value, str) or not SAFE_NAME.fullmatch(value) or '..' in value:
        raise UpdateError('The release contains an unsafe asset filename.')
    return value


def _identity(data):
    name = _name(data.get('name'))
    size, sha = data.get('size'), data.get('sha256')
    if type(size) is not int or not 0 < size <= MAX_ASSET or not isinstance(sha, str) or not SHA.fullmatch(sha):
        raise UpdateError('The update size or SHA-256 is invalid.')
    return name, size, sha


def _release_asset(assets, name, repository, tag):
    matches = [a for a in assets if isinstance(a, dict) and a.get('name') == name and a.get('state', 'uploaded') == 'uploaded']
    if len(matches) != 1:
        raise UpdateError('A required verified update asset is missing or duplicated.')
    item = matches[0]
    expected = 'https://github.com/' + repository + '/releases/download/' + quote(tag, safe='') + '/' + quote(name, safe='')
    if item.get('browser_download_url') != expected:
        raise UpdateError('The asset URL does not belong to the selected repository and release.')
    _url(expected)
    return item, expected


def check_for_updates(source=UpdateSource(), current_version=__version__, *, include_prereleases=None,
                      cancel=None, client=None, target=None):
    repository = source.validated()
    current = Version(current_version)
    allow_pre = bool(current.pre) if include_prereleases is None else bool(include_prereleases)
    target = target or host_target()
    try:
        with _client(client) as network:
            data = _json(network, 'https://api.github.com/repos/' + repository + '/releases?per_page=30', cancel)
            if not isinstance(data, list):
                raise UpdateError('The release list has an invalid format.')
            candidates = []
            for release in data[:30]:
                if not isinstance(release, dict) or release.get('draft'):
                    continue
                try:
                    version = Version(release.get('tag_name', ''))
                except UpdateError:
                    continue
                prerelease = bool(version.pre) or bool(release.get('prerelease'))
                if version > current and (allow_pre or not prerelease):
                    candidates.append((version, release, prerelease))
            for version, release, prerelease in sorted(candidates, key=lambda x: x[0], reverse=True):
                tag, assets = release['tag_name'], release.get('assets', [])
                if not isinstance(assets, list):
                    raise UpdateError('The release asset list is invalid.')
                _, manifest_url = _release_asset(assets, MANIFEST_NAME, repository, tag)
                manifest = _json(network, manifest_url, cancel)
                if not isinstance(manifest, dict) or manifest.get('schema') != 1 or manifest.get('version') != version.text:
                    raise UpdateError('The update manifest version or schema does not match its release.')
                rows = manifest.get('files', [])
                if not isinstance(rows, list) or len(rows) > 16:
                    raise UpdateError('The update manifest file list is invalid.')
                matching = [r for r in rows if isinstance(r, dict) and (r.get('platform'), r.get('arch')) == tuple(target)]
                if not matching:
                    continue
                if len(matching) != 1:
                    raise UpdateError('The update manifest contains duplicate platform targets.')
                row = matching[0]
                name, size, sha = _identity(row)
                api_asset, url = _release_asset(assets, name, repository, tag)
                if api_asset.get('size') != size or row.get('kind') != ('installer' if target[0] == 'windows' else 'portable'):
                    raise UpdateError('The release size or package type does not match its manifest.')
                digest = api_asset.get('digest')
                if digest and digest != 'sha256:' + sha:
                    raise UpdateError('The GitHub asset digest does not match the manifest.')
                deltas = []
                if not isinstance(row.get('deltas', []), list) or len(row.get('deltas', [])) > 8:
                    raise UpdateError('The differential update list is invalid.')
                for patch in row.get('deltas', []):
                    pn, ps, ph = _identity(patch)
                    base = patch.get('from_sha256', '')
                    previous = Version(patch.get('from_version', ''))
                    if not SHA.fullmatch(base) or previous >= version or patch.get('algorithm') != 'kayriva-block-v1':
                        raise UpdateError('The differential update identity is invalid.')
                    pa, pu = _release_asset(assets, pn, repository, tag)
                    if pa.get('size') != ps or ps >= size:
                        raise UpdateError('The differential update size is invalid.')
                    deltas.append(DeltaAsset(pn, pu, ps, ph, previous.text, base))
                expected_page = 'https://github.com/' + repository + '/releases/tag/' + quote(tag, safe='')
                if release.get('html_url') != expected_page:
                    raise UpdateError('The release page does not match its repository.')
                return ReleaseInfo(version.text, expected_page, str(release.get('body') or '')[:24000],
                                   str(release.get('published_at') or ''),
                                   UpdateAsset(name, url, size, sha, *target, row['kind'], tuple(deltas)), prerelease)
        return None
    except httpx.HTTPError as exc:
        raise UpdateError('The update server could not be reached. Your installed version is unchanged.') from exc


def _download(network, asset, destination, cancel, progress):
    temporary = destination.with_name(destination.name + '.' + uuid.uuid4().hex + '.part')
    try:
        with temporary.open('xb') as stream:
            os.chmod(temporary, 0o600)
            received = _response(network, asset.url, asset.size, cancel, stream, progress, asset.size)
            stream.flush()
            os.fsync(stream.fileno())
        if received != asset.size or file_sha256(temporary, cancel) != asset.sha256:
            raise UpdateError('The downloaded update failed size or SHA-256 verification.')
        _cancel(cancel)
        temporary.replace(destination)
        return destination
    finally:
        temporary.unlink(missing_ok=True)


def download_update(release, destination_dir, progress=lambda done, total: None, cancel=None, *,
                    base_path=None, current_version=None, client=None):
    _identity(release.asset.__dict__)
    destination_dir = Path(destination_dir)
    destination_dir.mkdir(parents=True, exist_ok=True)
    destination = destination_dir / (Version(release.version).text + '-' + release.asset.name)
    if destination.is_file() and destination.stat().st_size == release.asset.size and file_sha256(destination, cancel) == release.asset.sha256:
        return destination
    if shutil.disk_usage(destination_dir).free < release.asset.size * 2 + 8 * 1024 * 1024:
        raise UpdateError('There is not enough free disk space to stage this update safely.')
    try:
        with _client(client) as network:
            if current_version:
                matching = [d for d in release.asset.deltas if Version(d.from_version) == Version(current_version)]
                if matching:
                    for delta in matching:
                        # Windows installs an onedir application, while its
                        # release artifact is Setup.exe. Only the previous
                        # verified cached installer can be that patch's base.
                        bases = [destination_dir / (delta.from_version + '-' + release.asset.name)]
                        if base_path:
                            bases.append(Path(base_path))
                        verified_base = next((path for path in bases if path.is_file()
                                              and file_sha256(path, cancel) == delta.from_sha256), None)
                        if verified_base is None:
                            continue
                        patch_path = destination_dir / (release.version + '-' + _name(delta.name))
                        try:
                            _download(network, delta, patch_path, cancel, progress)
                            apply_delta(verified_base, patch_path, destination, expected_base=delta.from_sha256,
                                        expected_target=release.asset.sha256, expected_size=release.asset.size, cancel=cancel)
                            return destination
                        except InterruptedError:
                            raise
                        except (UpdateError, OSError, httpx.HTTPError):
                            LOG.warning('Differential update unavailable or invalid; downloading the full package.')
                        finally:
                            patch_path.unlink(missing_ok=True)
                        break
            return _download(network, release.asset, destination, cancel, progress)
    except httpx.HTTPError as exc:
        raise UpdateError('The update download was interrupted. Your installed version is unchanged.') from exc


def build_delta(base_path, target_path, output_path):
    """Write a bounded copy/literal patch. Returns its metadata; no shell tools."""
    base_path, target_path, output_path = map(Path, (base_path, target_path, output_path))
    if not 0 < target_path.stat().st_size <= MAX_ASSET or base_path.stat().st_size > MAX_ASSET:
        raise UpdateError('The differential update input is too large or empty.')
    blocks = {}
    with base_path.open('rb') as base:
        while chunk := base.read(BLOCK_SIZE):
            blocks.setdefault(hashlib.sha256(chunk).hexdigest(), (base.tell() - len(chunk), len(chunk)))
    ops = []
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryFile() as literals, target_path.open('rb') as target:
        while chunk := target.read(BLOCK_SIZE):
            match = blocks.get(hashlib.sha256(chunk).hexdigest())
            if match:
                ops.append(['copy', *match])
            else:
                compressed = zlib.compress(chunk, 6)
                ops.append(['data', len(chunk), len(compressed)])
                literals.write(compressed)
        header = {'schema': 1, 'base_sha256': file_sha256(base_path), 'target_sha256': file_sha256(target_path),
                  'target_size': target_path.stat().st_size, 'ops': ops}
        encoded = json.dumps(header, separators=(',', ':')).encode()
        if len(encoded) > MAX_METADATA:
            raise UpdateError('The differential update instruction list is too large.')
        with output_path.open('wb') as output:
            output.write(DELTA_MAGIC + struct.pack('>I', len(encoded)) + encoded)
            literals.seek(0)
            shutil.copyfileobj(literals, output, BLOCK_SIZE)
    return {'name': output_path.name, 'size': output_path.stat().st_size,
            'sha256': file_sha256(output_path), 'from_sha256': header['base_sha256'],
            'algorithm': 'kayriva-block-v1'}


def apply_delta(base_path, patch_path, destination, *, expected_base, expected_target, expected_size, cancel=None):
    if file_sha256(base_path, cancel) != expected_base or not 0 < expected_size <= MAX_ASSET:
        raise UpdateError('The differential update base does not match this installation.')
    destination = Path(destination)
    temporary = destination.with_name(destination.name + '.' + uuid.uuid4().hex + '.part')
    try:
        with Path(patch_path).open('rb') as patch, Path(base_path).open('rb') as base:
            if patch.read(len(DELTA_MAGIC)) != DELTA_MAGIC:
                raise UpdateError('The differential update header is invalid.')
            size_raw = patch.read(4)
            if len(size_raw) != 4:
                raise UpdateError('The differential update is incomplete.')
            header_size = struct.unpack('>I', size_raw)[0]
            if not 0 < header_size <= MAX_METADATA:
                raise UpdateError('The differential update header exceeds its limit.')
            try:
                header = json.loads(patch.read(header_size))
            except (ValueError, UnicodeError) as exc:
                raise UpdateError('The differential update header is invalid.') from exc
            if not isinstance(header, dict) or header.get('schema') != 1 or header.get('base_sha256') != expected_base or header.get('target_sha256') != expected_target or header.get('target_size') != expected_size:
                raise UpdateError('The differential update target does not match the verified release.')
            ops = header.get('ops')
            if not isinstance(ops, list) or not 0 < len(ops) <= MAX_ASSET // BLOCK_SIZE + 1:
                raise UpdateError('The differential update instruction list is invalid.')
            written, base_size = 0, Path(base_path).stat().st_size
            with temporary.open('xb') as output:
                os.chmod(temporary, 0o600)
                for op in ops:
                    _cancel(cancel)
                    if not isinstance(op, list) or len(op) != 3 or type(op[1]) is not int or type(op[2]) is not int:
                        raise UpdateError('The differential update instruction is invalid.')
                    kind, first, second = op
                    if kind == 'copy':
                        if first < 0 or not 0 < second <= BLOCK_SIZE or first + second > base_size:
                            raise UpdateError('The differential update copy range is invalid.')
                        base.seek(first)
                        chunk = base.read(second)
                    elif kind == 'data':
                        if not 0 < first <= BLOCK_SIZE or not 0 < second <= BLOCK_SIZE + 1024:
                            raise UpdateError('The differential update literal exceeds its limit.')
                        compressed = patch.read(second)
                        if len(compressed) != second:
                            raise UpdateError('The differential update is incomplete.')
                        try:
                            decoder = zlib.decompressobj()
                            chunk = decoder.decompress(compressed, first + 1)
                        except zlib.error as exc:
                            raise UpdateError('The differential update literal is corrupt.') from exc
                        if len(chunk) != first or not decoder.eof or decoder.unused_data or decoder.unconsumed_tail:
                            raise UpdateError('The differential update decompression exceeded its limit.')
                    else:
                        raise UpdateError('The differential update instruction is unknown.')
                    written += len(chunk)
                    if written > expected_size:
                        raise UpdateError('The differential update output exceeds its target.')
                    output.write(chunk)
                output.flush()
                os.fsync(output.fileno())
            if patch.read(1) or written != expected_size or file_sha256(temporary, cancel) != expected_target:
                raise UpdateError('The reconstructed update failed SHA-256 verification.')
            _cancel(cancel)
            temporary.replace(destination)
            return destination
    finally:
        temporary.unlink(missing_ok=True)


def launch_update(release, staged_path, *, current_executable=None):
    """Schedule installation after exit; the caller must gracefully quit the app."""
    if current_executable is None and not getattr(sys, 'frozen', False):
        raise UpdateError('Source installations must be updated through the source repository.')
    if (release.asset.platform, release.asset.arch) != host_target():
        raise UpdateError('This update was built for a different platform or architecture.')
    staged, executable = Path(staged_path).resolve(), Path(current_executable or sys.executable).resolve()
    if not staged.is_file() or staged.stat().st_size != release.asset.size or file_sha256(staged) != release.asset.sha256:
        raise UpdateError('The staged update is missing or has changed; download it again.')
    if not executable.is_file() or not os.access(executable.parent, os.W_OK):
        raise UpdateError('The installation directory is not writable. Install the staged package manually.')
    env = os.environ.copy()
    env['PYINSTALLER_RESET_ENVIRONMENT'] = '1'
    if 'LD_LIBRARY_PATH_ORIG' in env:
        env['LD_LIBRARY_PATH'] = env.pop('LD_LIBRARY_PATH_ORIG')
    else:
        env.pop('LD_LIBRARY_PATH', None)
    if release.asset.platform == 'linux' and release.asset.kind == 'portable':
        hash_tool = shutil.which('sha256sum')
        shell = shutil.which('sh')
        if not hash_tool or not shell:
            raise UpdateError('Automatic installation needs sh and sha256sum; the verified package is available for manual installation.')
        pending = executable.parent / ('.' + executable.name + '-' + uuid.uuid4().hex + '.update')
        backup = executable.parent / ('.' + executable.name + '.previous')
        try:
            shutil.copyfile(staged, pending)
            pending.chmod(executable.stat().st_mode & 0o777 or 0o700)
            with pending.open('rb') as stream:
                os.fsync(stream.fileno())
            if file_sha256(pending) != release.asset.sha256:
                raise UpdateError('The staged application copy failed verification.')
            script = '''set -eu
pid="$1"; target="$2"; stage="$3"; expected="$4"; hash_tool="$5"; backup="$6"
n=0
while kill -0 "$pid" 2>/dev/null; do n=$((n+1)); [ "$n" -lt 360 ] || exit 1; sleep 1; done
actual=$("$hash_tool" -- "$stage"); actual=${actual%% *}
[ "$actual" = "$expected" ] || exit 2
mv -f -- "$target" "$backup"
if ! mv -f -- "$stage" "$target"; then mv -f -- "$backup" "$target"; exit 3; fi
"$target" >/dev/null 2>&1 &
child=$!
sleep 5
if ! kill -0 "$child" 2>/dev/null; then
  if ! wait "$child"; then
    mv -f -- "$backup" "$target"
    "$target" >/dev/null 2>&1 &
  fi
fi
'''
            subprocess.Popen([shell, '-c', script, 'kayriva-updater', str(os.getpid()), str(executable),
                              str(pending), release.asset.sha256, hash_tool, str(backup)], env=env,
                             stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                             start_new_session=True, close_fds=True)
        except BaseException:
            pending.unlink(missing_ok=True)
            raise
    elif release.asset.platform == 'windows' and release.asset.kind == 'installer':
        powershell = shutil.which('powershell.exe')
        if not powershell:
            raise UpdateError('Automatic installation requires Windows PowerShell; run the verified Setup.exe manually.')
        helper = staged.parent / ('install-' + uuid.uuid4().hex + '.ps1')
        helper.write_text('''param([string]$Stage,[string]$Target,[int]$AppPid,[string]$Expected,[long]$Size)
$ErrorActionPreference = 'Stop'
try {
  $running = Get-Process -Id $AppPid -ErrorAction SilentlyContinue
  if ($running) { Wait-Process -Id $AppPid -Timeout 360 -ErrorAction Stop }
  if ((Get-Item -LiteralPath $Stage).Length -ne $Size) { throw 'Update size changed' }
  if ((Get-FileHash -LiteralPath $Stage -Algorithm SHA256).Hash.ToLowerInvariant() -ne $Expected) { throw 'Update hash changed' }
  $directory = Split-Path -LiteralPath $Target
  $arguments = @('/SP-', '/SILENT', '/NORESTART', '/CURRENTUSER', '/NOCLOSEAPPLICATIONS', ('/DIR="' + $directory + '"'))
  $process = Start-Process -FilePath $Stage -ArgumentList $arguments -Wait -PassThru
  if ($process.ExitCode -ne 0) { throw ('Installer failed: ' + $process.ExitCode) }
  Start-Process -FilePath $Target
} catch { $_ | Out-File -LiteralPath ($Stage + '.install-error.log'); exit 1 }
''', encoding='utf-8-sig')
        # The frozen application's DLL directory is inherited by children;
        # system PowerShell must use the normal Windows DLL search path.
        kernel = None
        if os.name == 'nt':
            import ctypes
            kernel = ctypes.windll.kernel32
            kernel.SetDllDirectoryW(None)
        try:
            subprocess.Popen([powershell, '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass',
                              '-File', str(helper), '-Stage', str(staged), '-Target', str(executable),
                              '-AppPid', str(os.getpid()), '-Expected', release.asset.sha256, '-Size', str(release.asset.size)],
                             env=env, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                             creationflags=0x08000000 | 0x00000008, close_fds=True)
        except BaseException:
            helper.unlink(missing_ok=True)
            raise
        finally:
            if kernel is not None:
                kernel.SetDllDirectoryW(getattr(sys, '_MEIPASS', None))
    else:
        raise UpdateError('This package type cannot be installed automatically.')
    return ApplyResult(True, 'The verified update will install and restart Kayriva after the application closes.')


def generate_manifest(version, artifacts, output, *, previous=None):
    version = Version(version).text
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    rows, targets = [], set()
    for os_name, arch, kind, path in artifacts:
        path = Path(path)
        if (os_name, arch) in targets or os_name not in {'linux', 'windows'} or arch not in {'x86_64', 'aarch64'} or kind != ('installer' if os_name == 'windows' else 'portable'):
            raise UpdateError('The release artifact target is invalid or duplicated.')
        targets.add((os_name, arch))
        row = {'name': _name(path.name), 'platform': os_name, 'arch': arch, 'kind': kind,
               'size': path.stat().st_size, 'sha256': file_sha256(path)}
        _identity(row)
        old = (previous or {}).get((os_name, arch))
        if old:
            old_version, old_path = old
            if Version(old_version) >= Version(version):
                raise UpdateError('The differential base must be older than the release.')
            patch_name = f'{path.name}.{Version(old_version).text}-to-{version}.kdelta'
            patch_path = output.parent / _name(patch_name)
            patch = build_delta(old_path, path, patch_path)
            if patch['size'] < row['size'] * .85:
                patch['from_version'] = Version(old_version).text
                row['deltas'] = [patch]
            else:
                patch_path.unlink()
        rows.append(row)
    if not rows:
        raise UpdateError('At least one release artifact is required.')
    manifest = {'schema': 1, 'version': version, 'files': rows}
    temporary = output.with_name(output.name + '.' + uuid.uuid4().hex + '.tmp')
    try:
        temporary.write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
        temporary.replace(output)
    finally:
        temporary.unlink(missing_ok=True)
    return manifest


def main(argv=None):
    parser = argparse.ArgumentParser(description='Kayriva verified release manifest builder')
    sub = parser.add_subparsers(dest='command', required=True)
    build = sub.add_parser('manifest')
    build.add_argument('--version', default=__version__)
    build.add_argument('--output', type=Path, required=True)
    build.add_argument('--artifact', action='append', required=True, help='platform:arch:kind=path')
    build.add_argument('--previous', action='append', default=[], help='platform:arch:version=path')
    args = parser.parse_args(argv)
    def split(value):
        identity, sep, path = value.partition('=')
        parts = identity.split(':')
        if not sep or len(parts) != 3 or not path:
            parser.error('Expected platform:arch:kind-or-version=path')
        return (*parts, Path(path))
    artifacts = [split(item) for item in args.artifact]
    previous = {(os_name, arch): (version, path) for os_name, arch, version, path in map(split, args.previous)}
    result = generate_manifest(args.version, artifacts, args.output, previous=previous)
    print(f"Created {args.output} for {result['version']} ({len(result['files'])} platform targets)")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
