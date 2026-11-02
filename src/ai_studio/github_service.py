"""GitHub operations through the user's GitHub CLI session.

Publishing uses only a reviewed source snapshot. It never stages the source
project, changes its remotes, or silently uploads existing Git history.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit


EXCLUDED_PARTS = {".git", ".hg", ".svn", ".venv", "venv", "env", "node_modules", "__pycache__",
                  ".cache", "runtime", "dist", "build", ".aws", ".ssh", ".gnupg", ".codex", ".agents"}
EXCLUDED_SUFFIXES = {".gguf", ".safetensors", ".bin", ".pt", ".pth", ".onnx", ".dll", ".so", ".exe",
                     ".pyc", ".pyo", ".sqlite", ".sqlite3", ".db", ".pem", ".key", ".p12", ".pfx"}
SECRET_PATTERN = re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|\b(?:gh[pousr]_[A-Za-z0-9_]{20,}|github_pat_[A-Za-z0-9_]{20,}|sk-[A-Za-z0-9_-]{24,})\b")
NAME_PATTERN = re.compile(r"(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?/)?[A-Za-z0-9_.-]{1,100}\Z")


@dataclass(frozen=True)
class PublishPreview:
    root: Path
    files: tuple[tuple[str, int, str], ...]
    excluded: tuple[tuple[str, str], ...]

    @property
    def total_bytes(self):
        return sum(size for _, size, _ in self.files)


def repository_name(value: str) -> str:
    name = value.strip()
    if not NAME_PATTERN.fullmatch(name) or name.split("/")[-1] in {".", ".."} or name.startswith("-"):
        raise ValueError("Depo adında yalnızca harf, sayı, nokta, tire ve alt çizgi kullan; istersen sahip/depo biçimini seç")
    return name


def github_url(value: str) -> str:
    parsed = urlsplit(str(value))
    if parsed.scheme != "https" or parsed.hostname != "github.com" or parsed.username or parsed.password or parsed.port not in {None, 443}:
        raise ValueError("Geçerli bir github.com HTTPS adresi gerekli")
    return value


def exclusion(path: str) -> str | None:
    parts = Path(path).parts
    lower = [part.lower() for part in parts]
    leaf = lower[-1] if lower else ""
    if any(part in EXCLUDED_PARTS for part in lower):
        return "Çalışma verisi, bağımlılık veya derleme çıktısı"
    if leaf in {".env.example", ".env.sample", ".env.template"}:
        return None
    if leaf == ".env" or leaf.startswith(".env.") or any(word in leaf for word in ("credentials", "secret", "token", "password")):
        return "Kimlik bilgisi içerebilir"
    if leaf.startswith("id_rsa") or leaf.startswith("id_ed25519") or leaf.endswith((".log", ".egg-info")):
        return "Özel anahtar veya yerel kayıt"
    if Path(leaf).suffix in EXCLUDED_SUFFIXES:
        return "Model, çalıştırılabilir dosya veya kişisel veri"
    return None


class GitHubService:
    def __init__(self, runner=None):
        self.runner = runner or subprocess.run

    def command(self, argv, *, cwd=None, check=True, timeout=120, binary=False):
        env = os.environ.copy()
        env.update(GH_PROMPT_DISABLED="1", GIT_TERMINAL_PROMPT="0", GIT_LITERAL_PATHSPECS="1")
        try:
            result = self.runner(list(argv), cwd=cwd, env=env, stdin=subprocess.DEVNULL,
                                 capture_output=True, text=not binary, timeout=timeout, shell=False,
                                 creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        except FileNotFoundError as exc:
            raise RuntimeError("Git veya GitHub CLI bulunamadı. git-scm.com ve cli.github.com üzerinden kur.") from exc
        except subprocess.TimeoutExpired as exc:
            raise TimeoutError("GitHub işlemi zaman aşımına uğradı. Bağlantını kontrol edip yeniden dene.") from exc
        if check and result.returncode:
            raise RuntimeError(f"GitHub işlemi tamamlanamadı (kod {result.returncode}). Oturumunu, depo adını ve erişim izinlerini kontrol et.")
        return result

    def account(self) -> dict:
        if not shutil.which("gh"):
            return {"installed": False, "authenticated": False, "login": ""}
        status = self.command(["gh", "auth", "status", "--hostname", "github.com"], check=False, timeout=30)
        if status.returncode:
            return {"installed": True, "authenticated": False, "login": ""}
        login = self.command(["gh", "api", "user", "--jq", ".login"], timeout=30).stdout.strip()
        return {"installed": True, "authenticated": bool(login), "login": login}

    def repositories(self, limit=50) -> list[dict]:
        raw = self.command(["gh", "repo", "list", "--limit", str(min(100, max(1, int(limit)))),
                            "--json", "nameWithOwner,url,description,isPrivate,updatedAt"]).stdout
        data = json.loads(raw)
        if not isinstance(data, list):
            raise ValueError("GitHub beklenmeyen bir depo listesi döndürdü")
        return [{**row, "url": github_url(row["url"])} for row in data]

    def create(self, name: str, description="", private=True) -> str:
        name = repository_name(name)
        args = ["gh", "repo", "create", name, "--private" if private else "--public"]
        if description.strip():
            args += ["--description", description.strip()[:1000]]
        self.command(args)
        raw = self.command(["gh", "repo", "view", name, "--json", "url"]).stdout
        return github_url(json.loads(raw)["url"])

    def _candidate_paths(self, root: Path) -> list[str]:
        # An independent temporary Git directory makes Git's actual ignore rules
        # work without creating .git or changing the project's index.
        with tempfile.TemporaryDirectory(prefix="kayriva-preview-") as temp:
            git_dir = Path(temp) / "index.git"
            self.command(["git", "init", "--bare", "--quiet", str(git_dir)])
            output = self.command(["git", "--git-dir", str(git_dir), "--work-tree", str(root),
                                   "ls-files", "--others", "--exclude-standard", "-z"], binary=True).stdout
        return sorted(os.fsdecode(item) for item in output.split(b"\0") if item)

    def preview(self, workspace: str | Path) -> PublishPreview:
        root = Path(workspace).expanduser().resolve()
        if not root.is_dir():
            raise ValueError("Önce yayınlamak istediğin proje klasörünü seç")
        candidates = self._candidate_paths(root)
        included, excluded, total = [], [], 0
        if len(candidates) > 12000:
            raise ValueError("Proje çok fazla dosya içeriyor. .gitignore ile bağımlılık ve çıktıları hariç tut.")
        for name in candidates:
            candidate = root / name
            reason = exclusion(name)
            if candidate.is_symlink() or not candidate.resolve().is_relative_to(root):
                reason = "Sembolik bağlantı veya proje dışındaki dosya"
            if reason:
                excluded.append((name, reason))
                continue
            if not candidate.is_file():
                continue
            size = candidate.stat().st_size
            if size > 25 * 1024 * 1024:
                excluded.append((name, "25 MB dosya sınırını aşıyor"))
                continue
            content = candidate.read_bytes()
            if SECRET_PATTERN.search(content):
                excluded.append((name, "Özel anahtar veya erişim anahtarı bulundu"))
                continue
            total += len(content)
            if total > 100 * 1024 * 1024 or len(included) >= 2000:
                raise ValueError("Kaynak önizlemesi 2000 dosya / 100 MB sınırını aşıyor. .gitignore kapsamını daralt.")
            included.append((name, len(content), hashlib.sha256(content).hexdigest()))
        if not included:
            raise ValueError("Yüklenebilecek kaynak dosya bulunamadı. Projeni ve .gitignore kurallarını kontrol et.")
        return PublishPreview(root, tuple(included), tuple(excluded))

    def publish(self, preview: PublishPreview, name: str, description="", private=True, *, selected=None, status=lambda _: None) -> str:
        name = repository_name(name)
        expected = {name: (size, digest) for name, size, digest in preview.files}
        choices = tuple(expected) if selected is None else tuple(dict.fromkeys(selected))
        if not choices or any(path not in expected for path in choices):
            raise ValueError("Yalnızca önizlemede görülen kaynak dosyaları seçilebilir")
        with tempfile.TemporaryDirectory(prefix="kayriva-publish-") as temp:
            snapshot = Path(temp)
            status("Seçilen dosyalar doğrulanıyor…")
            for relative in choices:
                source = preview.root / relative
                if source.is_symlink() or not source.resolve().is_relative_to(preview.root) or exclusion(relative):
                    raise ValueError("Bir dosyanın yolu değişti. Önizlemeyi yenile.")
                content = source.read_bytes()
                size, digest = expected[relative]
                if len(content) != size or hashlib.sha256(content).hexdigest() != digest:
                    raise ValueError("Proje dosyaları önizlemeden sonra değişti. Önizlemeyi yenile.")
                target = snapshot / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(content)
            self.command(["git", "init", "--quiet", "--initial-branch=main", str(snapshot)])
            self.command(["git", "-C", str(snapshot), "add", "--all"])
            self.command(["git", "-C", str(snapshot), "-c", "user.name=Kayriva", "-c", "user.email=kayriva@users.noreply.github.com",
                          "-c", "core.hooksPath=" + str(snapshot / ".git/no-hooks"), "-c", "commit.gpgSign=false",
                          "commit", "--quiet", "-m", "Proje kaynaklarını ekle"])
            status("Yeni depo oluşturuluyor ve kaynaklar yükleniyor…")
            args = ["gh", "repo", "create", name, "--private" if private else "--public",
                    "--source", str(snapshot), "--remote", "origin", "--push"]
            if description.strip():
                args += ["--description", description.strip()[:1000]]
            try:
                self.command(args, cwd=snapshot, timeout=300)
            except RuntimeError as exc:
                raise RuntimeError("Yükleme tamamlanamadı. GitHub'da depo oluşturulmuş olabilir; yeniden denemeden önce depo listeni yenile ve git kimlik doğrulamanı kontrol et.") from exc
            raw = self.command(["gh", "repo", "view", name, "--json", "url"]).stdout
            return github_url(json.loads(raw)["url"])
