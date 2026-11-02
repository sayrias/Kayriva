"""Local model discovery without copying weights or relying on a dialog filter."""
from __future__ import annotations

from dataclasses import dataclass
import json
import os
import re
from pathlib import Path
from urllib.parse import unquote, urlsplit


@dataclass(frozen=True)
class LocalModel:
    path: Path
    backend: str
    name: str
    projector: Path | None = None


def find_projector(model: Path) -> Path | None:
    """Use a clearly matching local projector, never an arbitrary other VLM's."""
    if not model.is_file():
        return None
    prefix = re.split(r'[-.](?:UD-|IQ\d|Q\d|F16|BF16)', model.stem, maxsplit=1, flags=re.I)[0].casefold()
    candidates = [p for p in model.parent.iterdir() if p.is_file()
                  and p.suffix.lower() == '.gguf' and p.name.lower().startswith('mmproj')]
    matching = [p for p in candidates if prefix in p.stem.casefold()]
    if len(matching) == 1:
        return matching[0]
    mains = [p for p in model.parent.iterdir() if p.is_file() and p.suffix.lower() == '.gguf'
             and not p.name.lower().startswith(('mmproj', 'mtp-'))]
    if len(candidates) == 1 and len(mains) == 1:
        return candidates[0]
    return None


def model_file_filter() -> str:
    # Native dialogs on Linux may treat globs as case-sensitive. Always expose
    # an unrestricted choice too, for extensionless GGUF and drag/drop paths.
    return ('Model dosyaları (*.gguf *.GGUF *.Gguf *.safetensors *.SAFETENSORS '
            'config.json *.index.json);;Tüm dosyalar (*)')


def normalize_model_path(raw: str | Path, search_root: Path | None = None) -> Path:
    value = str(raw).strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        value = value[1:-1]
    if not value or any(c in value for c in ('\0', '\n', '\r')):
        raise ValueError('Bir model dosyasının veya model klasörünün tam yolunu gir.')
    if value.lower().startswith('file:'):
        parsed = urlsplit(value)
        if parsed.netloc not in {'', 'localhost'} or parsed.query or parsed.fragment:
            raise ValueError('Yalnızca bu bilgisayardaki file:// yolları eklenebilir.')
        value = unquote(parsed.path)
        if os.name == 'nt' and len(value) > 2 and value[0] == '/' and value[2] == ':':
            value = value[1:]
    elif '://' in value:
        raise ValueError('Bu alan indirme bağlantısı değil, bilgisayarındaki model yolu içindir.')
    path = Path(os.path.expandvars(value)).expanduser()
    if not path.is_absolute() and search_root is not None:
        path = Path(search_root) / path
    return path.resolve()


def _transformers_model(directory: Path) -> LocalModel | None:
    config = directory / 'config.json'
    if not config.is_file():
        return None
    try:
        data = json.loads(config.read_text(encoding='utf-8'))
    except (ValueError, OSError) as exc:
        raise ValueError('Model klasöründeki config.json okunamadı veya geçersiz.') from exc
    if not isinstance(data, dict) or not (data.get('model_type') or data.get('architectures')):
        raise ValueError('config.json bir Transformers model yapılandırması değil.')
    entries = list(directory.iterdir())
    weights = [p for p in entries if p.is_file() and (p.suffix.lower() == '.safetensors' or
               p.name.startswith('pytorch_model') and p.suffix.lower() == '.bin')]
    if not weights:
        raise ValueError('Model klasöründe ağırlık bulunamadı. config.json ve safetensors dosyalarını birlikte indir.')
    if not any((directory / name).is_file() for name in ('tokenizer.json', 'tokenizer.model', 'spiece.model', 'vocab.json', 'vocab.txt')):
        raise ValueError('Model tokenizer dosyaları eksik. Yalnızca safetensors yerine bütün yerel model klasörünü indir.')
    for index in directory.glob('*.index.json'):
        try:
            mapping = json.loads(index.read_text(encoding='utf-8')).get('weight_map', {})
            if not isinstance(mapping, dict):
                raise ValueError('Geçersiz ağırlık indeksi')
            for name in set(mapping.values()):
                part = directory / name
                if not isinstance(name, str) or part.resolve().parent != directory.resolve() or not part.is_file():
                    raise ValueError('Model parçaları eksik veya geçersiz; bütün safetensors parçalarını indir.')
        except (OSError, TypeError, json.JSONDecodeError) as exc:
            raise ValueError('Model ağırlık indeksi okunamadı.') from exc
    return LocalModel(directory, 'transformers', directory.name)


def resolve_model_path(raw: str | Path, search_root: Path | None = None) -> LocalModel:
    """Detect a real GGUF file or complete local Transformers directory.

    Pasted URLs, mixed-case extensions, config/weight selections and a folder
    containing one GGUF all work independently of the selected engine setting.
    """
    path = normalize_model_path(raw, search_root)
    if not path.exists():
        raise ValueError(f'Model yolu bulunamadı: {path}. Arşiv içindeki dosyayı önce çıkar; model dosyasını veya klasörünü seç.')
    try:
        if path.is_dir():
            result = _transformers_model(path)
            if result:
                return result
            files = [p for p in path.iterdir() if p.is_file() and p.suffix.lower() == '.gguf'
                     and not p.name.lower().startswith(('mmproj', 'mtp-'))]
            if len(files) == 1:
                return resolve_model_path(files[0])
            if files:
                raise ValueError('Bu klasörde birden fazla GGUF var. Kullanmak istediğin GGUF dosyasını seç.')
            raise ValueError('Bu klasörde GGUF veya config.json ile model ağırlıkları bulunamadı.')
        if path.suffix.lower() in {'.safetensors', '.json', '.bin'}:
            result = _transformers_model(path.parent)
            if result:
                return result
        with path.open('rb') as stream:
            magic = stream.read(4)
        if magic != b'GGUF':
            if path.suffix.lower() in {'.zip', '.gz', '.7z', '.tar'}:
                raise ValueError('Bu bir arşiv. İçindeki model dosyalarını çıkarıp yeniden seç.')
            raise ValueError('Dosya GGUF biçiminde değil. GGUF dosyasını veya tam Transformers model klasörünü seç.')
        if path.name.lower().startswith(('mmproj', 'mtp-')):
            raise ValueError('Bu yardımcı model dosyası. Asıl sohbet GGUF dosyasını seç.')
        split = re.fullmatch(r'(.+)-(\d{5})-of-(\d{5})\.gguf', path.name, flags=re.I)
        if split:
            count = int(split[3])
            if not 1 <= count <= 256:
                raise ValueError('GGUF parça sayısı geçersiz.')
            parts = [path.with_name(f'{split[1]}-{n:05}-of-{count:05}{path.suffix}') for n in range(1, count + 1)]
            if any(not part.is_file() for part in parts):
                raise ValueError('GGUF parçaları eksik. Aynı modelin bütün parçalarını aynı klasöre indir.')
            path = parts[0]
        return LocalModel(path, 'gguf', path.stem, find_projector(path))
    except OSError as exc:
        raise ValueError(f'Model dosyası okunamadı: {path}. Dosya erişim izinlerini kontrol et.') from exc


def discover_local_models(directory: Path) -> list[LocalModel]:
    """Bounded one-level discovery; never recurse into a user's whole disk."""
    if not directory.is_dir():
        return []
    found = {}
    for path in sorted(directory.iterdir(), key=lambda p: p.name.casefold()):
        if not (path.is_dir() or path.suffix.lower() == '.gguf'):
            continue
        try:
            model = resolve_model_path(path)
            found[model.path] = model
        except (ValueError, OSError):
            continue
    return list(found.values())
