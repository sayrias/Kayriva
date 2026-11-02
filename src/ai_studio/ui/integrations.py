"""Embedded, opt-in extension and GitHub interfaces."""
from __future__ import annotations

import os
from ..i18n import tr

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QApplication, QFileDialog, QHBoxLayout, QVBoxLayout
)
from .localized import QWidget, QCheckBox, QLineEdit, QPlainTextEdit, QListWidget, QListWidgetItem, QFormLayout, QSplitter, QTabWidget, QComboBox


from ..extension_library import ExtensionLibrary, requirement
from ..github_service import GitHubService, github_url
from ..integrations import export_configuration, import_configuration
from .icons import icon
from .widgets import InlineDialog, button, label, ChoiceBox
from .localized import QScrollArea, QFrame, FilterTabs


def _surfaces(window):
    preferences = getattr(window, "preferences", None)
    return [preferences.panel] if preferences and preferences.isVisible() else getattr(preferences, "surfaces", [])


def _finish_dialog(dialog, panel):
    dialog.exec()
    if panel.worker is not None and panel.worker.isRunning():
        panel.worker.cancel.set()
        panel.worker.finished.connect(dialog.deleteLater)
    else:
        dialog.deleteLater()


class ExtensionBrowser(QWidget):
    def __init__(self, window):
        super().__init__()
        self.window = window
        self.library = ExtensionLibrary(window.config.root)
        self.worker = None
        self.selected_entry = None
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        intro = label(tr('Araçlarını seç, erişimini incele, tek yerden kur. Kurulum sen seçmeden başlamaz.'), "subtitle")
        layout.addWidget(intro)
        top = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText(tr('Eklenti, yayıncı veya özellik ara…'))
        self.search.setClearButtonEnabled(True)
        self.search.setAccessibleName(tr('Eklenti ara'))
        self.category = ChoiceBox()
        self.category.addItem(tr('Tüm alanlar'), '')
        for category in dict.fromkeys(entry['category'] for entry in self.library.entries):
            self.category.addItem(tr(category), category)
        self.category.setAccessibleName(tr('Eklenti alanı'))
        self.category.setMaximumWidth(190)
        top.addWidget(self.search, 1)
        top.addWidget(self.category)
        layout.addLayout(top)
        filters = QHBoxLayout()
        self.count_label = label('', 'status')
        self.count_label.setWordWrap(False)
        self.type_filter = FilterTabs()
        for title, value in [(tr('Tümü'), ''), (tr('Yerel'), 'local'), (tr('Uzak'), 'remote'), (tr('Eklenenler'), 'installed')]:
            self.type_filter.addItem(title, value)
        self.type_filter.setAccessibleName(tr('Eklenti bağlantı türü'))
        filters.addWidget(self.type_filter)
        filters.addStretch()
        filters.addWidget(self.count_label)
        layout.addLayout(filters)
        split = QSplitter(Qt.Orientation.Horizontal)
        split.setChildrenCollapsible(False)
        self.list = QListWidget()
        self.list.setAccessibleName(tr('Eklenti kütüphanesi'))
        self.list.setMinimumWidth(210)
        self.list.setSpacing(4)
        self.list.setObjectName('extensionList')
        self.list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.list.setTextElideMode(Qt.TextElideMode.ElideRight)
        split.addWidget(self.list)
        self.detail_scroll = QScrollArea()
        self.detail_scroll.setWidgetResizable(True)
        self.detail_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.detail_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.details = QFrame()
        self.details.setObjectName('extensionDetails')
        self.detail_scroll.setWidget(self.details)
        detail = QVBoxLayout(self.details)
        detail.setContentsMargins(18, 16, 18, 16)
        detail.setSpacing(10)
        self.title = label(tr('Bir eklenti seç'), "brand")
        self.publisher = label("", "status")
        self.description = label("")
        self.connection_kind = label('', 'pill')
        self.access = label("", "status")
        self.requirements = label("", "status")
        self.workspace = QLineEdit(window.config.settings.workspace)
        self.workspace.setPlaceholderText(tr('Erişim verilecek proje klasörü'))
        self.workspace.setAccessibleName(tr('Eklentinin proje klasörü'))
        self.workspace_row = QWidget()
        folder_layout = QHBoxLayout(self.workspace_row)
        folder_layout.setContentsMargins(0, 0, 0, 0)
        folder_layout.addWidget(self.workspace, 1)
        folder_layout.addWidget(button(tr('Seç'), self.choose_folder, icon_name="folder"))
        self.enable = QCheckBox(tr('Kurulumdan sonra etkinleştir'))
        self.enable.setToolTip(tr('Etkin sunucular sohbette araç çağrıları için çalıştırılabilir.'))
        self.command = QPlainTextEdit()
        self.command.setReadOnly(True)
        self.command.setMaximumHeight(78)
        self.command.setAccessibleName(tr('Kurulum kaynağı'))
        for field in (self.connection_kind, self.title, self.publisher, self.description):
            detail.addWidget(field, alignment=Qt.AlignmentFlag.AlignLeft) if field is self.connection_kind else detail.addWidget(field)
        detail.addSpacing(8)
        detail.addWidget(label(tr('Erişim ve kapsam'), 'subtitle'))
        detail.addWidget(self.access)
        detail.addWidget(label(tr('Gereksinimler'), 'subtitle'))
        detail.addWidget(self.requirements)
        for field in (self.workspace_row, self.command, self.enable):
            detail.addWidget(field)
        detail.addStretch()
        actions = QHBoxLayout()
        self.source = button(tr('Resmî kaynak'), self.open_source, icon_name="globe")
        self.source.setObjectName("ghost")
        self.install_button = button(tr('Kur ve ekle'), self.install, True, "download")
        actions.addWidget(self.source)
        actions.addStretch()
        actions.addWidget(self.install_button)
        self.detail_panel = QWidget()
        right = QVBoxLayout(self.detail_panel)
        right.setContentsMargins(0, 0, 0, 0)
        right.setSpacing(10)
        right.addWidget(self.detail_scroll, 1)
        right.addLayout(actions)
        split.addWidget(self.detail_panel)
        split.setSizes([280, 470])
        layout.addWidget(split, 1)
        self.status = label("", "status")
        layout.addWidget(self.status)
        bottom = QHBoxLayout()
        bottom.addWidget(button(tr('JSON yapıştır'), self.import_json, icon_name="file"))
        bottom.addWidget(button(tr('Bağlantıları kopyala'), self.copy_json, icon_name="copy"))
        bottom.addStretch()
        self.cancel_button = button(tr('Kurulumu durdur'), self.cancel, icon_name="stop")
        self.cancel_button.hide()
        bottom.addWidget(self.cancel_button)
        layout.addLayout(bottom)
        note = label(tr("Bu kütüphanede bağımsız MCP sunucuları bulunur. Her aracın kapsamı, erişim gereksinimleri ve kurulum koşulları açıklamasında yazılıdır."), "status")
        layout.addWidget(note)
        self.search.textChanged.connect(self.refresh)
        self.category.currentIndexChanged.connect(self.refresh)
        self.type_filter.currentChanged.connect(self.refresh)
        self.list.currentItemChanged.connect(self.select)
        self.refresh()

    def refresh(self):
        selected_id = self.selected_entry['id'] if self.selected_entry else None
        self.list.blockSignals(True)
        self.list.clear()
        query = self.search.text().casefold().strip()
        category = self.category.currentData()
        installed = {spec.get("library_id") for spec in self.window.config.settings.mcp_servers}
        selected_row = 0
        kind = self.type_filter.currentData()
        for entry in sorted(self.library.entries, key=lambda entry: entry['name'].casefold()):
            if kind == 'installed' and entry['id'] not in installed:
                continue
            if kind == 'remote' and entry['kind'] != 'http' or kind == 'local' and entry['kind'] == 'http':
                continue
            if category and entry["category"] != category:
                continue
            if query and query not in " ".join(tr(str(entry.get(k, ""))) for k in ("name", "publisher", "description", "category")).casefold():
                continue
            item = QListWidgetItem(entry["name"] + "\n" + (tr('Eklendi · ') if entry["id"] in installed else "") + tr(entry['category']))
            item.setToolTip(entry['name'] + '\n' + tr(entry['description']))
            item.setData(Qt.ItemDataRole.UserRole, entry)
            glyph = {'Dosyalar': 'folder', 'Belgeler': 'file', 'Araştırma': 'globe', 'Bellek ve plan': 'book', 'Geliştirme': 'code', 'Yardımcılar': 'clock', 'Dokümantasyon': 'book'}.get(entry['category'], 'tools')
            item.setIcon(icon(glyph))
            self.list.addItem(item)
            if entry['id'] == selected_id:
                selected_row = self.list.count()-1
        self.list.blockSignals(False)
        self.count_label.setText(tr('{visible} / {total} eklenti · {installed} eklendi', visible=self.list.count(), total=len(self.library.entries), installed=len(installed & {e['id'] for e in self.library.entries})))
        self.detail_panel.setVisible(bool(self.list.count()))
        if self.list.count():
            self.list.setCurrentRow(selected_row)
            self.select(self.list.currentItem())
        else:
            self.selected_entry = None
            self.status.setText(tr('Eşleşen eklenti bulunamadı. Aramanı veya alan filtresini değiştir.'))

    def select(self, item, previous=None):
        if not item:
            self.selected_entry = None
            return
        entry = self.selected_entry = item.data(Qt.ItemDataRole.UserRole)
        self.connection_kind.setText(tr('Uzak MCP · HTTPS') if entry['kind'] == 'http' else tr('Yerel MCP · Node.js') if entry['kind'] == 'npm' else tr('Yerel MCP · Python'))
        self.title.setText(entry["name"])
        self.publisher.setText(entry["publisher"] + " · " + tr(entry["category"]))
        self.description.setText(tr(entry["description"]))
        self.access.setText(tr(entry["permissions"]))
        required = requirement(entry)
        prefix = 'Ortam değişkeni gerekli: '
        self.requirements.setText(tr(prefix) + required[len(prefix):] if required.startswith(prefix) else tr(required))
        self.workspace_row.setVisible(bool(entry.get("workspace")))
        self.command.setPlainText(entry.get("package") or entry.get("url", ""))
        already = any(spec.get("library_id") == entry["id"] for spec in self.window.config.settings.mcp_servers)
        self.install_button.setText(tr('Bağlantı eklendi') if already else tr('Bağlantıyı ekle') if entry["kind"] == "http" else tr('Kur ve ekle'))
        self.install_button.setEnabled(not already and not (self.worker and self.worker.isRunning()))
        self.status.setText("" if not already else tr('Bu eklenti Bağlantılar sayfasında. Oradan test edebilir, düzenleyebilir veya kaldırabilirsin.'))

    def choose_folder(self):
        path = QFileDialog.getExistingDirectory(self, tr('Proje klasörü'), self.workspace.text())
        if path:
            self.workspace.setText(path)

    def open_source(self):
        if self.selected_entry:
            QDesktopServices.openUrl(QUrl(self.selected_entry["source"]))

    def install(self):
        entry = self.selected_entry
        if not entry or self.worker and self.worker.isRunning():
            return
        if self.window.config.settings.offline and entry["kind"] != "http":
            self.status.setText(tr('Kurulum için internet gerekli. Genel ayarlardan çevrimdışı modu kapat.'))
            return
        ident, workspace, enabled = entry["id"], self.workspace.text().strip(), self.enable.isChecked()
        if enabled and any(not os.environ.get(name) for name in [*entry.get('header_env', {}).values(), *entry.get('required_env', [])]):
            self.status.setText(tr('Önce gerekli ortam değişkenini tanımla veya etkinleştirmeden ekle.'))
            return
        self.install_button.setEnabled(False)
        self.cancel_button.show()
        self.status.setText(tr('Kurulum hazırlanıyor…'))
        def action(worker):
            try:
                return self.library.install(ident, workspace, cancel=worker.cancel, status=worker.status.emit)
            except InterruptedError:
                return None
        def complete(spec):
            if spec is None:
                self.cancel_button.hide()
                self.refresh()
                self.status.setText(tr('Kurulum durduruldu. İstediğinde yeniden deneyebilirsin.'))
                return
            spec["enabled"] = enabled
            servers = self.window.config.settings.mcp_servers
            if not any(s.get("library_id") == ident for s in servers):
                servers.append(spec)
                self.window.config.save()
                self.window.refresh_mcp()
            self.cancel_button.hide()
            self.refresh()
            self.status.setText(tr('Bağlantı eklendi. ') + (tr('Sohbette kullanılabilir.') if enabled else tr('Bağlantılar sayfasında test edip etkinleştirebilirsin.')))
        self.worker = self.window.run_task(action, complete, self.status.setText)
        def failed(message):
            self.status.setText(message)
            self.cancel_button.hide()
            self.install_button.setEnabled(True)
        self.worker.failed.connect(failed)

    def cancel(self):
        if self.worker:
            self.worker.cancel.set()
            self.status.setText(tr('Kurulum durduruluyor…'))

    def copy_json(self):
        QApplication.clipboard().setText(export_configuration(self.window.config.settings.mcp_servers))
        self.status.setText(tr('Bağlantılar kopyalandı. Satır içi anahtarlar ve kimlik bilgisi başlıkları dışarı aktarılmadı.'))

    def import_json(self):
        parent = self.window.centralWidget()
        dialog = InlineDialog(parent, tr('MCP yapılandırmasını yapıştır'), 640, 420, [self.parentWidget()])
        editor = QPlainTextEdit()
        editor.setPlaceholderText('{"mcpServers": {"sunucu": {"command": "…", "args": []}}}')
        dialog.body.addWidget(editor, 1)
        hint = label(tr('İçe aktarma program çalıştırmaz. Bağlantılar kapalı olarak eklenir.'), "status")
        dialog.body.addWidget(hint)
        def save():
            try:
                servers = import_configuration(editor.toPlainText())
                self.window.config.settings.mcp_servers.extend(servers)
                self.window.config.save()
                self.window.refresh_mcp()
                self.refresh()
                self.status.setText(f"{len(servers)}{tr(' bağlantı kapalı olarak eklendi.')}")
                dialog.accept()
            except ValueError as exc:
                hint.setText(str(exc))
        dialog.body.addWidget(button(tr('İçe aktar'), save, True), alignment=Qt.AlignmentFlag.AlignRight)
        dialog.exec()
        dialog.deleteLater()


class GitHubPanel(QWidget):
    def __init__(self, window, project_path=None):
        super().__init__()
        self.window = window
        self.service = GitHubService()
        self.worker = None
        self.preview = None
        self.account_ready = False
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.status = label(tr('Hesap durumunu kontrol et. GitHub CLI oturumu kullanılır; erişim anahtarın burada saklanmaz.'), "subtitle")
        layout.addWidget(self.status)
        head = QHBoxLayout()
        self.refresh_button = button(tr('Hesabı ve depoları yenile'), self.refresh, icon_name="refresh")
        head.addWidget(self.refresh_button)
        login = button(tr('Oturum açma komutunu kopyala'), self.copy_login, icon_name="copy")
        login.setObjectName("ghost")
        head.addWidget(login)
        head.addStretch()
        layout.addLayout(head)
        self.tabs = QTabWidget()
        repositories = QWidget()
        repo_layout = QVBoxLayout(repositories)
        repo_layout.setContentsMargins(0, 12, 0, 0)
        self.repo_search = QLineEdit()
        self.repo_search.setPlaceholderText(tr('Depolarında ara…'))
        self.repo_search.setClearButtonEnabled(True)
        self.repo_search.textChanged.connect(self.filter_repositories)
        repo_layout.addWidget(self.repo_search)
        self.repos = QListWidget()
        self.repos.setAccessibleName(tr('GitHub depoları'))
        self.repos.itemDoubleClicked.connect(self.open_repo)
        repo_layout.addWidget(self.repos, 1)
        repo_layout.addWidget(button(tr("GitHub'da aç"), self.open_repo, icon_name="globe"), alignment=Qt.AlignmentFlag.AlignRight)
        self.tabs.addTab(repositories, tr('Depolarım'))
        publish = QWidget()
        publish_layout = QVBoxLayout(publish)
        publish_layout.setContentsMargins(0, 12, 0, 0)
        publish_layout.setSpacing(10)
        form = QFormLayout()
        self.name = QLineEdit()
        self.name.setPlaceholderText(tr('sahip/proje-adi veya proje-adi'))
        self.description = QLineEdit()
        self.description.setPlaceholderText(tr('Kısa açıklama · isteğe bağlı'))
        self.private = QCheckBox(tr('Özel depo'))
        self.private.setChecked(True)
        self.private.setToolTip(tr('Yalnızca sen ve erişim verdiğin kişiler görebilir.'))
        self.mode = QComboBox()
        self.mode.addItems([tr('Proje kaynaklarını yükle'), tr('Yalnızca boş depo oluştur')])
        form.addRow(tr('İşlem'), self.mode)
        form.addRow(tr('Depo adı'), self.name)
        form.addRow(tr('Açıklama'), self.description)
        form.addRow(tr('Görünürlük'), self.private)
        publish_layout.addLayout(form)
        folder = QHBoxLayout()
        self.path = QLineEdit(project_path or window.config.settings.workspace)
        self.path.setPlaceholderText(tr('Yüklenecek proje klasörü'))
        self.path.setAccessibleName(tr('GitHub proje klasörü'))
        self.path.textChanged.connect(self.invalidate)
        folder.addWidget(self.path, 1)
        folder.addWidget(button(tr('Klasör seç'), self.choose_folder, icon_name="folder"))
        self.preview_button = button(tr('Dosyaları incele'), self.make_preview, icon_name="file")
        folder.addWidget(self.preview_button)
        publish_layout.addLayout(folder)
        self.files = QListWidget()
        self.files.setAccessibleName(tr("GitHub'a yüklenecek dosyalar"))
        self.files.itemChanged.connect(self.change_publish_details)
        publish_layout.addWidget(self.files, 1)
        self.summary = label(tr('Yeni depo seçilen dosyaların bir kopyasından oluşur. Kaynak projenin Git geçmişi ve uzak bağlantıları değişmez.'), "status")
        publish_layout.addWidget(self.summary)
        self.confirm = QCheckBox(tr("Görünürlüğü ve seçilen dosyaları inceledim; GitHub'a gönder"))
        self.confirm.toggled.connect(self.update_publish)
        publish_layout.addWidget(self.confirm)
        self.publish_button = button(tr('Depo oluştur ve yükle'), self.publish, True, "send")
        self.publish_button.setEnabled(False)
        publish_layout.addWidget(self.publish_button, alignment=Qt.AlignmentFlag.AlignRight)
        self.mode.currentIndexChanged.connect(self.change_mode)
        self.name.textChanged.connect(self.change_publish_details)
        self.description.textChanged.connect(self.change_publish_details)
        self.private.toggled.connect(self.change_publish_details)
        self.tabs.addTab(publish, tr('Yeni depo / Yükle'))
        layout.addWidget(self.tabs, 1)
        self.result = label("", "status")
        layout.addWidget(self.result)

    def set_busy(self, busy):
        self.refresh_button.setEnabled(not busy)
        self.preview_button.setEnabled(not busy)
        self.tabs.setEnabled(not busy)

    def task(self, fn, done):
        if self.worker and self.worker.isRunning():
            return
        self.set_busy(True)
        def complete(result):
            self.set_busy(False)
            done(result)
        self.worker = self.window.run_task(fn, complete, self.result.setText)
        def failed(message):
            self.set_busy(False)
            self.result.setText(message)
        self.worker.failed.connect(failed)

    def copy_login(self):
        QApplication.clipboard().setText("gh auth login --hostname github.com --web --git-protocol https")
        self.result.setText(tr('Komut kopyalandı. Terminalde çalıştır, tarayıcıda oturum aç; sonra burada hesabını yenile. GitHub CLI kurulumu: cli.github.com'))

    def refresh(self):
        if self.window.config.settings.offline:
            self.result.setText(tr('GitHub için internet gerekli. Genel ayarlardan çevrimdışı modu kapat.'))
            return
        self.result.setText(tr('GitHub hesabı kontrol ediliyor…'))
        def action(worker):
            account = self.service.account()
            return account, self.service.repositories() if account["authenticated"] else []
        def complete(value):
            account, repositories = value
            self.account_ready = account["authenticated"]
            self.status.setText(tr('Bağlı hesap: ') + account["login"] if account["authenticated"] else
                                tr('GitHub CLI bulunamadı · cli.github.com üzerinden kur.') if not account["installed"] else
                                tr('GitHub oturumu kapalı. Oturum açma komutunu kopyalayıp terminalde çalıştır.'))
            self.repos.clear()
            for repo in repositories:
                item = QListWidgetItem(repo["nameWithOwner"] + (tr(' · Özel') if repo["isPrivate"] else tr(' · Herkese açık')) + "\n" + (repo.get("description") or tr('Açıklama yok')))
                item.setData(Qt.ItemDataRole.UserRole, repo["url"])
                item.setIcon(icon("code"))
                self.repos.addItem(item)
            self.result.setText(f"{len(repositories)}{tr(' depo gösteriliyor.')}" if repositories else tr('Gösterilecek depo yok.'))
            self.update_publish()
        self.task(action, complete)

    def filter_repositories(self):
        query = self.repo_search.text().casefold()
        for n in range(self.repos.count()):
            item = self.repos.item(n)
            item.setHidden(query not in item.text().casefold())

    def open_repo(self, item=None):
        if not isinstance(item, QListWidgetItem):
            item = self.repos.currentItem()
        if item:
            QDesktopServices.openUrl(QUrl(github_url(item.data(Qt.ItemDataRole.UserRole))))

    def choose_folder(self):
        folder = QFileDialog.getExistingDirectory(self, tr('Yüklenecek proje'), self.path.text())
        if folder:
            self.path.setText(folder)

    def invalidate(self):
        self.preview = None
        self.files.clear()
        self.confirm.setChecked(False)
        self.update_publish()

    def change_mode(self):
        empty = self.mode.currentIndex() == 1
        for control in (self.path, self.preview_button, self.files):
            control.setEnabled(not empty)
        self.publish_button.setText(tr('Boş depo oluştur') if empty else tr('Depo oluştur ve yükle'))
        self.confirm.setChecked(False)
        self.update_publish()

    def make_preview(self):
        workspace = self.path.text().strip()
        self.result.setText(tr('.gitignore, boyut ve kimlik bilgileri kontrol ediliyor…'))
        def complete(preview):
            self.preview = preview
            self.files.clear()
            for name, size, _ in preview.files:
                item = QListWidgetItem(f"{name}  ·  {size / 1000:.1f} kB")
                item.setData(Qt.ItemDataRole.UserRole, name)
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                item.setCheckState(Qt.CheckState.Checked)
                self.files.addItem(item)
            self.summary.setText(f"{len(preview.files)}{tr(' dosya · ')}{preview.total_bytes / 1000000:.2f} MB · {len(preview.excluded)}{tr(' dosya dışarıda. .gitignore kuralları uygulanır; çalışma verileri, anahtarlar ve model dosyaları ayrıca hariç tutulur.')}")
            self.summary.setToolTip("\n".join(name + ": " + reason for name, reason in preview.excluded[:50]))
            if not self.name.text().strip():
                self.name.setText(preview.root.name.replace(" ", "-"))
            self.confirm.setChecked(False)
            self.update_publish()
            self.result.setText(tr('Dosyaları ve görünürlüğü incele; istemediğin dosyaların seçimini kaldır.'))
        self.task(lambda _: self.service.preview(workspace), complete)

    def update_publish(self):
        selected = any(self.files.item(n).checkState() == Qt.CheckState.Checked for n in range(self.files.count()))
        self.publish_button.setEnabled(self.account_ready and bool(self.name.text().strip()) and self.confirm.isChecked()
                                       and (self.mode.currentIndex() == 1 or self.preview is not None and selected))

    def change_publish_details(self):
        self.confirm.setChecked(False)
        self.update_publish()

    def publish(self):
        if self.window.config.settings.offline:
            self.result.setText(tr('GitHub için internet gerekli. Genel ayarlardan çevrimdışı modu kapat.'))
            return
        if not self.confirm.isChecked() or not self.account_ready:
            return
        name, description, private = self.name.text(), self.description.text(), self.private.isChecked()
        empty = self.mode.currentIndex() == 1
        selected = [self.files.item(n).data(Qt.ItemDataRole.UserRole) for n in range(self.files.count()) if self.files.item(n).checkState() == Qt.CheckState.Checked]
        preview = self.preview
        if not empty and preview is None:
            return
        self.result.setText(tr('GitHub işlemi başlıyor…'))
        def action(worker):
            if empty:
                return self.service.create(name, description, private)
            return self.service.publish(preview, name, description, private, selected=selected, status=worker.status.emit)
        def complete(url):
            self.confirm.setChecked(False)
            self.result.setText(tr('Depo hazır: ') + url)
            QApplication.clipboard().setText(url)
            self.status.setText(tr('Depo adresi kopyalandı. Depolarım sekmesinden listeyi yenileyip açabilirsin.'))
        self.task(action, complete)


def show_extension_library(window):
    dialog = InlineDialog(window.centralWidget(), tr('Eklenti kütüphanesi'), 900, 650, _surfaces(window))
    try:
        panel = ExtensionBrowser(window)
    except Exception as exc:
        dialog.deleteLater()
        window.error(str(exc))
        return
    dialog.body.addWidget(panel, 1)
    _finish_dialog(dialog, panel)


def show_github_dialog(window, project_path=None):
    dialog = InlineDialog(window.centralWidget(), "GitHub", 820, 650, _surfaces(window))
    panel = GitHubPanel(window, project_path)
    dialog.body.addWidget(panel, 1)
    _finish_dialog(dialog, panel)
