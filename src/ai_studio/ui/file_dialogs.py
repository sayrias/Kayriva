"""Consistent Qt file picker, avoiding broken desktop-portal folder listings."""
from pathlib import Path
from ..i18n import tr
from PySide6.QtCore import QDir, QUrl, Qt
from PySide6.QtWidgets import QFileDialog as NativeFileDialog, QLineEdit, QAbstractItemView


class QFileDialog(NativeFileDialog):
    @staticmethod
    def _choose(parent, caption, directory, filters, mode):
        dialog = NativeFileDialog(parent, caption)
        # Set before changing file modes: never delegate to the desktop portal.
        dialog.setOption(NativeFileDialog.Option.DontUseNativeDialog, True)
        dialog.setFileMode(mode)
        dialog.setAcceptMode(NativeFileDialog.AcceptMode.AcceptOpen)
        dialog.setViewMode(NativeFileDialog.ViewMode.Detail)
        for role, title in [(NativeFileDialog.DialogLabel.LookIn,tr('Konum')),
                            (NativeFileDialog.DialogLabel.FileName,tr('Klasör') if mode==NativeFileDialog.FileMode.Directory else tr('Dosya adı')),
                            (NativeFileDialog.DialogLabel.FileType,tr('Dosya türü')),
                            (NativeFileDialog.DialogLabel.Accept,tr('Seç')),
                            (NativeFileDialog.DialogLabel.Reject,tr('Vazgeç'))]:
            dialog.setLabelText(role,title)
        dialog.setFilter(QDir.Filter.AllDirs | QDir.Filter.Files | QDir.Filter.NoDotAndDotDot)
        if mode == NativeFileDialog.FileMode.Directory:
            dialog.setOption(NativeFileDialog.Option.ShowDirsOnly, True)
        initial = Path(directory).expanduser() if directory else Path.home()
        while not initial.is_dir() and initial != initial.parent:
            initial = initial.parent
        dialog.setDirectory(str(initial))
        dialog.setSidebarUrls([QUrl.fromLocalFile(str(path)) for path in dict.fromkeys([Path.home(),Path.home()/'Masaüstü',Path.home()/'Desktop',Path.home()/'Downloads',initial]) if path.is_dir()])
        if filters:
            dialog.setNameFilter(filters)
        # The location is already shown above. Filename starts genuinely blank.
        filename = dialog.findChild(QLineEdit, 'fileNameEdit')
        if filename:
            filename.clear()
        for view in dialog.findChildren(QAbstractItemView):
            view.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        sidebar=dialog.findChild(QAbstractItemView,'sidebar')
        if sidebar:
            sidebar.setMinimumWidth(160)
            sidebar.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        dialog.resize(860, 560)
        if dialog.exec() != NativeFileDialog.DialogCode.Accepted:
            return [], ''
        return dialog.selectedFiles(), dialog.selectedNameFilter()

    @staticmethod
    def getExistingDirectory(parent=None, caption='', directory='', options=None):
        files, _ = QFileDialog._choose(parent, caption, directory, '', NativeFileDialog.FileMode.Directory)
        return files[0] if files else ''

    @staticmethod
    def getOpenFileName(parent=None, caption='', directory='', filter='', **kwargs):
        files, selected = QFileDialog._choose(parent, caption, directory, filter, NativeFileDialog.FileMode.ExistingFile)
        return (files[0] if files else '', selected)

    @staticmethod
    def getOpenFileNames(parent=None, caption='', directory='', filter='', **kwargs):
        return QFileDialog._choose(parent, caption, directory, filter, NativeFileDialog.FileMode.ExistingFiles)
