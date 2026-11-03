"""Open private attachment images in a zoomable, local-only preview."""
from pathlib import Path
import re
import math
from PySide6.QtCore import Qt, QSize, QTimer
from PySide6.QtGui import QImageReader, QPixmap
from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QSizePolicy
from .localized import QLabel, QScrollArea, QPushButton
from .icons import icon
from ..i18n import tr


def attachment_path(runtime, descriptor):
    name = descriptor.get('image_path', '')
    if not isinstance(name, str) or not re.fullmatch(r'[a-f0-9]{64}\.png', name):
        return None
    path = Path(runtime)/'attachments'/name
    return path if path.is_file() and not path.is_symlink() else None


class ImagePreview(QDialog):
    def __init__(self, path, title, parent=None):
        super().__init__(parent)
        self.setObjectName('imagePreview')
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setWindowTitle(title or tr('Görsel önizlemesi'))
        self.resize(900, 650)
        reader = QImageReader(str(path)); reader.setAutoTransform(True)
        size = reader.size()
        self.pixmap = QPixmap() if size.width()*size.height()>50_000_000 else QPixmap.fromImage(reader.read())
        self.scale = 1.0
        self.fitting = True
        box = QVBoxLayout(self); box.setContentsMargins(18,16,18,16); box.setSpacing(12)
        top = QHBoxLayout(); name=QLabel(title or tr('Görsel önizlemesi'));name.setWordWrap(True)
        top.addWidget(name,1)
        for text, glyph, action in [(tr('Sığdır'),'image',self.fit),('1:1','image',self.original),('', 'minus',lambda:self.zoom(.8)),('', 'plus',lambda:self.zoom(1.25))]:
            control=QPushButton(text);control.setIcon(icon(glyph));control.setIconSize(QSize(16,16))
            control.setToolTip(text or (tr('Uzaklaştır') if glyph=='minus' else tr('Yakınlaştır')))
            control.clicked.connect(action);top.addWidget(control)
        box.addLayout(top)
        self.scroll=QScrollArea();self.scroll.setWidgetResizable(False);self.scroll.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image=QLabel();self.image.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.scroll.setWidget(self.image);box.addWidget(self.scroll,1)
        self.info=QLabel(tr('Görsel okunamadı.') if self.pixmap.isNull() else f'{self.pixmap.width()} × {self.pixmap.height()} px')
        box.addWidget(self.info)
        QTimer.singleShot(0,self.fit)

    def show_scaled(self):
        if self.pixmap.isNull():return
        size=self.pixmap.size()*self.scale
        self.image.setPixmap(self.pixmap.scaled(size,Qt.AspectRatioMode.KeepAspectRatio,Qt.TransformationMode.SmoothTransformation))
        self.image.resize(self.image.pixmap().size())

    def fit(self):
        self.fitting=True
        if not self.pixmap.isNull():
            viewport=self.scroll.viewport().size()-QSize(20,20)
            self.scale=min(1, max(.01,min(viewport.width()/self.pixmap.width(),viewport.height()/self.pixmap.height())))
            self.show_scaled()

    def original(self):
        self.fitting=False;self.scale=1;self.show_scaled()

    def zoom(self, factor):
        self.fitting=False
        pixels=max(1,self.pixmap.width()*self.pixmap.height())
        ceiling=min(4,math.sqrt(50_000_000/pixels))
        self.scale=max(.02,min(ceiling,self.scale*factor));self.show_scaled()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if getattr(self,'fitting',False) and hasattr(self,'scroll'):QTimer.singleShot(0,self.fit)


class AttachmentImage(QPushButton):
    def __init__(self, path, title, size=QSize(120,90), parent=None):
        super().__init__(parent)
        self.path=Path(path);self.image_title=title
        self.setObjectName('attachmentImage')
        self.setToolTip(tr('Görseli aç')+' · '+title)
        self.setAccessibleName(tr('Görseli aç')+' · '+title)
        self.setIcon(icon('image'));self.setIconSize(size)
        pixmap=QPixmap(str(path))
        if not pixmap.isNull():
            from PySide6.QtGui import QIcon
            self.setIcon(QIcon(pixmap))
        self.setFixedSize(size+QSize(8,8))
        self.setSizePolicy(QSizePolicy.Policy.Fixed,QSizePolicy.Policy.Fixed)
        self.clicked.connect(self.open_preview)

    def open_preview(self):
        if not self.path.is_file() or self.path.is_symlink():return
        viewer=ImagePreview(self.path,self.image_title,self.window())
        viewer.open()
        return viewer
