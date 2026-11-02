"""Conservative, explainable candidates, never measured hardware compatibility."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Recommendation:
    label: str
    reason: str
    score: int
    recommended: bool


def assess(model, ram_gb, vram_gb):
    # Catalog files are decimal GB; hardware controls use the customary GiB budget.
    weights = float(model['approx_gb']) * 1_000_000_000 / (1024 ** 3)
    ram_budget = max(0.0, float(ram_gb) - 4.0)
    gpu_budget = max(0.0, float(vram_gb) - 1.0)
    # An allowance for buffers/cache is a heuristic, not a parsed GGUF memory plan.
    needed = weights + 1.25
    total = ram_budget + gpu_budget
    quality = model.get('quality', 'balanced')
    if needed > total * .9:
        return Recommendation('Bellek sınırında', 'Kısa bağlam veya daha küçük kuantizasyon gerekebilir.', 10, False)
    if needed <= gpu_budget:
        label, reason = 'GPU adayı', 'Kısa bağlamla GPU’da denenebilir.'
    elif gpu_budget:
        label, reason = 'RAM + GPU', 'Ağırlıkların bir kısmı sistem RAM’inde kalır.'
    else:
        label, reason = 'CPU + RAM', 'GPU olmadan; üretim daha yavaş olabilir.'
    if quality == 'extreme':
        return Recommendation(label, 'Aşırı sıkıştırma; kalite kaybı yüksek olabilir.', 25, False)
    params = model.get('params_b', 0)
    score = 95 if 6 <= params <= 10 and quality == 'balanced' else 88 if params <= 5 else 80
    if quality == 'low':
        score -= 8
        reason += ' Düşük bit, kaliteyi azaltabilir.'
    if model.get('category') == 'uncensored':
        reason += ' Topluluk türevi.'
    return Recommendation(label, reason, score, True)


def matches(model, category, query, root, ram, vram, *, brand='all', capability='all', tier='all', max_gb=None):
    text = ' '.join(str(model.get(k, '')) for k in ['name', 'brand', 'quant', 'repo', 'purpose', 'approx_gb', 'capabilities', 'license']).casefold()
    if query.casefold() not in text:
        return False
    if brand not in {'all', '', None} and model.get('brand') != brand:
        return False
    if capability not in {'all', '', None} and capability not in model.get('capabilities', []):
        return False
    if tier not in {'all', '', None} and model.get('tier') != tier:
        return False
    if max_gb is not None and float(model['approx_gb']) > float(max_gb):
        return False
    if category == 'recommended':
        return model.get('availability') != 'unavailable' and assess(model, ram, vram).recommended
    if category == 'compact27':
        return model.get('params_b') == 27 and model['approx_gb'] <= 9
    if category == 'installed':
        return (root / 'models' / model['filename']).is_file()
    return category == 'all' or model.get('category') == category
