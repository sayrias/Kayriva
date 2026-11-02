"""Conservative local memory estimates and configurable model usage budgets.

This checks a budget before model loading, not a hard OS allocation cap. Engine
fitting refines GPU placement when available; other processes can race this check.
"""
from __future__ import annotations
from dataclasses import dataclass
import math
import re
from pathlib import Path
from ..hardware import model_limits, detect
from ..resources import snapshot
from ..memory_units import memory_text

GIB=1024**3


def effective_cache(settings):
    cache = settings.kv_cache
    return 'q8_0' if getattr(settings, 'memory_profile', 'balanced') == 'low_memory' and cache == 'f16' else cache


def context_limit(settings, model):
    if settings.context > 0:
        return settings.context
    maximum=model_limits(model).get('context')
    if not maximum:
        raise ValueError('Sınırsız bağlam için modelin bağlam sınırı okunamadı. Sayısal bir bağlam seç.')
    return maximum


def allocation_context(settings, model, messages=None, tools=None):
    """Grow the unlimited context per request instead of reserving the full model maximum.

    UTF-8 bytes conservatively bound text tokens. Extra room covers chat template
    markers and a reply. Explicit numeric contexts remain fixed.
    """
    maximum = context_limit(settings, model)
    if settings.context > 0:
        return maximum
    import json
    from ..attachments import prompt_size
    prompt = prompt_size(messages or [])
    prompt += len(json.dumps(tools or [], ensure_ascii=False).encode('utf-8'))
    prompt += 256 * (len(messages or []) + len(tools or []) + 1)
    low_memory = getattr(settings, 'memory_profile', 'balanced') == 'low_memory'
    reply = settings.max_tokens if settings.max_tokens > 0 else (1024 if low_memory else 2048)
    required = prompt + reply
    if prompt >= maximum:
        raise ValueError('Sohbet modelin bağlam sınırını aşıyor. Yeni bir sohbet başlat veya ekleri azalt.')
    # Base64 is transport, not text tokens. Images require a separate encoder budget.
    capacity = min(2048 if low_memory else 4096, maximum)
    while capacity < required and capacity < maximum:
        capacity = min(capacity * 2, maximum)
    return capacity


def weights_gb(model):
    model=Path(model)
    if model.is_file():
        split = re.fullmatch(r'(.+)-(\d{5})-of-(\d{5})\.gguf', model.name, re.I)
        if split:
            total = int(split[3])
            if not 1 <= total <= 256:
                raise ValueError('GGUF parça sayısı geçersiz.')
            parts = [model.with_name(f'{split[1]}-{n:05}-of-{total:05}{model.suffix}') for n in range(1, total + 1)]
            if any(not part.is_file() for part in parts):
                raise ValueError('Modelin GGUF parçaları eksik. Bütün parçaları aynı klasöre ekle.')
            return sum(part.stat().st_size for part in parts) / GIB
        return model.stat().st_size/GIB
    files=list(model.glob('*.safetensors')) or list(model.glob('pytorch_model*.bin'))
    return sum(p.stat().st_size for p in files)/GIB


@dataclass(frozen=True)
class MemoryPlan:
    layers: int
    ram: float
    vram: float
    ram_budget: float
    vram_budget: float
    context: int
    gpu_available: bool
    vram_margin: float = 0.0


def memory_budgets(settings, counters):
    """Manual values cap model use; Auto leaves space for other applications.

    Neither mode reserves memory in advance. The current free memory is always
    an upper bound, including for manually chosen budgets.
    """
    ram_total = max(0, counters.get('ram_total', detect().ram_gb))
    gpu_total = max(0, counters.get('vram_total', settings.hardware_vram_gb))
    ram_free = max(0, min(ram_total, ram_total - counters.get('ram_used', 0)))
    gpu_free = max(0, min(gpu_total, gpu_total - counters.get('vram_used', 0)))
    budgets = []
    for requested, free, total, margin in [
        (settings.ram_budget_gb, ram_free, ram_total, 2.),
        (settings.vram_budget_gb, gpu_free, gpu_total, 1.),
    ]:
        if not math.isfinite(requested) or requested < 0:
            raise ValueError('Bellek üst sınırı geçersiz. Otomatik veya pozitif bir GB miktarı seç.')
        budgets.append(min(requested, free) if requested > 0 else max(0, free - min(margin, total / 4)))
    return budgets[0], budgets[1], gpu_free - budgets[1]


def plan_memory(settings, model, counters=None, gpu_available=True, strict=True, context=None):
    limits=model_limits(model); context=context_limit(settings,model) if context is None else context
    if not 0 < context <= context_limit(settings,model):
        raise ValueError('Geçersiz çalışma bağlamı')
    weights=weights_gb(model)
    layers=limits.get('layers',0)
    interval=limits.get('attention_interval',1)
    kv_layers=math.ceil(layers/interval) if layers else 32
    heads=limits.get('kv_heads', limits.get('heads',8))
    dimension=limits.get('key_length',limits.get('embedding',4096)//limits.get('heads',32))
    value_dim=limits.get('value_length',dimension)
    element={'f16':2.,'q8_0':1.0625,'q4_0':.5625}.get(effective_cache(settings),2.)
    cache=context*kv_layers*heads*(dimension+value_dim)*element/GIB
    # Scratch, graph buffers and hybrid recurrent-state allowance.
    projector = getattr(settings, 'mmproj_path', '')
    projector_path = Path(projector).expanduser() if projector else None
    projector_size = projector_path.stat().st_size / GIB if projector_path and projector_path.is_file() else 0
    # Projectors run on CPU to leave the selected VRAM budget for the text model.
    fixed=1.0 + (.25 if interval>1 else 0) + (projector_size + .5 if projector_size else 0)
    counters=snapshot() if counters is None else counters
    ram_budget, gpu_budget, gpu_margin = memory_budgets(settings, counters)
    gpu_total=counters.get('vram_total',settings.hardware_vram_gb)
    gpu=gpu_available and settings.acceleration!='cpu' and gpu_total>0
    if not gpu:
        gpu_budget = 0
    # Reserve graph room in VRAM; layer weights/cache are an estimate.
    gpu_overhead=.5 if gpu else 0
    per_layer=(weights+cache)/max(1,layers)
    fits=max(0,min(layers,int(max(0,gpu_budget-gpu_overhead)/max(.000001,per_layer))))
    if settings.acceleration=='gpu' and not gpu:
        raise ValueError('GPU kullanılamıyor. Çalışan GPU sürücüsü ve Vulkan/CUDA motoru seç veya GPU + RAM / CPU modunu kullan.')
    if settings.acceleration=='gpu':
        offload=layers
    elif gpu:
        offload=fits if settings.gpu_layers<0 else min(settings.gpu_layers,fits)
    else:offload=0
    fraction=offload/max(1,layers)
    vram=(weights+cache)*fraction + (gpu_overhead if offload else 0)
    ram=(weights+cache)*(1-fraction)+fixed
    if strict and (ram>ram_budget or vram>gpu_budget):
        message=f'Model bu bellek bütçesine sığmıyor. Tahmini RAM: {memory_text(ram*GIB)} / kullanılabilir {memory_text(ram_budget*GIB)}'
        if gpu:message+=f'; VRAM: {memory_text(vram*GIB)} / bütçe {memory_text(gpu_budget*GIB)}'
        message+='. Düşük bellek profilini, daha kısa bağlamı veya daha küçük GGUF kuantizasyonunu dene. Ayarlar → Genel bölümünde RAM/VRAM üst sınırını yalnızca sistemde boş yer varsa artır. Disk/swap daha fazla fiziksel bellek veya GPU hızı sağlamaz. Bu bir tahmindir.'
        raise ValueError(message)
    return MemoryPlan(offload,ram,vram,ram_budget,gpu_budget,context,gpu,gpu_margin if gpu else 0)
