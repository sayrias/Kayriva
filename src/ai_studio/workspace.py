from __future__ import annotations

import json
import hashlib
import os
import tempfile
import re
from pathlib import Path


def root_output_requested(query):
    """A single report in the current project doesn't imply a new directory."""
    query=query.casefold()
    if re.search(r'[\w.-]+/[\w./-]+\.[\w]+',query):
        return False  # Explicit nested file path.
    if re.search(r'(?:yeni|alt)\s+(?:bir\s+)?klasör|klasör\w*\s+(?:oluştur|aç)|dizin\w*\s+oluştur',query):
        return False
    return bool(re.search(r'(?:bir|bi|tek)\s+dosya\s*(?:oluştur|hazırla|yaz|kaydet)|(?:proje|klasör)\w*.{0,55}dosya\s*(?:oluştur|hazırla|yaz|kaydet)',query))


def root_output_arguments(root, name, args):
    if name=='workspace_mkdir':
        raise ValueError('Bu istek için yeni klasör gerekmiyor. Dosyayı doğrudan proje kökünde workspace_write ile oluştur.')
    if name=='workspace_write' and args.get('mode')=='create':
        path=resolve_file(root,args['path'])
        if path.is_dir():raise ValueError('Bir dosya adı ve uzantısı kullan; seçilen yol klasör.')
        return {**args,'path':path.name}
    return args


def resolve_file(root, relative):
    root = Path(root).resolve()
    if not isinstance(relative,str) or not relative or Path(relative).is_absolute():
        raise ValueError('Proje içinde göreli bir dosya yolu kullan')
    path = (root / relative).resolve()
    if not path.is_relative_to(root):
        raise ValueError("Dosya çalışma klasörünün dışında")
    # Keep application/credential and VCS internals out of model context.
    if any(p in {".git", ".aws", ".codex", ".ssh", "runtime", ".venv", "node_modules"} or p.startswith('.env') for p in path.relative_to(root).parts):
        raise ValueError("Bu özel/sistem klasörüne araç erişimi kapalı")
    return path


WORKSPACE_TOOLS = [
    {"type": "function", "function": {"name": "workspace_list", "description": "Seçili çalışma klasöründeki dosyaları listele.", "parameters": {"type": "object", "properties": {}, "additionalProperties": False}}},
    {"type": "function", "function": {"name": "workspace_read", "description": "Çalışma klasöründeki bir metin dosyasını oku.", "parameters": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"], "additionalProperties": False}}},
    {"type":"function","function":{"name":"workspace_search","description":"Proje dosyalarının içinde düz metin ara. Kod incelemesinde ilgili dosya ve satırları bul; düzenli ifade veya komut çalıştırmaz.","parameters":{"type":"object","properties":{"query":{"type":"string"},"case_sensitive":{"type":"boolean"}},"required":["query"],"additionalProperties":False}}},
    {"type":"function","function":{"name":"workspace_read_lines","description":"Büyük UTF-8 kod/metin dosyasının belirli satırlarını oku. start_line 1 ile başlar; en çok 200 satır. PDF/Office için workspace_read kullan.","parameters":{"type":"object","properties":{"path":{"type":"string"},"start_line":{"type":"integer","minimum":1},"count":{"type":"integer","minimum":1,"maximum":200}},"required":["path","start_line"],"additionalProperties":False}}},
    {"type":"function","function":{"name":"workspace_write","description":"Proje içinde UTF-8 metin dosyası oluştur, sonuna ekle veya değiştir. Var olan dosyayı replace ile değiştirmeden önce workspace_read ile oku ve dönen sha256 değerini expected_sha256 olarak kullan. create var olan dosyayı değiştirmez.","parameters":{"type":"object","properties":{"path":{"type":"string"},"content":{"type":"string"},"mode":{"type":"string","enum":["create","replace","append"]},"expected_sha256":{"type":"string"}},"required":["path","content","mode"],"additionalProperties":False}}},
    {"type":"function","function":{"name":"workspace_edit","description":"Projedeki metin dosyasında tek bir eşleşen bölümü değiştir. Önce dosyayı oku. old_text birden fazla eşleşirse işlem uygulanmaz.","parameters":{"type":"object","properties":{"path":{"type":"string"},"old_text":{"type":"string"},"new_text":{"type":"string"}},"required":["path","old_text","new_text"],"additionalProperties":False}}},
    {"type":"function","function":{"name":"workspace_mkdir","description":"Proje içinde klasör oluştur.","parameters":{"type":"object","properties":{"path":{"type":"string"}},"required":["path"],"additionalProperties":False}}},
]


def write_text(path, content, create=False):
    encoded=content.encode('utf-8')
    if len(encoded)>150_000:raise ValueError('Dosya metni 150 KB sınırını aşıyor')
    path.parent.mkdir(parents=True,exist_ok=True)
    if create:
        with path.open('xb') as out:out.write(encoded)
    else:
        descriptor,raw=tempfile.mkstemp(prefix='.'+path.name+'.',dir=path.parent)
        temp=Path(raw)
        try:
            with os.fdopen(descriptor,'wb') as out:out.write(encoded)
            if path.exists():temp.chmod(path.stat().st_mode & 0o777)
            temp.replace(path)
        finally:temp.unlink(missing_ok=True)
    return json.dumps({'path':path.name,'bytes':len(encoded),'sha256':hashlib.sha256(encoded).hexdigest()},ensure_ascii=False)


def list_files(root, limit=400):
    paths = []
    def walk(directory):
        for path in sorted(directory.iterdir()):
            if len(paths) >= limit:
                return
            if path.name.startswith(".") or path.name in {"models", "runtime", "node_modules", "__pycache__", "vendor", "build", "dist"} or path.is_symlink():
                continue
            if path.is_dir():
                walk(path)
            elif path.is_file():
                paths.append(str(path.relative_to(root)))
    root = Path(root).resolve()
    walk(root)
    return paths


def call_workspace(root, name, args):
    if not root:
        raise ValueError("Çalışma klasörü seçilmedi")
    if name == "workspace_list":
        return json.dumps(list_files(Path(root)), ensure_ascii=False)
    if name == 'workspace_search':
        query = args.get('query', '')
        if not isinstance(query, str) or not 1 <= len(query) <= 300:
            raise ValueError('Arama 1–300 karakter olmalı.')
        sensitive = bool(args.get('case_sensitive', False))
        needle = query if sensitive else query.casefold()
        found, scanned = [], 0
        for relative in list_files(Path(root), limit=1200):
            path = resolve_file(root, relative)
            if path.stat().st_size > 2_000_000:
                continue
            data = path.read_bytes()
            if b'\0' in data:
                continue
            try:
                lines = data.decode('utf-8-sig').splitlines()
            except UnicodeError:
                continue
            scanned += 1
            for number, line in enumerate(lines, 1):
                if needle in (line if sensitive else line.casefold()):
                    found.append({'path': relative, 'line': number, 'text': line[:300]})
                    if len(found) >= 30:
                        return json.dumps({'matches':found,'scanned_files':scanned,'limited':True},ensure_ascii=False)
        return json.dumps({'matches':found,'scanned_files':scanned,'limited':False},ensure_ascii=False)
    if name == 'workspace_read_lines':
        path = resolve_file(root, args['path'])
        if path.stat().st_size > 2_000_000:
            raise ValueError('Satırla inceleme sınırı 2 MB.')
        start, count = args.get('start_line', 1), args.get('count', 100)
        if type(start) is not int or start < 1 or type(count) is not int or not 1 <= count <= 200:
            raise ValueError('Başlangıç pozitif, satır sayısı 1–200 arasında olmalı.')
        data = path.read_bytes()
        if b'\0' in data:
            raise ValueError('Satırla inceleme UTF-8 metin dosyaları içindir.')
        lines = data.decode('utf-8-sig').splitlines()
        section = '\n'.join(f'{i+1}: {line}' for i,line in enumerate(lines[start-1:start-1+count],start-1))
        return json.dumps({'path':args['path'],'sha256':hashlib.sha256(data).hexdigest(),'start_line':start,'total_lines':len(lines),'content':section[:12000],'limited':len(section)>12000},ensure_ascii=False)
    if name == "workspace_read":
        path = resolve_file(root, args["path"])
        if path.suffix.casefold() in {'.pdf','.docx','.xlsx','.pptx'}:
            from .attachments import extract_document
            content = extract_document(path, limit=12000)
            return json.dumps({'path':args['path'],'content':content,'document':True,'note':'Çıkarılmış belge metni; sayfa görünümü ve gömülü görseller incelenmedi.'},ensure_ascii=False)
        if path.stat().st_size > 150_000:
            raise ValueError("Dosya çok büyük (metin sınırı 150 KB)")
        data=path.read_bytes()
        return json.dumps({'path':args['path'],'sha256':hashlib.sha256(data).hexdigest(),'content':data.decode('utf-8')},ensure_ascii=False)
    if name=='workspace_mkdir':
        path=resolve_file(root,args['path']);path.mkdir(parents=True,exist_ok=True)
        return json.dumps({'created':args['path']},ensure_ascii=False)
    if name=='workspace_write':
        path=resolve_file(root,args['path']);mode=args['mode']
        if mode not in {'create','replace','append'}:raise ValueError('Geçersiz yazma modu')
        content=args['content']
        if not isinstance(content,str):raise ValueError('İçerik metin olmalı')
        if mode!='create' and path.exists():
            if path.stat().st_size>150_000:raise ValueError('Dosya çok büyük')
            original=path.read_bytes()
            if mode=='replace' and args.get('expected_sha256')!=hashlib.sha256(original).hexdigest():
                raise ValueError('Dosyayı önce oku; değişmiş olabilir. Güncel sha256 gerekli.')
            if mode=='append':content=original.decode('utf-8')+content
        return write_text(path,content,create=mode=='create')
    if name=='workspace_edit':
        path=resolve_file(root,args['path'])
        if path.stat().st_size>150_000:raise ValueError('Dosya çok büyük')
        content=path.read_text(encoding='utf-8');old=args['old_text']
        if not old or content.count(old)!=1:raise ValueError('Değiştirilecek metin tam bir kez eşleşmeli; dosyayı tekrar oku')
        return write_text(path,content.replace(old,args['new_text'],1))
    raise ValueError("Bilinmeyen çalışma klasörü aracı")
