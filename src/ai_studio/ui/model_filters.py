"""Library filters describe model metadata, never benchmark scores."""
from __future__ import annotations
from ..i18n import tr

TIERS = ('low', 'medium', 'high', 'very_high', 'ultra')
TIER_NAMES = ('Düşük', 'Orta', 'Yüksek', 'Çok yüksek', 'Ultra')
CAPABILITY_NAMES = {
    'chat': 'Sohbet', 'code': 'Kod', 'reasoning': 'Akıl yürütme',
    'vision': 'Görsel mimari', 'tools': 'Araç kullanımı',
}


def brand(model):
    if model.get('brand'):
        return str(model['brand'])
    name = model.get('name', '').casefold()
    for prefix, title in [('qwen', 'Qwen'), ('deepseek', 'DeepSeek'), ('gemma', 'Google'),
                          ('llama', 'Meta'), ('phi', 'Microsoft'), ('mistral', 'Mistral'),
                          ('ministral', 'Mistral'), ('smollm', 'Hugging Face')]:
        if name.startswith(prefix):
            return title
    return model.get('repo', '').split('/')[0] or 'Diğer'


def capabilities(model):
    values = model.get('capabilities')
    if isinstance(values, list):
        return set(values)
    # Older catalogs contain no feature assertions. Only the stated purpose
    # gives a safe coding/reasoning hint; do not infer vision or tool support.
    purpose = model.get('purpose', '').casefold()
    result = {'chat'}
    if 'kod' in purpose:
        result.add('code')
    if 'düşün' in purpose or 'reason' in purpose:
        result.add('reasoning')
    return result


def capacity_tier(model):
    if model.get('tier') in TIERS:
        return TIERS.index(model['tier'])
    size = float(model.get('approx_gb') or 0)
    return 0 if size <= 2 else 1 if size <= 5 else 2 if size <= 10 else 3 if size <= 20 else 4


def accepts(model, *, maker='', capability='', tier=4, maximum_gb=0):
    if maker and brand(model) != maker:
        return False
    if capability and capability not in capabilities(model):
        return False
    if capacity_tier(model) > tier:
        return False
    return not maximum_gb or float(model.get('approx_gb') or 0) <= maximum_gb


def capability_text(model):
    values = capabilities(model)
    # Web and document work are application workflows; the library must not
    # disguise them as independently measured model skills.
    return ' · '.join(tr(CAPABILITY_NAMES[key]) for key in CAPABILITY_NAMES if key in values)
