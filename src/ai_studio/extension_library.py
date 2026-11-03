"""Opt-in, isolated installation of curated MCP servers.

Opening the catalog never downloads or executes a server. Installation resolves
the registry release at the user's explicit request and records its version.
"""
from __future__ import annotations

import json
import importlib.metadata
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

from .integrations import validate_spec

_INSTALL_LOCKS = {}
_INSTALL_LOCKS_GUARD = threading.Lock()


def load_catalog(root: Path) -> list[dict]:
    candidates = [Path(root) / "extensions/catalog.json",
                  Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[2])) / "extensions/catalog.json"]
    path = next((p for p in candidates if p.is_file()), None)
    if path is None:
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    entries = data.get("entries", [])
    if data.get("schema") != 1 or not isinstance(entries, list):
        raise ValueError("Eklenti kütüphanesinin biçimi desteklenmiyor")
    seen = set()
    for entry in entries:
        if not isinstance(entry, dict):
            raise ValueError('Eklenti kaydı bir nesne olmalı')
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,63}", entry.get("id", "")):
            raise ValueError("Geçersiz eklenti kimliği")
        if entry['id'] in seen:
            raise ValueError('Eklenti kimlikleri benzersiz olmalı')
        seen.add(entry['id'])
        if entry.get("kind") not in {"npm", "python", "http"}:
            raise ValueError("Desteklenmeyen eklenti kurulum türü")
        if not entry.get("source", "").startswith("https://"):
            raise ValueError("Eklenti için resmî HTTPS kaynak gerekli")
        if not isinstance(entry.get('required_env', []), list) or not all(isinstance(key, str) and re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', key) for key in entry.get('required_env', [])):
            raise ValueError('Geçersiz ortam değişkeni adı')
        if entry["kind"] != "http":
            if entry.get('bin') and not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]*', entry['bin']):
                raise ValueError('Eklenti giriş adı geçersiz')
            pattern = r"(?:@[a-z0-9_.-]+/)?[a-z0-9][a-z0-9_.-]*" if entry["kind"] == "npm" else r"[A-Za-z0-9][A-Za-z0-9_.-]*"
            if not re.fullmatch(pattern, entry.get("package", "")):
                raise ValueError("Paket adı kayıt deposundan yüklenebilir bir ad olmalı")
            if entry["kind"] == "python" and not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", entry.get("entry", "")):
                raise ValueError("Python eklentisinin giriş adı geçersiz")
            if not isinstance(entry.get("args", []), list) or not all(isinstance(a, str) and "\x00" not in a for a in entry.get("args", [])):
                raise ValueError("Eklenti argümanları bir metin dizisi olmalı")
            if not isinstance(entry.get("env", {}), dict) or not all(isinstance(k, str) and isinstance(v, str) for k, v in entry.get("env", {}).items()):
                raise ValueError("Eklenti ortam değerleri metin olmalı")
        else:
            validate_spec({'name': entry.get('name', entry['id']), 'url': entry.get('url'), 'header_env': entry.get('header_env', {})})
    return entries


def external_python() -> str | None:
    for name in ("python3", "python"):
        path = shutil.which(name)
        if path and (not getattr(sys, "frozen", False) or Path(path).resolve() != Path(sys.executable).resolve()):
            return path
    return None


def requirement(entry: dict) -> str:
    if entry.get('requirement'):
        return entry['requirement']
    kind = entry["kind"]
    missing = [name for name in entry.get('required_env', []) if not os.environ.get(name)]
    if missing:
        return 'Ortam değişkeni gerekli: ' + ', '.join(missing)
    if kind == "npm":
        return "Hazır · Node.js ve npm" if shutil.which("node") and shutil.which("npm") else "Node.js ve npm gerekli"
    if kind == "python":
        return "Hazır · Python" if external_python() else "Python 3.11+ gerekli"
    missing = [name for name in entry.get("header_env", {}).values() if not os.environ.get(name)]
    return "Ortam değişkeni gerekli: " + ", ".join(missing) if missing else "Hazır · uzak bağlantı"


def authentication_issue(entry: dict) -> str:
    """Check configured references only; this is not a remote login test."""
    variables = [*entry.get('required_env', []), *entry.get('header_env', {}).values()]
    missing = [name for name in variables if not os.environ.get(name)]
    if missing:
        return 'Ortam değişkeni gerekli: ' + ', '.join(dict.fromkeys(missing))
    variable = entry.get('header_env', {}).get('Authorization')
    if variable:
        prefix = entry.get('auth_prefix', 'Bearer') + ' '
        value = os.environ.get(variable, '')
        if not value.startswith(prefix) or not value[len(prefix):].strip():
            return variable + ' değeri ' + prefix.strip() + ' önekiyle tanımlanmalı.'
    return ''


def _npm_command(node: str, npm: str) -> list[str]:
    executable = Path(npm).resolve()
    if executable.suffix == ".js":
        return [node, str(executable)]
    # npm.cmd is a batch file on Windows. Launch its JS entry with Node so no
    # command shell interprets user-directory characters such as & or %.
    if os.name == "nt":
        script = executable.parent / "node_modules/npm/bin/npm-cli.js"
        if not script.is_file():
            raise RuntimeError("npm'nin Node giriş dosyası bulunamadı. Node.js LTS kurulumunu onar.")
        return [node, str(script)]
    return [npm]


def _execute(argv, *, cwd=None, cancel=None, timeout=600):
    """No shell; do not expose package logs or inherited credentials in errors."""
    with tempfile.TemporaryFile() as log:
        process = subprocess.Popen(list(argv), cwd=cwd, stdin=subprocess.DEVNULL,
                                   stdout=log, stderr=log, shell=False,
                                   creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        started = time.monotonic()
        try:
            while process.poll() is None:
                if cancel is not None and cancel.is_set():
                    raise InterruptedError("Eklenti kurulumu durduruldu")
                if time.monotonic() - started > timeout:
                    raise TimeoutError("Kurulum zaman aşımına uğradı. İnternetini kontrol edip yeniden dene.")
                time.sleep(.1)
            if process.returncode:
                raise RuntimeError(f"Paket kurulamadı (kod {process.returncode}). Gerekli çalışma ortamını ve internet bağlantısını kontrol et; sonra yeniden dene.")
        finally:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(3)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()


class ExtensionLibrary:
    def __init__(self, root: Path):
        self.root = Path(root).resolve()
        self.entries = load_catalog(self.root)
        self.base = self.root / "runtime/extensions"
        with _INSTALL_LOCKS_GUARD:
            self.lock = _INSTALL_LOCKS.setdefault(str(self.base), threading.Lock())

    def find(self, ident: str) -> dict:
        try:
            return next(item for item in self.entries if item["id"] == ident)
        except StopIteration as exc:
            raise ValueError("Eklenti kütüphanede bulunamadı") from exc

    def install(self, ident: str, workspace="", *, cancel=None, status=lambda _: None) -> dict:
        entry = self.find(ident)
        if not self.base.resolve().is_relative_to(self.root) or self.base.is_symlink():
            raise ValueError('Eklenti kurulum klasörü proje verilerinin içinde olmalı')
        # Validate the whole catalog even for direct service callers.
        directory = (self.base / entry["id"]).resolve()
        if not directory.is_relative_to(self.base.resolve()):
            raise ValueError("Geçersiz eklenti klasörü")
        work = Path(workspace).expanduser().resolve() if workspace else None
        if entry.get("workspace") and (work is None or not work.is_dir()):
            raise ValueError("Bu eklenti için bir proje klasörü seç")
        if not self.lock.acquire(blocking=False):
            raise RuntimeError("Başka bir eklenti kuruluyor; bitmesini bekle")
        try:
            if cancel is not None and cancel.is_set():
                raise InterruptedError("Eklenti kurulumu durduruldu")
            substitutions = {"{workspace}": str(work or ""), "{data}": str(directory)}
            def expand(value):
                for key, text in substitutions.items():
                    value = value.replace(key, text)
                return value
            spec = {"name": entry["name"], "library_id": ident, "enabled": False,
                    "transport": "http" if entry["kind"] == "http" else "stdio"}
            if entry["kind"] == "http":
                spec.update(url=entry["url"], header_env=entry.get("header_env", {}))
                return validate_spec(spec)
            self.base.mkdir(mode=0o700, parents=True, exist_ok=True)
            directory.mkdir(mode=0o700, parents=True, exist_ok=True)
            status("Çalışma ortamı hazırlanıyor…")
            args = [expand(a) for a in entry.get("args", [])]
            env = {k: expand(v) for k, v in entry.get("env", {}).items()}
            if entry["kind"] == "npm":
                node, npm = shutil.which("node"), shutil.which("npm")
                if not node or not npm:
                    raise RuntimeError("Node.js ve npm bulunamadı. nodejs.org üzerinden güncel LTS sürümünü kur.")
                status("Paket indiriliyor; kurulum betikleri kapalı…")
                _execute([*_npm_command(node, npm), "install", "--prefix", str(directory), "--ignore-scripts", "--no-audit", "--no-fund", "--save-exact", "--", entry["package"]], cancel=cancel)
                package_root = directory / "node_modules" / entry["package"]
                meta = json.loads((package_root / "package.json").read_text(encoding="utf-8"))
                bins = meta.get("bin", {})
                wanted_bin = entry.get('bin') or entry['package'].split('/')[-1]
                binary = bins if isinstance(bins, str) else bins.get(wanted_bin, next(iter(bins.values()), '') if len(bins) == 1 else '') if isinstance(bins, dict) else ''
                if not isinstance(binary, str) or not binary:
                    raise RuntimeError("Paket çalıştırılabilir MCP girişi sunmuyor")
                script = (package_root / binary).resolve()
                if not script.is_relative_to(package_root.resolve()) or not script.is_file():
                    raise ValueError("Paketin çalıştırma yolu geçersiz")
                spec.update(command=node, args=[str(script), *args], env=env,
                            installed_version=str(meta.get("version", "")))
            else:
                python = external_python()
                if not python:
                    raise RuntimeError("Python bulunamadı. python.org üzerinden Python 3.11+ kur.")
                venv = directory / "venv"
                _execute([python, "-m", "venv", str(venv)], cancel=cancel)
                bindir = venv / ("Scripts" if os.name == "nt" else "bin")
                interpreter = bindir / ("python.exe" if os.name == "nt" else "python")
                status("Paket ayrı Python ortamına indiriliyor…")
                _execute([str(interpreter), "-m", "pip", "install", "--disable-pip-version-check", "--only-binary=:all:", "--", entry["package"]], cancel=cancel)
                executable = bindir / (entry["entry"] + (".exe" if os.name == "nt" else ""))
                if not executable.is_file():
                    raise RuntimeError("Kurulum tamamlandı ancak MCP giriş dosyası bulunamadı")
                sites = [venv / "Lib/site-packages", *venv.glob("lib/python*/site-packages")]
                wanted = re.sub(r"[-_.]+", "-", entry["package"]).lower()
                version = next((dist.version for dist in importlib.metadata.distributions(path=[str(path) for path in sites if path.is_dir()])
                                if re.sub(r"[-_.]+", "-", dist.metadata.get("Name", "")).lower() == wanted), "installed")
                spec.update(command=str(executable), args=args, env=env, installed_version=version)
            spec["cwd"] = str(work or directory)
            spec = validate_spec(spec)
            manifest = directory / "installed.json"
            manifest.write_text(json.dumps({"id": ident, "package": entry["package"],
                                           "version": spec.get("installed_version", "registry"),
                                           "source": entry["source"]}, ensure_ascii=False, indent=2), encoding="utf-8")
            manifest.chmod(0o600)
            return spec
        finally:
            self.lock.release()
