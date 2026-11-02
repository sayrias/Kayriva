"""Display decimal GB/MB while keeping engine settings compatible with GiB."""
from .i18n import language
GIB = 1024**3
GB = 1000**3
MB = 1000**2


def memory_text(byte_count):
    value = f'{byte_count / GB:.2f}'
    return (value.replace('.', ',') if language() == 'tr' else value) + ' GB'


def memory_detail(byte_count):
    value = f'{byte_count / MB:.0f} MB · {byte_count / 1024**2:.0f} MiB · {byte_count / GIB:.2f} GiB'
    return (value.replace('.', ',') if language() == 'tr' else value) + ' · 1 GB = 1000 MB'
