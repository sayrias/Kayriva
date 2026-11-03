from ..i18n import tr
import re
import math
import time
from PySide6.QtCore import QRect, Qt, Signal, QTimer, QUrl, QSize, QPropertyAnimation, QPoint, QEasingCurve, QEventLoop, QEvent
from PySide6.QtGui import QDesktopServices, QPainter, QColor, QRadialGradient, QBrush, QPainterPath, QPen, QFontMetricsF, QImage, QTextCursor, QTextBlockFormat, QFont
from PySide6.QtWidgets import (
    QCompleter, QVBoxLayout, QHBoxLayout, QSizePolicy, QGraphicsOpacityEffect, QStyledItemDelegate, QStyle, QListView, QAbstractItemView
)
from .icons import icon
from ..memory_units import GIB, MB, memory_text, memory_detail
from .localized import QListWidget, QListWidgetItem, QLineEdit, QSpinBox, QWidget, QFrame, QLabel, QPushButton, QCheckBox, QPlainTextEdit, QTextBrowser, QScrollArea, QSlider, QComboBox



class MemorySlider(QWidget):
    """100 MB decimal steps, exact hardware endpoint, persisted GiB budget."""
    valueChanged = Signal(float)
    step_bytes = 100 * MB

    def __init__(self, kind):
        super().__init__()
        self.kind = kind
        self.total_bytes = 0
        self.available_bytes = None
        self.resident_budget_bytes = None
        self.selected_bytes = 0
        self.updating = False
        self.setObjectName('memoryControl')
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        head = QHBoxLayout()
        self.automatic = QCheckBox(tr('Otomatik'))
        self.automatic.setChecked(True)
        head.addWidget(self.automatic)
        head.addStretch()
        self.amount = label('—', 'memoryAmount')
        head.addWidget(self.amount)
        layout.addLayout(head)
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setObjectName('memorySlider')
        self.slider.setMinimumHeight(22)
        self.slider.setSingleStep(1)
        self.slider.setPageStep(10)
        self.slider.setAccessibleName(f"{tr('Modelin kullanabileceği ')}{kind.upper()}")
        layout.addWidget(self.slider)
        self.details = label(tr('Kapasite algılanamadı'), 'status')
        layout.addWidget(self.details)
        self.automatic.toggled.connect(self.toggle_auto)
        self.slider.valueChanged.connect(self.move_slider)
        self.slider.sliderPressed.connect(self.start_drag)
        self.set_capacity(0)

    def value(self):
        return 0. if self.automatic.isChecked() else self.selected_bytes / GIB

    def currentData(self):
        return self.value()

    def setValue(self, value):
        self.updating = True
        self.automatic.setChecked(value <= 0)
        self.selected_bytes = max(0, round(value * GIB))
        if self.total_bytes:
            self.selected_bytes = min(self.total_bytes, self.selected_bytes)
        self.refresh()
        self.updating = False

    def set_capacity(self, total, available=None, resident_budget=None):
        self.updating = True
        self.total_bytes = max(0, int(total))
        self.available_bytes = None if available is None else max(0, min(self.total_bytes, int(available)))
        self.resident_budget_bytes = None if resident_budget is None else max(0,min(self.total_bytes,int(resident_budget)))
        self.slider.setRange(1, max(1, math.ceil(self.total_bytes / self.step_bytes)))
        self.slider.setEnabled(bool(self.total_bytes))
        self.automatic.setEnabled(bool(self.total_bytes))
        if self.total_bytes:
            self.selected_bytes = min(self.selected_bytes, self.total_bytes)
        self.refresh()
        self.updating = False

    def auto_bytes(self):
        if self.resident_budget_bytes is not None:
            return self.resident_budget_bytes
        free = self.total_bytes if self.available_bytes is None else self.available_bytes
        margin = min((2 if self.kind == 'ram' else 1) * GIB, self.total_bytes / 4)
        return max(0, int(free - margin))

    def refresh(self):
        automatic = self.automatic.isChecked()
        chosen = self.auto_bytes() if automatic else self.selected_bytes
        tick = self.slider.maximum() if chosen >= self.total_bytes else max(1, round(chosen / self.step_bytes))
        self.slider.blockSignals(True)
        self.slider.setValue(tick)
        self.slider.blockSignals(False)
        self.amount.setText(('~ ' if automatic else '') + memory_text(chosen) if self.total_bytes else '—')
        self.amount.setToolTip(memory_detail(chosen) + tr('\nÜst sınır; yalnızca ihtiyaç kadar kullanılır.'))
        text = tr('Toplam ') + memory_text(self.total_bytes) if self.total_bytes else tr('Kapasite algılanamadı · Donanımı yenile')
        if self.total_bytes:
            text += tr(' · Boş ') + (memory_text(self.available_bytes) if self.available_bytes is not None else tr('ölçülüyor…'))
        if not automatic and self.available_bytes is not None and chosen > self.available_bytes:
            text += tr(' · Seçilen sınır şu anki boş alanı aşıyor')
        if automatic and self.resident_budget_bytes is not None:
            text += tr(' · Model bellekte')
        self.details.setText(text)
        self.details.setToolTip(memory_detail(self.total_bytes) + tr('\nBoş alan modelin kullanımını da içerir. Bellekteki modelin yükleme bütçesi korunur; yeni yüklemede boş alan kontrol edilir. Ok tuşu: 100 MB.'))

    def start_drag(self):
        if self.automatic.isChecked():
            self.automatic.setChecked(False)

    def toggle_auto(self, automatic):
        if self.updating:
            return
        if not automatic:
            self.selected_bytes = min(self.total_bytes, self.slider.value() * self.step_bytes)
        self.refresh()
        self.valueChanged.emit(self.value())

    def move_slider(self, tick):
        if self.updating:
            return
        self.selected_bytes = min(self.total_bytes, tick * self.step_bytes)
        self.automatic.blockSignals(True)
        self.automatic.setChecked(False)
        self.automatic.blockSignals(False)
        self.refresh()
        self.valueChanged.emit(self.value())


def label(text, name=None):
    item = QLabel(text)
    if name:
        item.setObjectName(name)
    item.setWordWrap(True)
    return item


def button(text, slot=None, primary=False, icon_name=None):
    glyphs = {"＋": "plus", "✕": "close", "⚙": "settings", "⌘": "code", "↗": "globe", "↑": "send", "▾": "chevron-down", "▸": "chevron-right", "···": "more"}
    for glyph, name in glyphs.items():
        if glyph in text:
            icon_name = icon_name or name
            text = text.replace(glyph, "").strip()
    if "→" in text:
        text = text.replace("→", "").strip()
    item = QPushButton(text)
    if icon_name:
        item.setIcon(icon(icon_name, "#302443" if primary else "#c8bbed"))
        item.setIconSize(QSize(18, 18))
    if primary:
        item.setObjectName("primary")
    if slot:
        item.clicked.connect(slot)
    item.setCursor(Qt.CursorShape.PointingHandCursor)
    return item


class ModelButton(QPushButton):
    def __init__(self, slot):
        super().__init__(tr('Model seç'))
        self.setIcon(icon('models'))
        self.setIconSize(QSize(17,17))
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.clicked.connect(slot)

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        icon('chevron-down','#b5a1c9').paint(painter,QRect(self.width()-22,self.height()//2-7,14,14))


class ChoiceBox(QComboBox):
    """Keep native keyboard selection, with consistent readable popup rows."""
    def __init__(self, parent=None):
        super().__init__(parent)
        view = QListView(self)
        view.setUniformItemSizes(True)
        view.setMaximumHeight(330)
        view.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        view.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setView(view)
        self.setMaxVisibleItems(10)
        self.setCursor(Qt.CursorShape.PointingHandCursor)


class BrandPicker(ChoiceBox):
    """Read-only trigger; search belongs inside the bounded popup."""
    def __init__(self):
        super().__init__()
        self.setEditable(False)
        self.setMinimumWidth(180)
        self.setMaximumWidth(260)
        self.setAccessibleName(tr('Model markası'))
        self.popup = QFrame(self, Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        self.popup.setObjectName('brandPopup')
        layout = QVBoxLayout(self.popup)
        layout.setContentsMargins(8,8,8,8)
        layout.setSpacing(6)
        self.search = QLineEdit()
        self.search.setPlaceholderText(tr('Marka ara…'))
        self.search.setClearButtonEnabled(True)
        self.search.setAccessibleName(tr('Marka ara…'))
        layout.addWidget(self.search)
        self.results = QListWidget()
        self.results.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        layout.addWidget(self.results)
        self.search.textChanged.connect(self.filter_brands)
        self.search.returnPressed.connect(self.choose_current)
        self.results.itemClicked.connect(self.choose_item)
        self.results.itemActivated.connect(self.choose_item)
        self.search.installEventFilter(self)

    def filter_brands(self):
        self.results.clear()
        needle = self.search.text().casefold().strip()
        selected = 0
        for index in range(self.count()):
            if needle and needle not in self.itemText(index).casefold():
                continue
            item = QListWidgetItem(self.itemText(index))
            item.setData(Qt.ItemDataRole.UserRole, index)
            if index == self.currentIndex():
                selected = self.results.count()
            self.results.addItem(item)
        if self.results.count():
            self.results.setCurrentRow(selected)

    def choose_item(self, item):
        if item:
            self.setCurrentIndex(item.data(Qt.ItemDataRole.UserRole))
            self.popup.hide()
            self.setFocus()

    def choose_current(self):
        self.choose_item(self.results.currentItem())

    def showPopup(self):
        self.search.clear()
        self.filter_brands()
        self.popup.resize(max(240,self.width()), min(350, 60+self.count()*32))
        point = self.mapToGlobal(QPoint(0,self.height()+5))
        screen = self.screen().availableGeometry()
        if point.y()+self.popup.height()>screen.bottom():
            point.setY(self.mapToGlobal(QPoint(0,0)).y()-self.popup.height()-5)
        point.setX(min(point.x(),screen.right()-self.popup.width()))
        self.popup.move(point)
        self.popup.show()
        self.search.setFocus()

    def hidePopup(self):
        self.popup.hide()

    def eventFilter(self, watched, event):
        if watched is self.search and event.type()==QEvent.Type.KeyPress and event.key() in (Qt.Key.Key_Down,Qt.Key.Key_Up):
            direction = 1 if event.key()==Qt.Key.Key_Down else -1
            self.results.setCurrentRow(max(0,min(self.results.count()-1,self.results.currentRow()+direction)))
            return True
        return super().eventFilter(watched,event)


class LayerControl(QWidget):
    """Automatic offload or an exact layer count, without an unbounded popup."""
    valueChanged = Signal(int)

    def __init__(self):
        super().__init__()
        self.limit = 0
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        row = QHBoxLayout()
        self.automatic = QCheckBox(tr('Otomatik'))
        self.automatic.setChecked(True)
        self.automatic.setToolTip(tr('Bellek bütçesine göre GPU katmanlarını motor seçer.'))
        self.number = QSpinBox()
        self.number.setRange(0, 0)
        self.number.setAccessibleName(tr('GPU katman sayısı'))
        self.number.setMinimumWidth(90)
        row.addWidget(self.automatic)
        row.addStretch()
        row.addWidget(self.number)
        layout.addLayout(row)
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setObjectName('memorySlider')
        self.slider.setRange(0, 0)
        self.slider.setAccessibleName(tr('GPU katman sayısı'))
        self.slider.setMinimumHeight(22)
        layout.addWidget(self.slider)
        self.note = label(tr('Katman sınırı seçili modelden okunur.'), 'status')
        layout.addWidget(self.note)
        self.number.valueChanged.connect(self.change_number)
        self.slider.valueChanged.connect(self.number.setValue)
        self.automatic.toggled.connect(self.toggle_auto)
        self.toggle_auto(True)

    def value(self):
        return -1 if self.automatic.isChecked() else self.number.value()

    def currentData(self):
        return self.value()

    def setValue(self, value):
        blocked = self.blockSignals(True)
        self.automatic.setChecked(value < 0)
        self.number.setValue(max(0, value))
        self.blockSignals(blocked)

    def setMaximumLayers(self, maximum):
        self.limit = max(0, int(maximum))
        self.number.setMaximum(self.limit)
        self.slider.setMaximum(self.limit)
        self.number.setSuffix(' / ' + str(self.limit) if self.limit else '')
        self.number.setSpecialValueText(tr('Model seç') if not self.limit else '')
        self.note.setText(tr('0: CPU · En fazla {count} GPU katmanı.', count=self.limit) if self.limit else tr('Katman sınırı seçili modelden okunur.'))
        self.toggle_auto(self.automatic.isChecked(), emit=False)

    def change_number(self, value):
        self.slider.setValue(value)
        self.valueChanged.emit(self.value())

    def toggle_auto(self, automatic, emit=True):
        self.number.setEnabled(not automatic and self.limit > 0)
        self.slider.setEnabled(not automatic and self.limit > 0)
        if emit:
            self.valueChanged.emit(self.value())


class ProjectItemDelegate(QStyledItemDelegate):
    """One sidebar row system for projects, nested chats and recent chats."""
    def sizeHint(self, option, index):
        return QSize(option.rect.width(),36)

    def paint(self, painter, option, index):
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        payload = index.data(Qt.ItemDataRole.UserRole)
        project = isinstance(payload, (tuple, list)) and payload[0] == 'project'
        child = index.parent().isValid()
        row=option.rect.adjusted(20 if child else 0,2,-2,-2)
        selected=bool(option.state & QStyle.StateFlag.State_Selected)
        hovered=bool(option.state & QStyle.StateFlag.State_MouseOver)
        if selected or hovered:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor('#303542' if selected else '#22262f'))
            painter.drawRoundedRect(row,8,8)
        if option.state & QStyle.StateFlag.State_HasFocus:
            painter.setPen(QPen(QColor('#a898c6'), 1))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(row.adjusted(1,1,-1,-1),7,7)
        text_rect=row.adjusted(10,0,-10,0)
        decoration=index.data(Qt.ItemDataRole.DecorationRole)
        if project:
            icon('folder','#c5b7e2' if selected else '#a4a9ba').paint(painter,QRect(text_rect.left(),row.center().y()-8,16,16))
            text_rect.setLeft(text_rect.left()+24)
            count = index.model().rowCount(index)
            if count:
                tree=self.parent()
                icon('chevron-down' if tree.isExpanded(index) else 'chevron-right','#a1a5b5').paint(painter,QRect(row.right()-23,row.center().y()-7,14,14))
                count_rect=QRect(row.right()-52,row.top(),24,row.height())
                painter.setPen(QColor('#a1a5b5'))
                painter.drawText(count_rect,Qt.AlignmentFlag.AlignCenter,str(count))
                text_rect.setRight(row.right()-58)
        else:
            glyph=decoration if decoration is not None and not decoration.isNull() else icon('chat','#c5b7e2' if selected else '#7f879b')
            glyph.paint(painter,QRect(text_rect.left(),row.center().y()-7,14,14))
            text_rect.setLeft(text_rect.left()+22)
        painter.setPen(QColor('#f0edf7' if selected else '#d9dbe5' if project else '#b8bece'))
        font=option.font
        font.setWeight(QFont.Weight.Medium if project else QFont.Weight.Normal)
        painter.setFont(font)
        title=option.fontMetrics.elidedText(str(index.data() or ''),Qt.TextElideMode.ElideRight,max(0,text_rect.width()))
        painter.drawText(text_rect,Qt.AlignmentFlag.AlignVCenter|Qt.AlignmentFlag.AlignLeft,title)
        painter.restore()


class ProjectHeader(QFrame):
    """Stable section header; project actions stay visible and keyboard reachable."""
    def __init__(self):
        super().__init__()
        self.actions = []
        self.setObjectName("projectHeader")

    def reveal(self, visible):
        for action in self.actions:
            action.setVisible(visible)

class PreferencesOverlay(QWidget):
    """An in-window modal surface; no second native window or title bar."""
    def __init__(self, parent, surfaces):
        super().__init__(parent)
        self.setObjectName("preferencesOverlay")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground)
        self.surfaces = surfaces
        self.panel = QFrame()
        self.panel.setObjectName("preferences")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.panel, alignment=Qt.AlignmentFlag.AlignCenter)
        self.hide()

    def fit(self):
        self.setGeometry(self.parentWidget().rect())
        self.panel.setFixedSize(min(1000, self.width()-40), min(740, self.height()-40))

    def showEvent(self, event):
        self.fit()
        self.previous_states = [surface.isEnabled() for surface in self.surfaces]
        for surface in self.surfaces:
            surface.setEnabled(False)
        super().showEvent(event)

    def hideEvent(self, event):
        for surface, enabled in zip(self.surfaces, getattr(self, 'previous_states', [])):
            surface.setEnabled(enabled)
        super().hideEvent(event)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.close()
            event.accept()
        else:
            super().keyPressEvent(event)

    def mousePressEvent(self, event):
        if not self.panel.geometry().contains(event.position().toPoint()):
            self.close()
        super().mousePressEvent(event)


class InlineDialog(PreferencesOverlay):
    """Small nested modal, embedded in the existing native window."""
    def __init__(self, parent, title, width=480, height=300, surfaces=None):
        super().__init__(parent, surfaces or [])
        self.dialog_size = (width, height)
        self.result = 0
        self.loop = None
        self.body = QVBoxLayout(self.panel)
        self.body.setContentsMargins(20, 16, 20, 20)
        self.body.setSpacing(14)
        head = QHBoxLayout()
        head.addWidget(label(title, 'brand'), 1)
        close = button('', self.reject, icon_name='close')
        close.setObjectName('closePreferences')
        close.setFixedSize(28, 28)
        close.setToolTip(tr('Kapat'))
        head.addWidget(close)
        self.body.addLayout(head)

    def fit(self):
        self.setGeometry(self.parentWidget().rect())
        width, height = self.dialog_size
        self.panel.setFixedSize(min(width,self.width()-32), min(height,self.height()-32))

    def accept(self):
        self.result = 1
        self.close()

    def reject(self):
        self.result = 0
        self.close()

    def hideEvent(self, event):
        super().hideEvent(event)
        if self.loop:
            self.loop.quit()

    def exec(self):
        self.loop = QEventLoop()
        self.show()
        self.raise_()
        self.panel.setFocus()
        self.loop.exec()
        self.loop = None
        return self.result


class UsageChart(QWidget):
    def __init__(self):
        super().__init__()
        self.points = []
        self.setMinimumHeight(140)
        self.setMouseTracking(True)
        self.setAccessibleName(tr('Günlük token kullanımı'))

    def set_points(self, points):
        self.points = points
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        maximum = max([v for _,v in self.points] or [0])
        if not maximum:
            painter.setPen(QColor('#8f8999'))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, tr('Henüz kullanım yok'))
            return
        left, top, bottom = 48, 15, self.height()-28
        width = max(1,self.width()-left-12)
        for ratio in [0,.5,1]:
            y = bottom-(bottom-top)*ratio
            painter.setPen(QColor('#353139'))
            painter.drawLine(left,int(y),self.width()-10,int(y))
            painter.setPen(QColor('#958c9e'))
            number=maximum*ratio
            text=f'{number/1_000_000:.1f}M' if number>=1_000_000 else f'{number/1000:.1f}K' if number>=1000 else str(int(number))
            painter.drawText(0,int(y)+4,text)
        step = width/len(self.points)
        painter.setPen(Qt.PenStyle.NoPen)
        for i,(day,value) in enumerate(self.points):
            height = (bottom-top)*value/maximum
            painter.setBrush(QColor('#b8a2d5'))
            painter.drawRoundedRect(int(left+i*step+step*.22),int(bottom-height),max(2,int(step*.56)),max(0,int(height)),3,3)
            if len(self.points)<=7 or i%5==0 or i==len(self.points)-1:
                painter.setPen(QColor('#958c9e'))
                painter.drawText(int(left+i*step),self.height()-7,day[8:10]+'.'+day[5:7])
                painter.setPen(Qt.PenStyle.NoPen)

    def mouseMoveEvent(self, event):
        if self.points and event.position().x()>=48:
            i = min(len(self.points)-1,int((event.position().x()-48)/max(1,self.width()-60)*len(self.points)))
            day,value = self.points[i]
            self.setToolTip(f'{day} · {value:,} token')
        super().mouseMoveEvent(event)


class LiveChart(QWidget):
    def __init__(self):
        super().__init__()
        self.points=[]
        self.setMinimumHeight(110)
        self.setToolTip(tr('Son 60 saniye · token/sn'))
        self.setAccessibleName(tr('Anlık üretim hızı grafiği'))

    def append(self, value):
        self.points=(self.points+[max(0,value)])[-60:]
        self.update()

    def paintEvent(self,event):
        painter=QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        if not any(self.points):
            painter.setPen(QColor('#8f8999'))
            painter.drawText(self.rect(),Qt.AlignmentFlag.AlignCenter,tr('Üretim başladığında hız grafiği görünür'))
            return
        top,bottom,left=12,self.height()-22,38
        maximum=max(1,max(self.points)*1.15)
        width=self.width()-left-12
        for ratio in [0,.5,1]:
            y=bottom-(bottom-top)*ratio
            painter.setPen(QColor('#38323f'))
            painter.drawLine(left,int(y),self.width()-12,int(y))
            painter.setPen(QColor('#9b90a5'))
            painter.drawText(0,int(y)+4,f'{maximum*ratio:.0f}')
        path=QPainterPath()
        offset=60-len(self.points)
        for i,value in enumerate(self.points):
            x=left+(offset+i)*width/59
            y=bottom-value/maximum*(bottom-top)
            if i: path.lineTo(x,y)
            else: path.moveTo(x,y)
        painter.setPen(QPen(QColor('#cbb4e6'),2))
        painter.drawPath(path)
        painter.setPen(QColor('#9b90a5'))
        painter.drawText(left,self.height()-3,tr('60 sn önce'))
        painter.drawText(self.width()-45,self.height()-3,tr('Şimdi'))


class Welcome(QFrame):
    """Animation only runs while the empty-chat welcome is visible."""
    def __init__(self):
        super().__init__()
        self.started = time.monotonic()
        self.timer = QTimer(self)
        self.timer.setInterval(50)
        self.timer.timeout.connect(self.update)

    def showEvent(self, event):
        self.timer.start()
        super().showEvent(event)

    def hideEvent(self, event):
        self.timer.stop()
        super().hideEvent(event)

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        t = time.monotonic() - self.started
        for cx, cy, radius, rgba in [
            (self.width() * .42 + math.sin(t / 5) * 28, 150 + math.cos(t / 6) * 18, 215, (117, 83, 181, 29)),
            (self.width() * .68 + math.cos(t / 7) * 24, 220 + math.sin(t / 5) * 20, 160, (64, 123, 136, 17)),
        ]:
            gradient = QRadialGradient(cx, cy, radius)
            gradient.setColorAt(0, QColor(*rgba))
            gradient.setColorAt(1, QColor(rgba[0], rgba[1], rgba[2], 0))
            painter.fillRect(self.rect(), QBrush(gradient))
        painter.end()


class ComposerMenu(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent, Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        self.setObjectName("composerMenu")
        self.animation = QPropertyAnimation(self, b"pos", self)
        self.animation.setDuration(190)
        self.animation.setEasingCurve(QEasingCurve.Type.OutCubic)

    def open_above(self, anchor):
        self.adjustSize()
        destination = anchor.mapToGlobal(QPoint(0, -self.height() - 12))
        screen = anchor.screen().availableGeometry()
        destination.setX(min(max(screen.left() + 10, destination.x()), screen.right() - self.width() - 10))
        destination.setY(max(screen.top() + 10, destination.y()))
        self.move(destination + QPoint(0, 18))
        self.show()
        self.animation.stop()
        self.animation.setStartValue(destination + QPoint(0, 18))
        self.animation.setEndValue(destination)
        self.animation.start()

    def open_below(self, anchor):
        self.adjustSize()
        screen = anchor.screen().availableGeometry()
        destination = anchor.mapToGlobal(QPoint(anchor.width()-self.width(), anchor.height()+8))
        destination.setX(min(max(screen.left()+10, destination.x()),screen.right()-self.width()-10))
        destination.setY(min(destination.y(),screen.bottom()-self.height()-10))
        self.move(destination-QPoint(0,8))
        self.show()
        self.animation.stop()
        self.animation.setStartValue(destination-QPoint(0,8))
        self.animation.setEndValue(destination)
        self.animation.start()


class MenuRow(QPushButton):
    def __init__(self, title, detail="", name="file", slot=None, trailing="", chevron=False):
        super().__init__()
        self.setObjectName("menuRow")
        self.setFixedHeight(38)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAccessibleName(title)
        box = QHBoxLayout(self)
        box.setContentsMargins(10, 0, 10, 0)
        box.setSpacing(9)
        mark = QLabel()
        mark.setPixmap(icon(name, "#c9c5d0").pixmap(17, 17))
        box.addWidget(mark)
        self.title = QLabel(title)
        box.addWidget(self.title)
        self.detail = QLabel(detail)
        self.detail.setObjectName("menuHint")
        box.addWidget(self.detail, 1)
        self.trailing = QLabel(trailing)
        self.trailing.setObjectName("menuHint")
        box.addWidget(self.trailing)
        for child in [mark, self.title, self.detail, self.trailing]:
            child.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        if chevron:
            arrow = QLabel()
            arrow.setPixmap(icon("chevron-right", "#aaa4b0").pixmap(14, 14))
            arrow.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
            box.addWidget(arrow)
        if slot:
            self.clicked.connect(slot)


class ModelOption(QPushButton):
    """A complete model row, with metadata on its own line."""
    def __init__(self, title, detail, slot, selected=False):
        super().__init__()
        self.setObjectName('modelOption')
        self.setProperty('selected', selected)
        self.setFixedHeight(60)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAccessibleName(title + ' · ' + detail + (tr(' · Seçili') if selected else ''))
        self.setToolTip(title + '\n' + detail)
        box=QHBoxLayout(self)
        box.setContentsMargins(10,7,10,7)
        box.setSpacing(11)
        mark=QLabel();mark.setFixedSize(24,24)
        mark.setPixmap(icon('models','#cdbde7' if selected else '#a39aa9').pixmap(19,19))
        box.addWidget(mark)
        text=QVBoxLayout();text.setSpacing(3)
        self.title=QLabel(title);self.title.setObjectName('modelName')
        self.title.setSizePolicy(QSizePolicy.Policy.Ignored,QSizePolicy.Policy.Preferred)
        self.detail=QLabel(detail);self.detail.setObjectName('modelDetail')
        self.detail.setSizePolicy(QSizePolicy.Policy.Ignored,QSizePolicy.Policy.Preferred)
        text.addWidget(self.title);text.addWidget(self.detail)
        box.addLayout(text,1)
        self.check=QLabel();self.check.setFixedSize(18,18)
        if selected:self.check.setPixmap(icon('check','#d9cbed').pixmap(17,17))
        box.addWidget(self.check)
        for child in self.findChildren(QLabel):
            child.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.clicked.connect(slot)


class ActivityDetails(QFrame):
    """A compact timeline of actual reported stages, with readable explanations."""
    changed = Signal()

    def __init__(self):
        super().__init__()
        self.setObjectName('activityDetails')
        self.rows=QVBoxLayout(self)
        self.rows.setContentsMargins(0,8,0,8)
        self.rows.setSpacing(8)
        self.rows.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.activities=[]
        self.expanded_keys=set()
        self.expanded_groups=set()

    @staticmethod
    def explain(text):
        normalized=text.casefold()
        for fragment,title,detail in [
            ('araştırma kapsamı',tr('Araştırmayı hazırlama'),tr('Konuyu farklı açılardan ele alan sorgular')),
            ('web’de',tr('Web araması'),tr('Birden fazla sorguyla kaynak toplama')),
            ('kaynak metni',tr('Kaynakları okuma'),tr('Sayfalardan okunabilir metin alma')),
            ('kaynaklar inceleniyor',tr('Kaynakları inceleme'),tr('Okunan metinleri araştırmaya ekleme')),
            ('metin incelendi',tr('Araştırma kaynakları hazır'),tr('İncelenen metinleri modele sunma')),
            ('proje dosyası yazılıyor',tr('Dosyayı yazma'),tr('Sonucu seçili proje klasörüne kaydetme')),
            ('proje dosyası düzenleniyor',tr('Dosyayı düzenleme'),tr('Eşleşen metin bölümünü değiştirme')),
            ('proje dosyası okunuyor',tr('Dosyayı okuma'),tr('Projedeki metin dosyasını inceleme')),
            ('proje dosyaları listeleniyor',tr('Proje dosyaları'),tr('Projenin dosyalarını listeleme')),
            ('bellek bütçesi',tr('Bellek kontrolü'),tr('RAM ve GPU için kullanılabilir alan')),
            ('model belleğe',tr('Model yükleme'),tr('Model ağırlıklarını yerel belleğe aktarma')),
            ('yerel model hazır',tr('Model hazır'),tr('Yerel motorun çalışmaya hazır olması')),
            ('mesaj işleniyor',tr('Mesajı işleme'),tr('Sohbet bağlamını ve isteği değerlendirme')),
            ('yanıt oluşturuluyor',tr('Yanıtı hazırlama'),tr('Modelin yanıt metnini üretmesi')),
            ('yerel model düşünüyor',tr('İsteği hazırlama'),tr('Yanıt için yerel motoru hazırlama')),
            ('onay bekleniyor',tr('Onay bekleniyor'),tr('İşleme devam etmek için onay gerekli')),
            ('derin düşünme',tr('Derin düşünme'),tr('Modelin ek değerlendirme yapması')),
            ('hazırlanıyor',tr('Hazırlık'),tr('İstek ve araçları hazırlama')),
        ]:
            english_fragments = {
                'araştırma kapsamı': 'research scope', 'web’de': 'web queries',
                'kaynak metni': 'source texts', 'kaynaklar inceleniyor': 'reviewing sources',
                'metin incelendi': 'texts read', 'proje dosyası yazılıyor': 'writing project file',
                'proje dosyası düzenleniyor': 'editing project file', 'proje dosyası okunuyor': 'reading project file',
                'proje dosyaları listeleniyor': 'listing project files', 'bellek bütçesi': 'memory budget',
                'model belleğe': 'loading model', 'yerel model hazır': 'local model ready',
                'mesaj işleniyor': 'processing message', 'yanıt oluşturuluyor': 'generating response',
                'yerel model düşünüyor': 'local model is thinking', 'onay bekleniyor': 'waiting for approval',
                'derin düşünme': 'extended reasoning', 'hazırlanıyor': 'preparing',
            }
            if fragment in normalized or english_fragments[fragment] in normalized:
                return title,detail
        return text.rstrip('….'),tr('Yerel işlem')

    @staticmethod
    def batches(activities):
        """Keep public updates in place; compact adjacent operations underneath."""
        result=[]
        for index, entry in enumerate(activities):
            if entry.get('kind') == 'message':
                result.append({'kind':'message','entry':entry})
            else:
                if not result or result[-1]['kind'] != 'group':
                    result.append({'kind':'group','key':'group:'+str(entry.get('key') or index),'entries':[]})
                result[-1]['entries'].append(entry)
        # Preparation may arrive on the status signal before the public update.
        # Put that opening update first while retaining all operation details.
        if result and result[0]['kind']=='group' and len(result)>1 and result[1]['kind']=='message':
            if not any(e.get('kind') in {'tool','skill','integration'} for e in result[0]['entries']):
                result[0],result[1]=result[1],result[0]
                if len(result)>2 and result[2]['kind']=='group':
                    result[1]['entries'].extend(result[2]['entries']);result.pop(2)
        return result

    @staticmethod
    def group_title(entries):
        actual=[e for e in entries if e.get('kind') in {'tool','skill','integration'}]
        providers=list(dict.fromkeys(e.get('provider') for e in actual if e.get('provider')))
        skills=list(dict.fromkeys(e.get('skill_name') or e.get('title','') for e in actual if e.get('kind')=='skill'))
        names=[str(e.get('tool_name') or e.get('name') or e.get('title','')).casefold() for e in actual]
        if providers:
            return ', '.join(providers)+tr(' · entegrasyon işlemleri'), 'tools'
        if skills:
            return ', '.join(skills)+tr(' · beceri kullanımı'), 'book'
        if any('workspace_write' in n or 'workspace_edit' in n or 'yazma' in n or 'write' in n for n in names):
            return tr('Dosya okuma ve düzenleme'), 'file'
        if any('workspace' in n or 'read' in n or 'okuma' in n for n in names):
            return tr('Proje dosyalarını inceleme'), 'book'
        if any('web' in n for n in names):
            return tr('Web kaynaklarını araştırma'), 'globe'
        if actual:return tr('Araç işlemleri'), 'tools'
        return tr('Hazırlık ve model işlemleri'), 'clock'

    def set_activities(self, activities, state='running'):
        self.activities=list(activities)[-80:]
        while self.rows.count():
            item=self.rows.takeAt(0)
            if item.widget():item.widget().hide();item.widget().deleteLater()
        batches=self.batches(self.activities)
        for batch_index,batch in enumerate(batches):
            if batch['kind']=='message':
                note=label(str(batch['entry'].get('text',''))[:6000],'activityNarrative')
                note.setTextFormat(Qt.TextFormat.PlainText)
                note.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
                self.rows.addWidget(note)
                continue
            entries=batch['entries'];key=batch['key']
            group=QWidget();group.setObjectName('activityGroup')
            box=QVBoxLayout(group);box.setContentsMargins(0,2,0,6);box.setSpacing(7)
            title,glyph=self.group_title(entries)
            running=state=='running' and batch_index==len(batches)-1
            heading=QHBoxLayout();heading.setContentsMargins(0,0,0,0);heading.setSpacing(7)
            toggle=button(title,icon_name=glyph);toggle.setObjectName('activityGroupToggle');toggle.setCheckable(True)
            toggle.setChecked(key in self.expanded_groups)
            toggle.setToolTip(tr('İşlem grubunu aç veya kapat'))
            heading.addWidget(toggle,1)
            actual_count=sum(e.get('kind') in {'tool','skill','integration'} for e in entries)
            count=label(str(actual_count)+tr(' işlem') if actual_count else str(len(entries))+tr(' aşama'),'activityTime');count.setWordWrap(False);heading.addWidget(count)
            arrow=button('',icon_name='chevron-down' if toggle.isChecked() else 'chevron-right');arrow.setObjectName('activityGroupArrow');arrow.setFixedSize(26,26)
            heading.addWidget(arrow);arrow.clicked.connect(toggle.toggle)
            box.addLayout(heading)
            details=QScrollArea();details.setObjectName('activityGroupDetails');details.setFrameShape(QFrame.Shape.NoFrame);details.setWidgetResizable(True)
            content=QWidget();rows=QVBoxLayout(content);rows.setContentsMargins(12,5,8,5);rows.setSpacing(6)
            details.setWidget(content)
            for index,entry in enumerate(entries):
                line=QWidget();line.setObjectName('activityOperation')
                layout=QVBoxLayout(line);layout.setContentsMargins(0,0,0,0);layout.setSpacing(5)
                main=QHBoxLayout();main.setContentsMargins(0,0,0,0);main.setSpacing(8)
                actual=entry.get('kind') in {'tool','skill','integration'}
                entry_state=entry.get('state',state if index==len(entries)-1 and running else 'complete')
                mark='clock' if entry_state=='running' and state=='running' else 'stop' if entry_state in {'failed','running'} else 'check'
                marker=QLabel();marker.setFixedSize(16,23);marker.setPixmap(icon(mark,'#a6a4b6').pixmap(13,13));main.addWidget(marker)
                if actual:
                    event_key=str(entry.get('key') or index)
                    control=button(str(entry.get('title') or entry.get('text','')),icon_name='chevron-down' if event_key in self.expanded_keys else 'chevron-right')
                    control.setObjectName('activityTool');control.setCheckable(True);control.setChecked(event_key in self.expanded_keys)
                    main.addWidget(control,1)
                    payload=QPlainTextEdit();payload.setReadOnly(True);payload.setObjectName('activityPayload')
                    payload.setPlainText(str(entry.get('detail',''))+ ('\n\n'+str(entry['summary']) if entry.get('summary') else ''))
                    payload.setFixedHeight(min(180,max(88,40+payload.toPlainText().count('\n')*16)))
                    payload.setVisible(event_key in self.expanded_keys)
                    def expand(checked,k=event_key,field=payload,button=control,scroll=details,body=content):
                        self.expanded_keys.add(k) if checked else self.expanded_keys.discard(k)
                        field.setVisible(checked);button.setIcon(icon('chevron-down' if checked else 'chevron-right'))
                        body.layout().invalidate();scroll.setFixedHeight(min(280,max(44,body.sizeHint().height()+6)))
                        self.changed.emit()
                    control.toggled.connect(expand)
                else:
                    text=label(str(entry.get('text','')),'activityStepHint');text.setTextFormat(Qt.TextFormat.PlainText);main.addWidget(text,1)
                stamp=label(self.duration(entry.get('seconds',0)),'activityTime');stamp.setWordWrap(False);main.addWidget(stamp)
                layout.addLayout(main)
                if actual:layout.addWidget(payload)
                rows.addWidget(line)
            details.setFixedHeight(min(280,max(44,content.sizeHint().height()+6)))
            details.setVisible(key in self.expanded_groups);box.addWidget(details)
            def open_group(checked,k=key,section=details,chevron=arrow):
                self.expanded_groups.add(k) if checked else self.expanded_groups.discard(k)
                section.setVisible(checked);chevron.setIcon(icon('chevron-down' if checked else 'chevron-right'));self.changed.emit()
            toggle.toggled.connect(open_group)
            if running and entries:
                latest=entries[-1]
                status=label(str(latest.get('text') or latest.get('title','')),'activityStepHint')
                status.setContentsMargins(25,0,0,0);status.setTextFormat(Qt.TextFormat.PlainText)
                box.addWidget(status)
            self.rows.addWidget(group)
        if not self.activities:self.rows.addWidget(label(tr('Bu yanıt için işlem ayrıntısı kaydedilmemiş.'),'status'))
        self.changed.emit()

    @staticmethod
    def duration(seconds):
        seconds=max(0,int(seconds))
        return str(seconds//60)+tr(' dk ')+str(seconds%60)+tr(' sn') if seconds>=60 else str(seconds)+tr(' sn')

    def toPlainText(self):
        return '\n'.join(self.duration(a.get('seconds',0))+' · '+a.get('text',a.get('title','')) for a in self.activities)


def card():
    widget = QFrame()
    widget.setObjectName("card")
    layout = QVBoxLayout(widget)
    layout.setContentsMargins(20, 18, 20, 18)
    layout.setSpacing(12)
    return widget, layout


class Input(QPlainTextEdit):
    height_changed = Signal(int)
    send = Signal()
    image_pasted = Signal(object)
    files_pasted = Signal(object)

    def __init__(self):
        super().__init__()
        self.height_limit = 330
        self.setAcceptDrops(True)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.textChanged.connect(self.schedule_fit)
        self.document().documentLayout().documentSizeChanged.connect(self.schedule_fit)
        self.schedule_fit()

    def set_height_limit(self, limit):
        self.height_limit = max(140,min(440,int(limit)))
        self.schedule_fit()

    def schedule_fit(self, *args):
        if not getattr(self,'fit_pending',False):
            self.fit_pending=True
            QTimer.singleShot(0,self.fit_content)

    def fit_content(self):
        self.fit_pending=False
        block=self.document().begin()
        height=0
        while block.isValid():
            height+=self.blockBoundingRect(block).height()
            block=block.next()
        desired=max(78, int(height+self.document().documentMargin()*2+12))
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded if desired>self.height_limit else Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        target=min(self.height_limit,desired)
        if self.height()!=target:
            self.setFixedHeight(target)
            self.height_changed.emit(target)

    def resizeEvent(self,event):
        super().resizeEvent(event)
        self.schedule_fit()

    def canInsertFromMimeData(self,source):
        return source.hasImage() or source.hasUrls() or super().canInsertFromMimeData(source)

    def insertFromMimeData(self,source):
        paths=[url.toLocalFile() for url in source.urls() if url.isLocalFile()] if source.hasUrls() else []
        if paths:
            self.files_pasted.emit(paths)
        elif source.hasImage():
            value=source.imageData()
            image=value.toImage() if hasattr(value,'toImage') else QImage(value)
            if not image.isNull():
                self.image_pasted.emit(image)
        else:
            super().insertFromMimeData(source)

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter) and not event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
            self.send.emit()
        else:
            super().keyPressEvent(event)


class Message(QFrame):
    rendered = Signal()
    sources_requested = Signal(object)
    resume_requested = Signal()

    def __init__(self, role, text=""):
        super().__init__()
        self.role, self.text = role, text
        self.shown_text = text
        self.buffer = ''
        self.display_mode = 'blocks'
        self.running = False
        self.started = 0
        self.stage = ''
        self.metadata = {}
        self.live_activities = []
        self.rendered_text = None
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setObjectName("userMessage" if role == "user" else "assistantMessage")
        layout = QVBoxLayout(self)
        layout.setSpacing(6 if role == 'user' else 4)
        layout.setContentsMargins(16, 10, 46, 10) if role == 'user' else layout.setContentsMargins(6, 8, 6, 8)
        self.copy_button = button("", self.copy, icon_name="copy")
        self.copy_button.setToolTip(tr('Mesajı kopyala'))
        self.copy_button.setAccessibleName(tr('Mesajı kopyala'))
        self.copy_button.setObjectName("messageAction" if role != 'user' else 'iconButton')
        self.copy_button.setFixedSize(30, 30)
        self.copy_button.setIconSize(QSize(17,17))
        if role == 'user':
            self.copy_button.setParent(self)
            effect_target = self.copy_button
        else:
            self.activity_button = button(tr('Yanıt'), self.toggle_activity, icon_name='chevron-right')
            self.activity_button.setObjectName('activitySummary')
            self.activity_button.setFixedHeight(26)
            self.activity_button.setIconSize(QSize(13,13))
            self.activity_button.setToolTip(tr('Çalışma süresi ve gerçek işlem aşamaları'))
            layout.addWidget(self.activity_button, alignment=Qt.AlignmentFlag.AlignLeft)
            self.activity_divider=QFrame()
            self.activity_divider.setObjectName('activityDivider')
            self.activity_divider.setFixedHeight(1)
            layout.addWidget(self.activity_divider)
            self.activity_details = ActivityDetails()
            self.activity_details.hide()
            self.activity_details.changed.connect(lambda: QTimer.singleShot(0,self.refresh))
            layout.addWidget(self.activity_details)
        self.view = QTextBrowser()
        self.view.setObjectName('messageText')
        self.view.setOpenLinks(False)
        self.view.anchorClicked.connect(self.open_link)
        self.view.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.view.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.view.document().setDocumentMargin(0)
        self.view.document().setDefaultStyleSheet("pre { background: #15181f; padding: 12px; } code { color: #bfb2e6; font-family: monospace; } a { color: #b8c9ec; } th, td { padding: 6px; }")
        layout.addWidget(self.view)
        if role != 'user':
            self.error_label = label('', 'status')
            self.error_label.hide()
            layout.addWidget(self.error_label)
            self.resume_button=button(tr('Çalışmaya devam et'),self.resume_requested.emit,icon_name='play')
            self.resume_button.setObjectName('resumeTask')
            self.resume_button.hide()
            layout.addWidget(self.resume_button,alignment=Qt.AlignmentFlag.AlignLeft)
            self.footer = QWidget()
            self.footer.setObjectName('messageActions')
            actions = QHBoxLayout(self.footer)
            actions.setContentsMargins(0,0,0,0)
            actions.setSpacing(4)
            actions.addWidget(self.copy_button)
            for name, title, slot in [('text-select',tr('Metni seç'),self.select_text),('download',tr('Yanıtı kaydet'),self.save_text)]:
                control=button('',slot,icon_name=name)
                control.setObjectName('messageAction')
                control.setFixedSize(30,30)
                control.setIconSize(QSize(17,17))
                control.setToolTip(title)
                control.setAccessibleName(title)
                control.installEventFilter(self)
                actions.addWidget(control)
            self.sources_button=button('',lambda:self.sources_requested.emit(self.metadata.get('sources',[])),icon_name='globe')
            self.sources_button.setObjectName('messageAction')
            self.sources_button.setFixedSize(30,30)
            self.sources_button.setIconSize(QSize(17,17))
            self.sources_button.setToolTip(tr('Araştırma kaynakları'))
            self.sources_button.setAccessibleName(tr('Araştırma kaynakları'))
            self.sources_button.installEventFilter(self)
            self.sources_button.hide()
            actions.addWidget(self.sources_button)
            actions.addStretch()
            layout.addWidget(self.footer)
            effect_target = self.footer
        self.copy_opacity = QGraphicsOpacityEffect(effect_target)
        self.copy_opacity.setOpacity(0)
        effect_target.setGraphicsEffect(self.copy_opacity)
        self.copy_animation = QPropertyAnimation(self.copy_opacity, b'opacity', self)
        self.copy_animation.setDuration(160)
        self.copy_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.copy_button.installEventFilter(self)
        self.copy_reset_timer = QTimer(self)
        self.copy_reset_timer.setSingleShot(True)
        self.copy_reset_timer.timeout.connect(self.reset_copy)
        self.pending = False
        self.progress_timer = QTimer(self)
        self.progress_timer.setInterval(250)
        self.progress_timer.timeout.connect(self.update_progress)
        self.refresh()

    @staticmethod
    def duration(seconds):
        seconds=max(0,int(seconds))
        return str(seconds // 60)+tr(' dk ')+str(seconds % 60)+tr(' sn') if seconds>=60 else str(seconds)+tr(' sn')

    def begin(self, display_mode='complete'):
        self.running=True
        self.started=time.monotonic()
        self.display_mode=display_mode
        self.activity_details.show()
        self.activity_button.setIcon(icon('chevron-down'))
        self.resume_button.hide()
        self.footer.hide()
        self.set_activity(tr('Hazırlanıyor…'))
        self.progress_timer.start()
        self.refresh()

    @staticmethod
    def bounded_activities(activities):
        if len(activities)<=80:return activities
        opening=next((a for a in activities if a.get('kind')=='message' and (a.get('origin')=='assistant' or str(a.get('key','')).startswith('update-round-'))),None)
        if opening is None:opening=next((a for a in activities if a.get('kind')=='message'),None)
        tail=activities[-79:]
        return [opening,*tail] if opening is not None and opening not in tail else activities[-80:]

    def set_activity(self, text):
        self.stage=text
        waiting=re.sub(r' · \d+ (?:sn|s)(?: ·.*)?$', '',str(text))
        entry={'text':text,'seconds':time.monotonic()-self.started}
        prior=next((a for a in reversed(self.live_activities) if a.get('kind')=='waiting' and a.get('key')==waiting),None) if waiting!=text else None
        if prior:
            prior.update(entry)
        elif not self.live_activities or self.live_activities[-1]['text']!=text:
            if waiting!=text:entry.update(kind='waiting',key=waiting)
            self.live_activities.append(entry)
        self.live_activities=self.bounded_activities(self.live_activities)
        self.activity_details.set_activities(self.live_activities)
        self.activity_details.show()
        self.activity_button.setIcon(icon('chevron-down'))
        self.update_progress()
        self.refresh()

    def add_activity(self,event):
        entry=dict(event)
        entry.setdefault('text',entry.get('title',''))
        entry.setdefault('seconds',time.monotonic()-self.started)
        key=entry.get('key')
        existing=next((i for i,a in enumerate(self.live_activities) if key and a.get('key')==key),None)
        if existing is None:
            self.live_activities.append(entry)
        else:
            self.live_activities[existing]=entry
        self.live_activities=self.bounded_activities(self.live_activities)
        self.activity_details.set_activities(self.live_activities)
        self.activity_details.show()
        self.refresh()

    def update_progress(self):
        if self.running:
            self.activity_button.setText(self.stage+' · '+self.duration(time.monotonic()-self.started))
            self.activity_button.setAccessibleName(self.activity_button.text())

    def apply_metadata(self, metadata):
        self.metadata=metadata or {}
        self.sources_button.setVisible(bool(self.metadata.get('sources')))
        self.running=False
        self.progress_timer.stop()
        state=self.metadata.get('state','complete')
        duration=self.duration(self.metadata.get('seconds',0))
        self.activity_button.setText(duration+{'complete':tr(' çalıştı'),'cancelled':tr(' · durduruldu'),'failed':tr(' · tamamlanamadı'),'limited':tr(' · çalışma sınırına ulaşıldı')}.get(state,tr(' çalıştı')) if self.metadata else tr('Yanıt'))
        activity=self.metadata.get('activities',[])
        self.activity_details.set_activities(activity,state)
        self.activity_details.setVisible(state in {'cancelled','failed','limited'})
        self.activity_button.setIcon(icon('chevron-down' if state in {'cancelled','failed','limited'} else 'chevron-right'))
        self.resume_button.setVisible(state in {'cancelled','limited'})
        error=self.metadata.get('error','')
        self.error_label.setText(tr('Yanıt tamamlanamadı: ')+error if error else (tr('Yanıt durduruldu.') if state=='cancelled' and not self.text else ''))
        self.error_label.setVisible(bool(self.error_label.text()))
        self.shown_text=self.text
        self.buffer=''
        self.footer.show()
        self.copy_button.setEnabled(bool(self.text))
        self.refresh()

    def toggle_activity(self):
        expanded = True if self.running else self.activity_details.isHidden()
        self.activity_details.setVisible(expanded)
        self.activity_button.setIcon(icon('chevron-down' if expanded else 'chevron-right'))
        self.activity_button.setAccessibleDescription(tr('İşlem ayrıntıları açık') if expanded else tr('İşlem ayrıntılarını aç'))
        self.refresh()

    def select_text(self):
        self.view.setFocus()
        self.view.selectAll()

    def set_attachments(self, descriptors, runtime):
        from .image_viewer import attachment_path, AttachmentImage
        row=QHBoxLayout();row.setSpacing(10)
        for descriptor in descriptors[:4]:
            path=attachment_path(runtime,descriptor)
            if path:
                row.addWidget(AttachmentImage(path,descriptor.get('name',tr('Görsel'))))
        row.addStretch()
        self.layout().insertLayout(0,row)
        self.refresh()

    def save_text(self):
        from pathlib import Path
        from PySide6.QtWidgets import QFileDialog
        path,_=QFileDialog.getSaveFileName(self,tr('Yanıtı kaydet'),'yanit.md',tr('Markdown (*.md);;Metin (*.txt)'))
        if path:
            try:
                Path(path).write_text(self.text,encoding='utf-8')
            except OSError:
                self.error_label.setText(tr('Dosya kaydedilemedi. Konumu ve yazma iznini kontrol et.'))
                self.error_label.show()
                self.refresh()

    def open_link(self, url):
        if url.scheme() in {"http", "https"}:
            QDesktopServices.openUrl(url)

    def copy(self):
        from PySide6.QtWidgets import QApplication
        QApplication.clipboard().setText(self.text)
        self.copy_button.setToolTip(tr('Kopyalandı'))
        self.copy_button.setIcon(icon('check','#a6c8ad'))
        self.copy_reset_timer.start(1200)

    def reset_copy(self):
        self.copy_button.setIcon(icon('copy','#a59cac'))
        self.copy_button.setToolTip(tr('Mesajı kopyala'))

    def reveal_copy(self, visible):
        self.copy_animation.stop()
        self.copy_animation.setStartValue(self.copy_opacity.opacity())
        self.copy_animation.setEndValue(1.0 if visible else 0.0)
        self.copy_animation.start()

    def enterEvent(self, event):
        self.reveal_copy(True)
        super().enterEvent(event)

    def leaveEvent(self, event):
        controls = self.findChildren(QPushButton)
        if not any(control.hasFocus() for control in controls):
            self.reveal_copy(False)
        super().leaveEvent(event)

    def eventFilter(self, watched, event):
        if event.type() == QEvent.Type.FocusIn:
            self.reveal_copy(True)
        elif event.type() == QEvent.Type.FocusOut and not self.underMouse():
            self.reveal_copy(False)
        return super().eventFilter(watched, event)

    def append(self, text):
        self.text += text
        previous=self.shown_text
        if not self.running or self.display_mode=='stream':
            self.shown_text=self.text
        elif self.display_mode=='blocks':
            self.buffer+=text
            if len(self.buffer)>=48 or self.buffer.rstrip().endswith(('.', '!', '?', ':', '。')) or '\n' in self.buffer:
                self.shown_text=self.text
                self.buffer=''
        # Complete-mode output stays buffered until apply_metadata. There is
        # no typewriter queue or per-character animation after completion.
        if previous!=self.shown_text and not self.pending:
            self.pending=True
            QTimer.singleShot(60,self.refresh)

    def refresh(self):
        self.pending=False
        if self.role == "user":
            if self.rendered_text != self.text:
                self.view.setPlainText(self.text)
                self.rendered_text = self.text
            available = self.parentWidget().width() if self.parentWidget() else 900
            natural = max((QFontMetricsF(self.view.font()).horizontalAdvance(line) for line in self.text.splitlines()), default=60)
            self.setMaximumWidth(max(100, min(int(available*.82), int(natural)+72)))
        elif self.rendered_text != self.shown_text:
            self.view.setMarkdown(self.shown_text)
            # Qt Markdown doesn't apply CSS paragraph line-height. Format the
            # actual text blocks so lists and long prose have consistent rhythm.
            block = self.view.document().begin()
            while block.isValid():
                cursor = QTextCursor(block)
                fmt = block.blockFormat()
                fmt.setLineHeight(135, QTextBlockFormat.LineHeightTypes.ProportionalHeight.value)
                fmt.setBottomMargin((6 if block.textList() else 9) if block.next().isValid() else 0)
                cursor.setBlockFormat(fmt)
                block = block.next()
            self.rendered_text = self.shown_text
        self.view.setVisible(bool(self.shown_text))
        # Measure against the final bubble width, even before Qt applies the
        # child layout. An old viewport width can clip a freshly wrapped line.
        margins = self.layout().contentsMargins()
        text_width = min(self.width(), self.maximumWidth()) - margins.left() - margins.right()
        self.view.document().setTextWidth(max(30,text_width))
        self.view.setFixedHeight(min(700,max(26,int(self.view.document().size().height())+4)))
        self.view.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded if self.view.height()>=700 else Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setFixedHeight(self.layout().sizeHint().height())
        if self.role=='user':
            self.copy_button.move(self.width()-35,9)
        self.rendered.emit()

    def resizeEvent(self,event):
        super().resizeEvent(event)
        QTimer.singleShot(0,self.refresh)
