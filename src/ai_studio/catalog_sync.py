"""Refresh curated HF file identities; remote data never changes model identity.

Only Hugging Face's model metadata endpoint is contacted. User files, prompts,
and chat history are not sent, and model weights are never downloaded here.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
from dataclasses import dataclass
from datetime import datetime, timezone
import json
import logging
from pathlib import Path
import threading

import httpx

from .engine.download import repository_metadata, file_info

LOG = logging.getLogger('ai_studio.catalog')
SAFE_FIELDS = {'remote_filename', 'verified_revision', 'sha256', 'size_bytes',
               'approx_gb', 'size_estimated', 'availability', 'checked_at', 'sync_error'}


def catalog_needs_refresh(cache_path: Path, max_age_hours: float = 24) -> bool:
    try:
        cache = json.loads(cache_path.read_text(encoding='utf-8'))
        checked = datetime.fromisoformat(cache['checked_at'])
        if checked.tzinfo is None:
            return True
        age = (datetime.now(timezone.utc) - checked).total_seconds()
        return not 0 <= age < max_age_hours * 3600
    except (OSError, ValueError, TypeError, KeyError):
        return True


@dataclass(frozen=True)
class CatalogSyncResult:
    models: list[dict]
    checked: int
    available: int
    errors: dict[str, str]
    checked_at: str


def _base_models(base: list[dict] | Path) -> list[dict]:
    models = json.loads(Path(base).read_text(encoding='utf-8')) if isinstance(base, (Path, str)) else base
    if not isinstance(models, list):
        raise ValueError('Model kataloğu geçersiz')
    return [dict(model) for model in models]


def load_catalog(base: list[dict] | Path, cache_path: Path) -> list[dict]:
    models = _base_models(base)
    try:
        cache = json.loads(cache_path.read_text(encoding='utf-8'))
        entries = cache.get('models', {})
        if not isinstance(entries, dict):
            return models
    except (OSError, ValueError, AttributeError):
        return models
    for model in models:
        entry = entries.get(model.get('id'))
        if (isinstance(entry, dict) and entry.get('repo') == model.get('repo')
                and entry.get('filename') == model.get('filename')
                and entry.get('revision', 'main') == model.get('revision', 'main')):
            model.update({key: entry[key] for key in SAFE_FIELDS if key in entry})
    return models


def _readable_error(exc):
    if isinstance(exc, httpx.HTTPStatusError):
        code = exc.response.status_code
        if code in {401, 403}:
            return 'Depo özel, kaldırılmış veya erişim koşulu istiyor; yayıncının model kartını kontrol et.'
        if code == 404:
            return 'Depo veya sürüm bulunamadı; yüklü dosyaların korunuyor.'
    if isinstance(exc, httpx.HTTPError):
        return 'Yayıncıya ulaşılamadı. Son doğrulanmış kayıtlar korunuyor; bağlantı gelince yeniden dene.'
    return str(exc)


def refresh_catalog(base: list[dict] | Path, cache_path: Path, cancel=None,
                    progress=lambda done, total, text: None) -> CatalogSyncResult:
    cancel = cancel or threading.Event()
    def check_cancel():
        if cancel.is_set():
            raise InterruptedError('Katalog yenileme durduruldu; önceki kayıtlar korunuyor.')
    check_cancel()
    models = load_catalog(base, cache_path)
    checked_at = datetime.now(timezone.utc).isoformat(timespec='seconds')
    groups = {}
    for model in models:
        groups.setdefault((model['repo'], model.get('revision', 'main')), []).append(model)
    errors, done = {}, 0
    def fetch(repo, revision):
        # Each bounded background task owns its client. Cancelling the UI never
        # waits for a shared client's close or a blocked socket read to finish.
        check_cancel()
        with httpx.Client(follow_redirects=True, trust_env=True,
                          timeout=httpx.Timeout(20, connect=10, read=20, pool=10)) as client:
            return repository_metadata(client, repo, cancel, lambda _: None, revision)
    pool = ThreadPoolExecutor(max_workers=4, thread_name_prefix='catalog')
    try:
        futures = {pool.submit(fetch, repo, revision): (repo, rows)
                   for (repo, revision), rows in groups.items()}
        pending = set(futures)
        while pending:
            check_cancel()
            completed, pending = wait(pending, timeout=.1, return_when=FIRST_COMPLETED)
            for future in completed:
                check_cancel()
                repo, rows = futures[future]
                try:
                    metadata = future.result()
                except InterruptedError:
                    raise
                except (ValueError, OSError, httpx.HTTPError) as exc:
                    error = _readable_error(exc)
                    unavailable = isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code in {401, 403, 404}
                    for model in rows:
                        model.update(availability='unavailable' if unavailable else 'unreachable',
                                     checked_at=checked_at, sync_error=error)
                        errors[model['id']] = error
                else:
                    for model in rows:
                        try:
                            info = file_info(metadata, repo, model.get('remote_filename', model['filename']),
                                             model.get('filename_aliases', ()), model['filename'])
                        except ValueError as exc:
                            model.update(availability='unavailable', checked_at=checked_at, sync_error=str(exc))
                            errors[model['id']] = str(exc)
                        else:
                            model.update(remote_filename=info['remote_filename'], verified_revision=info['revision'],
                                         sha256=info['sha256'], size_bytes=info['size'],
                                         approx_gb=round(info['size'] / 1_000_000_000, 3), size_estimated=False,
                                         availability='available', checked_at=checked_at, sync_error='')
                done += len(rows)
                progress(done, len(models), repo)
    finally:
        # The metadata tasks never publish cache data. Pending requests may
        # finish within their timeout after Cancel, without a late cache write.
        pool.shutdown(wait=False, cancel_futures=True)
    check_cancel()
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    temp = cache_path.with_suffix(cache_path.suffix + '.tmp')
    try:
        temp.write_text(json.dumps({'schema': 1, 'checked_at': checked_at,
                                   'models': {m['id']: {k: v for k, v in m.items()
                                             if k in SAFE_FIELDS | {'repo', 'filename', 'revision'}} for m in models}},
                                   ensure_ascii=False, indent=2), encoding='utf-8')
        check_cancel()
        temp.replace(cache_path)
    finally:
        temp.unlink(missing_ok=True)
    available = sum(m.get('availability') == 'available' for m in models)
    LOG.info('Catalog checked: %d, available: %d, errors: %d', len(models), available, len(errors))
    return CatalogSyncResult(models, len(models), available, errors, checked_at)
