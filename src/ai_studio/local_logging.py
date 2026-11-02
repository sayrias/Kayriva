"""Rotating local diagnostics. Never log prompts, tool arguments or credentials."""
import logging
import sys
import traceback
from logging.handlers import RotatingFileHandler


def configure(runtime):
    folder = runtime / 'logs'
    folder.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger('ai_studio')
    logger.setLevel(logging.INFO)
    logger.propagate = False
    for handler in logger.handlers[:]:
        handler.close()
        logger.removeHandler(handler)
    handler = RotatingFileHandler(folder / 'app.log', maxBytes=2_000_000, backupCount=3, encoding='utf-8')
    handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
    logger.addHandler(handler)
    (folder / 'app.log').chmod(0o600)
    logger.info('Application started')
    return folder


def failure(context, exc):
    # Frame locations are useful for debugging; exception values can contain user data.
    logger = logging.getLogger('ai_studio')
    seen = set()
    while exc is not None and id(exc) not in seen and len(seen) < 8:
        seen.add(id(exc))
        logger.error('%s: %s\n%s', context, type(exc).__name__, '\n'.join(f'{frame.filename}:{frame.lineno} in {frame.name}' for frame in traceback.extract_tb(exc.__traceback__)))
        exc = exc.__cause__ or exc.__context__


def install_exception_hook():
    original = sys.excepthook
    def hook(kind, value, tb):
        failure('Unhandled exception', value)
        original(kind, value, tb)
    sys.excepthook = hook
