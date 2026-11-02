"""Native, non-blocking release updates. Downloading never forces a restart."""
from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout
)
from .localized import QWidget, QFrame, QCheckBox, QTextBrowser, QScrollArea, QProgressBar, QFormLayout


from .. import __version__
from ..brand import APP_NAME
from ..i18n import tr
from ..local_logging import failure
from ..updater import UpdateSource, check_for_updates, download_update, launch_update, host_target
from .widgets import label, button, card
from .workers import TaskWorker


class AboutPage(QWidget):
    def __init__(self, window):
        super().__init__()
        self.window = window
        self.release = None
        self.staged = None
        self.worker = None
        self.packaged = bool(getattr(sys, 'frozen', False))
        self.check_count = 0
        self.automatic_pending = False
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        content = QWidget()
        self.scroll.setWidget(content)
        outer.addWidget(self.scroll)
        layout = QVBoxLayout(content)
        layout.setContentsMargins(22, 18, 22, 18)
        layout.setSpacing(14)
        layout.addWidget(label(tr('Hakkında ve güncellemeler'), 'title'))
        layout.addWidget(label(tr('Yerel modeller için kişisel çalışma alanın.'), 'subtitle'))
        info, contents = card()
        heading = QHBoxLayout()
        heading.addWidget(label(APP_NAME, 'brand'))
        heading.addStretch()
        heading.addWidget(label(__version__, 'pill'))
        contents.addLayout(heading)
        details = QFormLayout()
        details.setHorizontalSpacing(24)
        details.setVerticalSpacing(9)
        details.addRow(tr('Sürüm'), label(__version__))
        details.addRow(tr('Platform'), label(' · '.join(host_target()) + ('' if self.packaged else ' · ' + tr('Kaynak koddan çalışıyor'))))
        self.source = label(window.config.settings.update_repository, 'subtitle')
        self.source.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        details.addRow(tr('Güncelleme kaynağı'), self.source)
        contents.addLayout(details)
        layout.addWidget(info)
        self.check_startup = QCheckBox(tr('Açılışta güncellemeleri denetle'))
        self.check_startup.setChecked(window.config.settings.check_updates_on_startup)
        self.check_startup.toggled.connect(self.save_preferences)
        layout.addWidget(self.check_startup)
        self.automatic = QCheckBox(tr('Güncellemeleri otomatik indir'))
        self.automatic.setChecked(window.config.settings.auto_install_updates)
        self.automatic.setEnabled(self.packaged)
        self.automatic.toggled.connect(self.save_preferences)
        layout.addWidget(self.automatic)
        layout.addWidget(label(tr('Doğrulanan güncellemeler hazırlanır. Yeniden başlatmayı sen seçersin; çalışan görevler veya taslaklar kesilmez.'), 'subtitle'))
        if not self.packaged:
            layout.addWidget(label(tr('Kaynak koddan çalışırken otomatik denetim ve kurulum kapalıdır. Paketlenmiş uygulamada etkinleşir.'), 'status'))
        actions = QHBoxLayout()
        self.check_button = button(tr('Güncellemeleri denetle'), self.check, icon_name='refresh')
        self.check_button.setObjectName('checkUpdates')
        actions.addWidget(self.check_button)
        self.apply_button = button(tr('Güncellemeyi indir'), self.download_or_apply, True, 'download')
        self.apply_button.setObjectName('applyUpdate')
        self.apply_button.hide()
        actions.addWidget(self.apply_button)
        self.cancel_button = button(tr('İndirmeyi iptal et'), self.cancel, icon_name='stop')
        self.cancel_button.hide()
        actions.addWidget(self.cancel_button)
        actions.addStretch()
        layout.addLayout(actions)
        self.status = label(tr('Henüz denetlenmedi'), 'subtitle')
        self.status.setObjectName('updateStatus')
        layout.addWidget(self.status)
        self.progress = QProgressBar()
        self.progress.setAccessibleName(tr('Güncelleme indiriliyor ve doğrulanıyor…'))
        self.progress.hide()
        layout.addWidget(self.progress)
        self.notes = QTextBrowser()
        self.notes.setAccessibleName(tr('Sürüm notları'))
        self.notes.setMaximumHeight(170)
        self.notes.hide()
        layout.addWidget(self.notes)
        self.release_button = button(tr('Sürümü GitHub’da aç'), self.open_release, icon_name='globe')
        self.release_button.setObjectName('ghost')
        self.release_button.hide()
        layout.addWidget(self.release_button, alignment=Qt.AlignmentFlag.AlignLeft)
        layout.addStretch()
        layout.addWidget(label(tr('Güncelleme denetimi GitHub sürümlerini kullanır. Sohbet veya proje dosyaları gönderilmez.'), 'status'))

    def save_preferences(self):
        settings = self.window.config.settings
        settings.check_updates_on_startup = self.check_startup.isChecked()
        settings.auto_install_updates = self.automatic.isChecked()
        self.window.config.save()

    def busy(self):
        return bool(self.worker and self.worker.isRunning())

    def startup_check(self):
        if self.packaged and self.window.config.settings.check_updates_on_startup and not self.window.config.settings.offline and not self.window.closing:
            self.check()

    def check(self):
        if self.busy() or self.window.closing:
            return
        if self.window.config.settings.offline:
            self.status.setText(tr('Güncelleme denetimi çevrimdışı modda kapalı.'))
            return
        self.check_count += 1
        self.status.setText(tr('Güncellemeler denetleniyor…'))
        self.check_button.setEnabled(False)
        repository = self.window.config.settings.update_repository
        self._start(lambda worker: check_for_updates(UpdateSource(repository), __version__, cancel=worker.cancel), self.checked)

    def _start(self, action, completed):
        worker = TaskWorker(action)
        self.worker = worker
        self.window.background.append(worker)
        worker.progress.connect(self.show_progress)
        worker.completed.connect(completed)
        worker.failed.connect(self.failed)
        worker.finished.connect(lambda: self.window.background.remove(worker) if worker in self.window.background else None)
        worker.finished.connect(lambda: self.finished(worker))
        worker.start()

    def finished(self, worker):
        # A completed check may schedule an automatic download on the next tick.
        if self.worker is worker:
            self.check_button.setEnabled(True)
            self.cancel_button.hide()
            if self.automatic_pending:
                self.automatic_pending = False
                from PySide6.QtCore import QTimer
                QTimer.singleShot(0, self.download_or_apply)

    def checked(self, release):
        previous = self.release
        self.release = release
        if release is None:
            self.staged = None
            self.status.setText(tr('Güncel sürümü kullanıyorsun.'))
            self.apply_button.hide()
            self.release_button.hide()
            self.notes.hide()
            self.progress.hide()
            return
        if previous is None or (previous.version, previous.sha256) != (release.version, release.sha256):
            self.staged = None
            self.apply_button.setText(tr('Güncellemeyi indir'))
            self.progress.hide()
        self.status.setText(tr('Yeni sürüm hazır: ') + release.version)
        self.notes.setPlainText(release.notes)
        self.notes.setVisible(bool(release.notes))
        self.release_button.show()
        self.apply_button.setVisible(self.packaged)
        if not self.packaged:
            self.status.setText(self.status.text() + '\n' + tr('Yeni sürüm kaynak koddan otomatik kurulmaz. Sürüm sayfasından paketini indirebilirsin.'))
        elif self.window.config.settings.auto_install_updates:
            # A completed signal can arrive before QThread.isRunning() becomes
            # false. Start the download from finished(), never lose the intent.
            if not self.staged:
                self.automatic_pending = True

    def download_or_apply(self):
        if self.busy() or self.window.closing or not self.release or not self.packaged:
            return
        if self.staged:
            self.apply()
            return
        if self.window.config.settings.offline:
            self.status.setText(tr('Güncelleme denetimi çevrimdışı modda kapalı.'))
            return
        self.status.setText(tr('Güncelleme indiriliyor ve doğrulanıyor…'))
        self.apply_button.setEnabled(False)
        self.check_button.setEnabled(False)
        self.progress.setRange(0, 0)
        self.progress.show()
        self.cancel_button.show()
        release = self.release
        destination = self.window.config.runtime / 'updates'
        self._start(lambda worker: download_update(release, destination,
            progress=lambda done, total: worker.progress.emit(done, total), cancel=worker.cancel,
            base_path=Path(sys.executable), current_version=__version__), self.downloaded)

    def show_progress(self, done, total):
        self.progress.setRange(0, 100 if total else 0)
        if total:
            self.progress.setValue(min(100, int(done * 100 / total)))

    def downloaded(self, path):
        self.staged = Path(path)
        self.progress.setRange(0, 100)
        self.progress.setValue(100)
        self.status.setText(tr('Güncelleme hazır · yeniden başlatınca uygulanır'))
        self.apply_button.setText(tr('Güncellemek için yeniden başlat'))
        self.apply_button.setEnabled(True)
        self.window.status_label.setText(tr('Güncelleme hazır · yeniden başlatınca uygulanır'))

    def apply(self):
        if self.window.is_busy() or any(w.isRunning() for w in self.window.background) or (
                self.window.download_worker and self.window.download_worker.isRunning()):
            self.status.setText(tr('Önce çalışan görevini tamamla veya durdur. Güncelleme hazır bekliyor.'))
            return
        if self.window.input.toPlainText().strip() or self.window.attachments:
            self.status.setText(tr('Yeniden başlatmadan önce mesaj taslağını gönder veya temizle. Güncelleme hazır bekliyor.'))
            return
        if self.window.edit_path and self.window.editor.toPlainText() != self.window.edit_original:
            self.status.setText(tr('Dosyayı kaydet veya değişiklikleri geri al; ardından yeniden başlatabilirsin.'))
            return
        try:
            result = launch_update(self.release, self.staged)
        except Exception as exc:
            self.failed(str(exc))
            return
        self.status.setText(tr(result.message))
        if result.requires_exit:
            self.window.close()

    def failed(self, message):
        self.status.setText(tr(message))
        self.apply_button.setEnabled(True)
        self.progress.hide()

    def cancel(self):
        if self.busy():
            self.worker.cancel.set()
            self.status.setText(tr('Güncelleme indirmesi iptal edildi.'))

    def open_release(self):
        if self.release and not self.window.config.settings.offline:
            QDesktopServices.openUrl(QUrl(self.release.page_url))
