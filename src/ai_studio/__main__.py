from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from . import __version__
from .brand import APP_ID, APP_NAME


def main():
    parser = argparse.ArgumentParser(description=f"{APP_NAME} — private native desktop")
    parser.add_argument("--version", action="version", version=f"{APP_NAME} {__version__}")
    parser.add_argument("--screenshot", type=Path, help="Render the native window offscreen and exit")
    parser.add_argument("--page", type=int, default=0, help="Page index for screenshot (0–8)")
    parser.add_argument("--install-desktop", action="store_true", help="Register the Linux application launcher and exit")
    args = parser.parse_args()
    if args.install_desktop:
        if not sys.platform.startswith('linux') or not getattr(sys, 'frozen', False):
            parser.error('--install-desktop requires the packaged Linux application')
        from .desktop import install_launcher
        print(install_launcher())
        return 0
    if args.screenshot:
        os.environ["QT_QPA_PLATFORM"] = "offscreen"
    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QApplication
    from PySide6.QtGui import QPalette, QColor, QFont, QFontDatabase, QIcon
    from .ui.window import Window
    app = QApplication([APP_NAME] if sys.platform.startswith('linux') else sys.argv[:1])
    app.setStyle("Fusion")
    bundled_font = Path(__file__).parent / 'ui/assets/NotoSans-Regular.ttf'
    if bundled_font.is_file():
        QFontDatabase.addApplicationFont(str(bundled_font))
    app.setFont(QFont("Noto Sans" if sys.platform == 'win32' else "Adwaita Sans", 10))
    palette = QPalette()
    for role, color in [(QPalette.ColorRole.Window, "#1b1d23"), (QPalette.ColorRole.Base, "#1c1f26"),
                        (QPalette.ColorRole.AlternateBase, "#242832"), (QPalette.ColorRole.WindowText, "#ececf1"),
                        (QPalette.ColorRole.Text, "#ececf1"), (QPalette.ColorRole.Button, "#2c3039"),
                        (QPalette.ColorRole.ButtonText, "#ececf1"), (QPalette.ColorRole.Highlight, "#5b4d72"),
                        (QPalette.ColorRole.HighlightedText, "#f5efff"), (QPalette.ColorRole.PlaceholderText, "#a0a7ba"),
                        (QPalette.ColorRole.Link, "#c9bcec")]:
        palette.setColor(role, QColor(color))
    app.setPalette(palette)
    app.setApplicationName(APP_NAME)
    app.setApplicationDisplayName(APP_NAME)
    app.setApplicationVersion(__version__)
    app.setOrganizationName(APP_NAME + " Local")
    if sys.platform.startswith('linux'):
        from .desktop import ICON_PATH
        app.setDesktopFileName(APP_ID)
        app.setWindowIcon(QIcon(str(ICON_PATH)))
    from .local_logging import install_exception_hook
    install_exception_hook()
    window = Window()
    if sys.platform.startswith('linux') and getattr(sys, 'frozen', False) and not args.screenshot:
        from .desktop import install_launcher
        from .local_logging import failure
        try:
            install_launcher()
        except (OSError, ValueError) as exc:
            failure('Linux desktop integration', exc)
    window.show()
    if args.screenshot:
        window.navigate(max(0, min(8, args.page)))
        window.timer.stop()
        def capture():
            args.screenshot.parent.mkdir(parents=True, exist_ok=True)
            target = window.preferences if args.page >= 2 else window
            target.grab().save(str(args.screenshot))
            window.preferences.close()
            window.close()
        QTimer.singleShot(600, capture)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
