"""Local hardware limits and bounded GGUF metadata inspection."""
import math
import json
import os
import struct
import subprocess
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path


def cpu_limit():
    count = os.cpu_count() or 1
    try:
        count = min(count, len(os.sched_getaffinity(0)))
    except (AttributeError, OSError):
        pass
    return max(1, count)


@dataclass(frozen=True)
class Hardware:
    threads: int
    ram_gb: int
    vram_gb: int = 0
    gpu_name: str = ''
    ram_bytes: int = 0
    vram_bytes: int = 0


@lru_cache(maxsize=1)
def detect():
    ram_bytes = vram_bytes = 0
    try:
        ram_bytes = os.sysconf('SC_PAGE_SIZE') * os.sysconf('SC_PHYS_PAGES')
        ram = math.ceil(ram_bytes / 1024**3)
    except (ValueError, OSError, AttributeError):
        # Windows: no third-party package or network access needed.
        ram = 0
        if os.name == 'nt':
            import ctypes
            class Memory(ctypes.Structure):
                _fields_ = [('length', ctypes.c_ulong), ('load', ctypes.c_ulong)] + [(k, ctypes.c_ulonglong) for k in ['total','available','page','free_page','virtual','free_virtual','extended']]
            memory = Memory(); memory.length = ctypes.sizeof(memory)
            if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(memory)):
                ram_bytes = memory.total
                ram = math.ceil(memory.total / 1024**3)
    gpu, vram = '', 0
    try:
        result = subprocess.run(['nvidia-smi','--query-gpu=name,memory.total','--format=csv,noheader,nounits'], capture_output=True,text=True,timeout=2)
        if result.returncode == 0:
            name, size = result.stdout.strip().splitlines()[0].rsplit(',',1)
            gpu, vram = name.strip(), int(round(float(size)/1024))
            vram_bytes = int(float(size) * 1024**2)
    except (OSError, ValueError, IndexError, subprocess.TimeoutExpired):
        pass
    return Hardware(cpu_limit(), max(1, ram), vram, gpu, ram_bytes, vram_bytes)


def model_limits(path):
    if not path:
        return {}
    path=Path(path).resolve()
    try:
        source=path/'config.json' if path.is_dir() else path
        info=source.stat()
        return dict(_cached_model_limits(str(path),info.st_mtime_ns,info.st_size))
    except OSError:
        return {}


@lru_cache(maxsize=64)
def _cached_model_limits(path, modified, size):
    return _read_model_limits(path)


def _read_model_limits(path):
    """Read local GGUF/Transformers metadata; never load weights or model code."""
    if not path:
        return {}
    path = Path(path)
    if path.is_dir():
        try:
            config = path / 'config.json'
            if config.stat().st_size > 1_048_576:
                return {}
            data = json.loads(config.read_text())
            data = data.get('text_config', data)
            result = {}
            for source, key, lower, upper in [('num_hidden_layers', 'layers', 1, 1024), ('max_position_embeddings', 'context', 512, 10_000_000)]:
                value = data.get(source)
                if isinstance(value, int) and lower <= value <= upper:
                    result[key] = value
            for source, key in [('hidden_size','embedding'),('num_attention_heads','heads'),('num_key_value_heads','kv_heads'),('head_dim','key_length')]:
                value = data.get(source)
                if isinstance(value,int) and 0 < value <= 1_000_000:
                    result[key] = value
            return result
        except (OSError, ValueError, AttributeError):
            return {}
    if not path.is_file():
        return {}
    limits = {}
    try:
        with Path(path).open('rb') as f:
            def read(n):
                data = f.read(n)
                if len(data) != n:
                    raise ValueError('truncated metadata')
                return data
            def u32(): return struct.unpack('<I',read(4))[0]
            def u64(): return struct.unpack('<Q',read(8))[0]
            def string():
                size = u64()
                if size > 1_048_576: raise ValueError('oversize metadata')
                return read(size).decode('utf-8')
            formats = {0:'B',1:'b',2:'H',3:'h',4:'I',5:'i',6:'f',7:'?',10:'Q',11:'q',12:'d'}
            def value(kind, depth=0):
                if depth > 2: raise ValueError('nested metadata')
                if kind in formats:
                    fmt='<'+formats[kind]
                    return struct.unpack(fmt,read(struct.calcsize(fmt)))[0]
                if kind == 8: return string()
                if kind == 9:
                    subtype, count = u32(), u64()
                    if count > 2_000_000: raise ValueError('oversize metadata')
                    if subtype in formats:
                        end = f.tell() + count*struct.calcsize('<'+formats[subtype])
                        if end > path.stat().st_size:
                            raise ValueError('truncated metadata')
                        f.seek(end)
                    else:
                        for _ in range(count): value(subtype,depth+1)
                    return None
                raise ValueError('unknown metadata type')
            if read(4) != b'GGUF' or u32() not in {2,3}: return {}
            u64(); count=u64()
            if count > 100_000: return {}
            for _ in range(count):
                key, kind = string(), u32()
                result = value(kind)
                if key.count('.') == 1 and key.endswith('.block_count') and isinstance(result,int) and 0 < result <= 1024:
                    limits['layers'] = result
                elif key.count('.') == 1 and key.endswith('.context_length') and isinstance(result,int) and 512 <= result <= 10_000_000:
                    limits['context'] = result
                elif '.vision.' not in key and isinstance(result,int) and 0 < result <= 1_000_000:
                    fields = {'.embedding_length':'embedding', '.attention.head_count':'heads', '.attention.head_count_kv':'kv_heads', '.attention.key_length':'key_length', '.attention.value_length':'value_length', '.full_attention_interval':'attention_interval'}
                    for suffix, name in fields.items():
                        if key.endswith(suffix):
                            limits[name] = result
    except (OSError, ValueError, struct.error, UnicodeError):
        return {}
    return limits
