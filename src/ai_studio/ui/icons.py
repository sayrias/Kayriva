"""Application-owned SVG line icons. No network fonts or emoji assets."""
from functools import lru_cache
from PySide6.QtCore import QByteArray, QSize, Qt
from PySide6.QtGui import QIcon, QPixmap, QPainter
from PySide6.QtSvg import QSvgRenderer

PATHS = {
    "chat": '<path d="M5 4h14a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H9l-6 4V6a2 2 0 0 1 2-2Z"/>',
    "search": '<circle cx="10" cy="10" r="7"/><path d="m15 15 6 6"/>',
    "pin": '<path d="m9 3 8 0-2 6 4 4H5l4-4ZM12 13v8"/>',
    "book": '<path d="M4 4h6l2 2 2-2h6v16h-6l-2 2-2-2H4ZM12 6v16"/>',
    "kayriva": '<path d="M4 19V9l8-6 8 6v10M8 17V11l4-3 4 3v6M4 19l8-6 8 6M12 13v8"/>',
    "check": '<path d="m5 12 4 4L19 6"/>',
    "clock": '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
    "download": '<path d="M12 3v12m-5-5 5 5 5-5M4 17v4h16v-4"/>',
    "text-select": '<path d="M4 4h16M12 4v16M8 20h8M4 10v6M20 10v6"/>',
    "info": '<circle cx="12" cy="12" r="9"/><path d="M12 11v6M12 7h.01"/>',
    "chart": '<path d="M4 3v17h17M8 16v-5m5 5V6m5 10V9"/>',
    "plan": '<path d="M9 5h12M9 12h12M9 19h12M3 5h1M3 12h1M3 19h1"/>',
    "thinking": '<path d="M9 18h6M9 21h6M8 15c-6-5-2-13 4-13s10 8 4 13l-1 3H9Z"/>',
    "shield": '<path d="m12 3 8 3v6c0 5-8 9-8 9s-8-4-8-9V6Z M8 12l3 3 5-6"/>',
    "hand": '<path d="M8 13V6a2 2 0 0 1 4 0v7-8a2 2 0 0 1 4 0v8-5a2 2 0 0 1 4 0v7c0 4-3 6-7 6H9c-2 0-4-3-6-7a2 2 0 0 1 3-2l2 2"/>',
    "save": '<path d="M4 3h13l3 3v15H4Z M8 3v6h8V3M8 21v-8h8v8"/>',
    "refresh": '<path d="M20 8a9 9 0 0 0-16 0M4 8V3m0 5h5M4 16a9 9 0 0 0 16 0m0 0v5m0-5h-5"/>',

    "play": '<path d="m8 4 12 8-12 8Z"/>',
    "edit": '<path d="m14 4 6 6M4 20l5-1L21 7l-4-4L5 15Z"/>',
    "plus": '<path d="M12 5v14M5 12h14"/>',
    "send": '<path d="M12 19V5M5 12l7-7 7 7"/>',
    "settings": '<path d="m9 3-.6 2.2-1.7 1-2.2-.6-2 3.5 1.6 1.6v2L2.5 14l2 3.5 2.2-.6 1.7 1L9 20h4l.6-2.1 1.7-1 2.2.6 2-3.5-1.6-1.3v-2l1.6-1.6-2-3.5-2.2.6-1.7-1L13 3Z"/><circle cx="11" cy="11.5" r="3"/>',
    "folder": '<path d="M3 7V5h6l2 2h10v12H3Z"/><path d="M3 10h18"/>',
    "code": '<path d="m8 7-5 5 5 5m8-10 5 5-5 5m-3-13-2 20"/>',
    "globe": '<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3c5 5 5 13 0 18-5-5-5-13 0-18Z"/>',
    "models": '<path d="m12 3 9 5-9 5-9-5Z M3 12l9 5 9-5M3 16l9 5 9-5"/>',
    "tools": '<path d="m14 6 4-4a6 6 0 0 0-7 8L3 18a2 2 0 0 0 3 3l8-8a6 6 0 0 0 8-7l-4 4Z"/>',
    "file": '<path d="M5 3h9l5 5v13H5Z M14 3v6h5 M8 13h8M8 17h5"/>',
    "copy": '<rect x="8" y="8" width="12" height="13" rx="2"/><path d="M15 8V3H3v13h5"/>',
    "chevron-down": '<path d="m6 9 6 6 6-6"/>',
    "chevron-right": '<path d="m9 6 6 6-6 6"/>',
    "back": '<path d="m10 5-7 7 7 7M3 12h18"/>',
    "close": '<path d="m6 6 12 12M6 18 18 6"/>',
    "more": '<circle cx="4" cy="12" r="1"/><circle cx="12" cy="12" r="1"/><circle cx="20" cy="12" r="1"/>',
    "spark": '<path d="m12 2 3 7 7 3-7 3-3 7-3-7-7-3Z"/>',
    "team": '<path d="M4 8h16m-4-4 4 4-4 4M20 16H4m4-4-4 4 4 4"/>',
    "stop": '<rect x="5" y="5" width="14" height="14" rx="3"/>',
    "trash": '<path d="M3 6h18M9 6V3h6v3M5 6l1 15h12l1-15M10 10v7m4-7v7"/>',
}

@lru_cache(maxsize=128)
def icon(name, color="#c4b6ee"):
    svg = f'<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">{PATHS.get(name, PATHS["spark"])}</svg>'
    renderer = QSvgRenderer(QByteArray(svg.encode()))
    pixmap = QPixmap(64, 64)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.end()
    return QIcon(pixmap)
