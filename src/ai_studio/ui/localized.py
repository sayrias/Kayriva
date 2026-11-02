"""Explicit native text bindings; plain user strings never become translations.

These are Qt subclasses, scoped to our UI imports. No global Qt monkeypatching,
widget reconstruction or edits to model output and editable user values.
"""
from PySide6 import QtWidgets
from PySide6.QtCore import QObject
from ..i18n import Text


def _remember(obj, key, value):
    if not hasattr(obj, '_translations'):
        obj._translations = {}
    if isinstance(value, Text):
        obj._translations[key] = value
    else:
        obj._translations.pop(key, None)


def _widget(base):
    namespace = {}
    for name in ('setText', 'setPlaceholderText', 'setToolTip', 'setAccessibleName', 'setAccessibleDescription', 'setStatusTip', 'setWindowTitle', 'setTitle', 'setFormat', 'setSpecialValueText'):
        original = getattr(base, name, None)
        if original is None:
            continue
        def setter(self, text, _name=name, _original=original):
            _remember(self, _name, text)
            return _original(self, text)
        namespace[name] = setter
    def init(self, *args, **kwargs):
        base.__init__(self, *args, **kwargs)
        if args and isinstance(args[0], Text) and hasattr(base, 'setText'):
            _remember(self, 'setText', args[0])
    namespace['__init__'] = init
    return type(base.__name__, (base,), namespace)


for _name in ('QWidget', 'QMainWindow', 'QFrame', 'QLabel', 'QPushButton', 'QCheckBox', 'QLineEdit',
              'QPlainTextEdit', 'QTextBrowser', 'QScrollArea', 'QProgressBar', 'QSlider', 'QSpinBox',
              'QListWidget', 'QTreeWidget', 'QTableWidget', 'QSplitter', 'QStackedWidget', 'QTabWidget'):
    globals()[_name] = _widget(getattr(QtWidgets, _name))


class QComboBox(_widget(QtWidgets.QComboBox)):
    # Keep source labels separate from the stable backend item data.
    def addItem(self, *args):
        super().addItem(*args)
        text = args[1] if args and not isinstance(args[0], str) else args[0]
        if isinstance(text, Text):
            # Python objects stored as QVariant may discard str-subclass metadata.
            self._item_sources = getattr(self, '_item_sources', {})
            self._item_sources[self.count()-1] = text

    def setItemText(self, index, text):
        self._item_sources = getattr(self, '_item_sources', {})
        if isinstance(text, Text):
            self._item_sources[index] = text
        else:
            self._item_sources.pop(index, None)
        super().setItemText(index, text)

    def removeItem(self, index):
        self._item_sources = {i if i < index else i-1: source
                              for i, source in getattr(self, '_item_sources', {}).items() if i != index}
        super().removeItem(index)

    def clear(self):
        self._item_sources = {}
        super().clear()


class FilterTabs(_widget(QtWidgets.QTabBar)):
    """Small, fixed set of filter scopes with stable IDs and live labels."""
    def __init__(self):
        super().__init__()
        self.setObjectName('filterTabs')
        self.setExpanding(False)
        self.setDrawBase(False)
        self.setUsesScrollButtons(False)
        self._tab_sources = {}

    def addItem(self, title, value):
        index = self.addTab(title)
        self.setTabData(index, value)
        if isinstance(title, Text):
            self._tab_sources[index] = title

    def currentData(self):
        return self.tabData(self.currentIndex())

    def findData(self, value):
        return next((i for i in range(self.count()) if self.tabData(i) == value), -1)


class QListWidgetItem(QtWidgets.QListWidgetItem):
    def __init__(self, *args):
        super().__init__(*args)
        text = next((arg for arg in args if isinstance(arg, Text)), None)
        if text is not None:
            _remember(self, 'setText', text)

    def setText(self, text):
        _remember(self, 'setText', text)
        super().setText(text)

    def setToolTip(self, text):
        _remember(self, 'setToolTip', text)
        super().setToolTip(text)


class QFormLayout(QtWidgets.QFormLayout):
    def __init__(self, *args):
        super().__init__(*args)
        self.setRowWrapPolicy(QtWidgets.QFormLayout.RowWrapPolicy.WrapLongRows)
        self.setFieldGrowthPolicy(QtWidgets.QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)

    def addRow(self, *args):
        if len(args) == 2 and isinstance(args[0], Text):
            title = QLabel(args[0])
            title.setWordWrap(True)
            args = (title, args[1])
        super().addRow(*args)


def retranslate(root):
    """Update only explicitly bound text, blocking control signals and preserving state."""
    for obj in [root, *root.findChildren(QObject)]:
        blocked = obj.blockSignals(True)
        try:
            for setter, source in list(getattr(obj, '_translations', {}).items()):
                getattr(obj, setter)(source.render())
            if isinstance(obj, QComboBox):
                for index, source in list(getattr(obj, '_item_sources', {}).items()):
                    obj.setItemText(index, source.render())
            if isinstance(obj, FilterTabs):
                for index, source in obj._tab_sources.items():
                    obj.setTabText(index, source.render())
            if isinstance(obj, QtWidgets.QListWidget):
                for row in range(obj.count()):
                    item = obj.item(row)
                    for setter, source in list(getattr(item, '_translations', {}).items()):
                        getattr(item, setter)(source.render())
            obj.update() if isinstance(obj, QtWidgets.QWidget) else None
        finally:
            obj.blockSignals(blocked)
