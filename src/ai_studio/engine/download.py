from __future__ import annotations

import hashlib
import json
import logging
import re
import shutil
import time
from pathlib import Path, PurePosixPath
from urllib.parse import quote

import httpx

LOG = logging.getLogger('ai_studio.download')
ATTEMPTS = 4


def digest(path: Path, cancel=None, progress=lambda *_: None):
    h = hashlib.sha256()
    size, done = path.stat().st_size, 0
    progress(0, size)
    with path.open('rb') as f:
        while chunk := f.read(4 * 1024 * 1024):
            if cancel and cancel.is_set():
                raise InterruptedError('Doğrulama durduruldu; dosya korundu')
            h.update(chunk)
            done += len(chunk)
            progress(done, size)
    return h.hexdigest()


def retryable(exc):
    return isinstance(exc, httpx.TransportError) or isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code in {408,429,500,502,503,504}


def pause(cancel, attempt, status):
    delay = min(8, 2**attempt)
    status(f'Bağlantı kesildi · {delay} sn sonra yeniden deneniyor ({attempt+2}/{ATTEMPTS})')
    if cancel.wait(delay):
        raise InterruptedError('İndirme durduruldu; kısmi dosya korundu')


def valid_remote_filename(filename):
    return (isinstance(filename, str) and bool(filename) and '\\' not in filename
            and not any(ord(c) < 32 for c in filename)
            and not PurePosixPath(filename).is_absolute()
            and all(p not in {'', '.', '..'} for p in filename.split('/')))


def validate_info(info, repo, filename):
    return bool(isinstance(info, dict) and info.get('repo') == repo and info.get('filename') == filename
                and isinstance(info.get('size'), int) and info['size'] > 0
                and isinstance(info.get('revision'), str) and re.fullmatch(r'[\w.-]+', info['revision'])
                and isinstance(info.get('sha256'), str) and re.fullmatch(r'[a-fA-F0-9]{64}', info['sha256'])
                and valid_remote_filename(info.get('remote_filename', filename)))


def select_remote_file(metadata, filename, aliases=()):
    """Resolve casing/folder changes, never silently choose a different quant."""
    files = [f for f in metadata.get('siblings', [])
             if isinstance(f, dict) and valid_remote_filename(f.get('rfilename'))]
    names = [filename, *(a for a in aliases if isinstance(a, str) and valid_remote_filename(a))]
    for name in names:
        exact = next((f for f in files if f['rfilename'] == name), None)
        if exact:
            return exact
    for name in names:
        candidates = [f for f in files if f['rfilename'].casefold() == name.casefold()]
        if len(candidates) == 1:
            return candidates[0]
    # A publisher may move the same named file into a quantization subfolder.
    # Ambiguity is rejected instead of picking the first model from a repo.
    basenames = {PurePosixPath(name).name.casefold() for name in names}
    candidates = [f for f in files if PurePosixPath(f['rfilename']).name.casefold() in basenames]
    if len(candidates) == 1:
        return candidates[0]
    if candidates:
        raise ValueError('Depoda aynı adlı birden fazla dosya var; doğru dosyayı model kartından seç.')
    raise ValueError('Bu kuantizasyon dosyası artık depoda yok. Kütüphaneyi yenile veya yayıncıdan yerel GGUF ekle; başka bir model otomatik seçilmedi.')


def repository_metadata(client, repo, cancel, status=lambda _: None, revision='main'):
    if not re.fullmatch(r'[\w.-]+/[\w.-]+', repo):
        raise ValueError('Geçersiz Hugging Face deposu')
    if not isinstance(revision, str) or not re.fullmatch(r'[\w./-]{1,128}', revision):
        raise ValueError('Geçersiz model sürümü')
    for attempt in range(ATTEMPTS):
        if cancel.is_set(): raise InterruptedError('İndirme durduruldu')
        status(f'Model bilgileri alınıyor · deneme {attempt+1}/{ATTEMPTS}')
        try:
            started, data = time.monotonic(), bytearray()
            suffix = '' if revision == 'main' else '/revision/' + quote(revision, safe='')
            with client.stream('GET', f'https://huggingface.co/api/models/{repo}{suffix}', params={'blobs':'true'}) as response:
                response.raise_for_status()
                for chunk in response.iter_bytes(64*1024):
                    if cancel.is_set(): raise InterruptedError('İndirme durduruldu')
                    if time.monotonic()-started > 30: raise httpx.ReadTimeout('Metadata deadline', request=response.request)
                    data.extend(chunk)
                    if len(data)>16*1024*1024: raise ValueError('Model bilgisi boyutu sınırı aştı')
            metadata = json.loads(data)
            if not isinstance(metadata, dict) or not isinstance(metadata.get('siblings'), list):
                raise ValueError('Yayıncının model listesi geçersiz; sonra yeniden dene.')
            return metadata
        except (httpx.HTTPError, OSError) as exc:
            if not retryable(exc) or attempt==ATTEMPTS-1: raise
            LOG.warning('Metadata retry: %s, attempt %d',type(exc).__name__,attempt+1)
            pause(cancel,attempt,status)


def file_info(metadata, repo, filename, aliases=(), local_filename=None):
    entry = select_remote_file(metadata, filename, aliases)
    lfs = entry.get('lfs') or {}
    if not isinstance(lfs, dict):
        raise ValueError('Yayıncının dosya doğrulama bilgisi geçersiz.')
    info = {'repo': repo, 'filename': local_filename or PurePosixPath(filename).name,
            'remote_filename': entry['rfilename'], 'revision': metadata.get('sha'),
            'sha256': lfs.get('sha256'), 'size': entry.get('size') or lfs.get('size')}
    if not validate_info(info, repo, info['filename']):
        raise ValueError('Dosyanın SHA-256 doğrulama bilgisi alınamadı; doğrulanmadan kurulmaz.')
    return info


def metadata_info(client, repo, filename, cancel, status, revision='main', aliases=(), local_filename=None):
    metadata = repository_metadata(client, repo, cancel, status, revision)
    return file_info(metadata, repo, filename, aliases, local_filename)


def download_model(model, target: Path, cancel, progress=lambda *_: None, status=lambda _: None):
    """Verified, commit-pinned download with cancellable retries and resumable data."""
    repo, filename = model['repo'], model['filename']
    remote_filename = model.get('remote_filename', filename)
    if not re.fullmatch(r'[\w.-]+/[\w.-]+',repo) or not valid_remote_filename(filename) or '/' in filename or Path(filename).name!=filename or not filename.lower().endswith('.gguf') or not valid_remote_filename(remote_filename):
        raise ValueError('Geçersiz Hugging Face GGUF modeli')
    target.mkdir(parents=True,exist_ok=True)
    final = target/filename
    partial = final.with_suffix(final.suffix + '.part')
    manifest = final.with_suffix(final.suffix + '.part.json')
    # A previous verified HF metadata response pins the same immutable commit.
    cached = None
    existing_manifest = manifest if manifest.exists() else final.with_suffix(final.suffix + '.metadata.json')
    if existing_manifest.exists():
        try:
            candidate=json.loads(existing_manifest.read_text())
            if validate_info(candidate,repo,filename): cached=candidate
        except (ValueError,OSError): pass
    try:
        with httpx.Client(follow_redirects=True,trust_env=True,timeout=httpx.Timeout(20,connect=10,read=20,pool=10)) as client:
            if cached:
                info=cached
                status('Doğrulama bilgisi hazır · kaydedilen sürümden devam ediliyor')
            else:
                info=metadata_info(client,repo,remote_filename,cancel,status,
                                   model.get('revision', 'main'), model.get('filename_aliases', ()), filename)
            sha,size,revision=info['sha256'],info['size'],info['revision']
            if final.exists():
                status('SHA-256 doğrulanıyor…')
                if final.stat().st_size==size and digest(final,cancel,progress)==sha:
                    status('Model doğrulandı')
                    return final
                raise ValueError('Aynı isimli dosya farklı; dosyayı taşıdıktan sonra yeniden dene')
            if not cached and partial.exists(): partial.unlink()
            manifest.write_text(json.dumps(info),encoding='utf-8')
            for attempt in range(ATTEMPTS):
                if cancel.is_set(): raise InterruptedError('İndirme durduruldu; kısmi dosya korundu')
                offset=partial.stat().st_size if partial.exists() else 0
                if offset>size:
                    partial.unlink(); offset=0
                if shutil.disk_usage(target).free<size-offset+128*1024*1024: raise OSError('İndirme için yeterli disk alanı yok')
                if offset==size: break
                status('İndiriliyor · kaldığı yerden devam edebilir')
                progress(offset,size)
                try:
                    headers={'Range':f'bytes={offset}-'} if offset else {}
                    url=f'https://huggingface.co/{repo}/resolve/{revision}/{quote(info.get("remote_filename", remote_filename), safe="/")}'
                    with client.stream('GET',url,headers=headers) as response:
                        response.raise_for_status()
                        if offset and response.status_code==206:
                            match=re.fullmatch(r'bytes (\d+)-(\d+)/(\d+)',response.headers.get('content-range',''))
                            if not match or int(match[1])!=offset or int(match[3])!=size or int(match[2])>=size: raise ValueError('Sunucu devam konumunu doğrulamadı')
                        elif response.status_code==200:
                            offset=0
                        else: raise ValueError('Beklenmeyen indirme yanıtı')
                        with partial.open('ab' if offset else 'wb') as f:
                            for chunk in response.iter_bytes(1024*1024):
                                if cancel.is_set(): raise InterruptedError('İndirme durduruldu; kısmi dosya korundu')
                                if offset+len(chunk)>size: raise ValueError('Dosya beklenen boyutu aştı')
                                f.write(chunk); offset+=len(chunk)
                                progress(offset,size)
                    if offset!=size: raise httpx.ReadError('Incomplete download')
                    break
                except (httpx.HTTPError,OSError) as exc:
                    if cached and isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code == 404 and attempt < ATTEMPTS-1:
                        # A removed old commit can invalidate a saved resume URL.
                        # Resolve the requested identity again, and reuse bytes only
                        # when the new metadata confirms exactly the same payload.
                        status('Kaydedilen sürüm taşınmış · yayıncıdaki dosya yeniden çözülüyor')
                        fresh = metadata_info(client, repo, remote_filename, cancel, status,
                                              model.get('revision', 'main'), model.get('filename_aliases', ()), filename)
                        if (fresh['sha256'], fresh['size']) != (sha, size):
                            partial.unlink(missing_ok=True)
                        info = fresh
                        sha, size, revision = info['sha256'], info['size'], info['revision']
                        manifest.write_text(json.dumps(info), encoding='utf-8')
                        cached = None
                        continue
                    if not retryable(exc) or attempt==ATTEMPTS-1: raise
                    LOG.warning('Download retry: %s, attempt %d',type(exc).__name__,attempt+1)
                    pause(cancel,attempt,status)
            status('SHA-256 doğrulanıyor…')
            if partial.stat().st_size!=size or digest(partial,cancel,progress)!=sha:
                partial.unlink(missing_ok=True); manifest.unlink(missing_ok=True)
                raise ValueError('Doğrulama başarısız; bozuk dosya kaldırıldı. Yeniden indirebilirsin.')
            with partial.open('rb') as f:
                if f.read(4)!=b'GGUF':
                    partial.unlink(missing_ok=True); manifest.unlink(missing_ok=True)
                    raise ValueError('Dosya GGUF değil; kaldırıldı')
            partial.replace(final)
            manifest.replace(final.with_suffix(final.suffix + '.metadata.json'))
            LOG.info('Model download verified: %s / %s',repo,filename)
            status('Model indirildi ve doğrulandı')
            return final
    except httpx.HTTPError as exc:
        LOG.error('Download stopped: %s',type(exc).__name__)
        if isinstance(exc,httpx.HTTPStatusError):
            code=exc.response.status_code
            if code in {401,403}: raise RuntimeError(f'Model erişimi reddedildi ({code}). Yayıncının erişim koşullarını kontrol et.') from exc
            if code==404: raise RuntimeError('Model dosyası bulunamadı (404); model kartını kontrol et.') from exc
        raise RuntimeError('Güvenli bağlantı kurulamadı veya kesildi. Kısmi dosya korundu; Yeniden dene ile devam et. Ayrıntı: runtime/logs/app.log') from exc
