"""Embedded, opt-in extension and GitHub interfaces."""
from __future__ import annotations

import os
import copy
from pathlib import Path
from ..i18n import tr

from PySide6.QtCore import Qt, QUrl, QSize
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QApplication, QFileDialog, QHBoxLayout, QVBoxLayout
)
from .localized import QWidget, QCheckBox, QLineEdit, QPlainTextEdit, QListWidget, QListWidgetItem, QFormLayout, QSplitter, QTabWidget, QComboBox


from ..extension_library import ExtensionLibrary, requirement, authentication_issue
from ..github_service import GitHubService, github_url
from ..integrations import export_configuration, import_configuration
from .icons import icon
from .file_dialogs import QFileDialog
from .widgets import InlineDialog, button, label, ChoiceBox
from .localized import QScrollArea, QFrame, FilterTabs, QLabel, QProgressBar


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


def _auth_message(entry):
    issue = authentication_issue(entry)
    prefix = 'Ortam değişkeni gerekli: '
    if issue.startswith(prefix):
        return tr(prefix) + issue[len(prefix):]
    if issue:
        return tr('{variable} değeri {prefix} önekiyle tanımlanmalı.',
                  variable=entry.get('header_env', {}).get('Authorization', ''), prefix=entry.get('auth_prefix', 'Bearer'))
    return ''


class ExtensionBrowser(QWidget):
    def __init__(self, window, apps_only=False):
        super().__init__()
        self.window = window
        self.library = ExtensionLibrary(window.config.root)
        self.apps_only = apps_only
        self.worker = None
        self.selected_entry = None
        self._selecting = False
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        intro = label(tr('Uygulamalara kendi MCP bağlantılarınla eriş. Hesap erişimi ve izinler ilgili sağlayıcıdan yönetilir.') if apps_only else tr('Araçlarını seç, erişimini incele, tek yerden kur. Kurulum sen seçmeden başlamaz.'), "subtitle")
        layout.addWidget(intro)
        top = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText(tr('Eklenti, yayıncı veya özellik ara…'))
        self.search.setClearButtonEnabled(True)
        self.search.setAccessibleName(tr('Eklenti ara'))
        self.category = ChoiceBox()
        self.category.addItem(tr('Tüm alanlar'), '')
        for category in dict.fromkeys(entry['category'] for entry in self.library.entries if not apps_only or entry.get('app')):
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
        self.list.setIconSize(QSize(24, 24))
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
        self.detail_icon = QLabel()
        self.detail_icon.setFixedSize(38, 38)
        title_row = QHBoxLayout()
        title_row.setSpacing(12)
        title_row.addWidget(self.detail_icon)
        title_column = QVBoxLayout()
        title_column.setSpacing(3)
        title_column.addWidget(self.title)
        title_column.addWidget(self.publisher)
        title_row.addLayout(title_column, 1)
        detail.addLayout(title_row)
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
        self.command.setFixedHeight(54)
        self.command.setAccessibleName(tr('Kurulum kaynağı'))
        for field in (self.connection_kind, self.description):
            detail.addWidget(field, alignment=Qt.AlignmentFlag.AlignLeft) if field is self.connection_kind else detail.addWidget(field)
        detail.addSpacing(8)
        detail.addWidget(label(tr('Erişim ve kapsam'), 'subtitle'))
        detail.addWidget(self.access)
        detail.addWidget(label(tr('Gereksinimler'), 'subtitle'))
        detail.addWidget(self.requirements)
        for field in (self.workspace_row, self.command):
            detail.addWidget(field)
        detail.addStretch()
        actions = QHBoxLayout()
        self.source = button(tr('Resmî kaynak'), self.open_source, icon_name="globe")
        self.source.setObjectName("ghost")
        self.install_button = button(tr('Kur ve ekle'), self.install, True, "download")
        self.test_button = button(tr('Bağlantıyı test et'), self.test_connection, icon_name='play')
        self.test_button.hide()
        actions.addWidget(self.source)
        actions.addStretch()
        actions.addWidget(self.install_button)
        self.detail_panel = QWidget()
        right = QVBoxLayout(self.detail_panel)
        right.setContentsMargins(0, 0, 0, 0)
        right.setSpacing(10)
        right.addWidget(self.detail_scroll, 1)
        self.install_footer = QWidget()
        footer = QVBoxLayout(self.install_footer)
        footer.setContentsMargins(18, 16, 18, 12)
        footer.setSpacing(12)
        enabled_row = QHBoxLayout()
        enabled_row.setSpacing(12)
        enabled_row.addWidget(self.enable)
        enabled_row.addStretch()
        enabled_row.addWidget(self.test_button)
        footer.addLayout(enabled_row)
        footer.addLayout(actions)
        right.addWidget(self.install_footer)
        split.addWidget(self.detail_panel)
        split.setSizes([280, 470])
        layout.addWidget(split, 1)
        self.status = label("", "status")
        layout.addWidget(self.status)
        self.install_progress = QProgressBar()
        self.install_progress.setRange(0, 0)
        self.install_progress.setFixedHeight(4)
        self.install_progress.setTextVisible(False)
        self.install_progress.hide()
        layout.addWidget(self.install_progress)
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
        self.enable.toggled.connect(self.toggle_enabled)
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
            if self.apps_only and not entry.get('app'):
                continue
            if kind == 'installed' and entry['id'] not in installed:
                continue
            remote = entry['kind'] == 'http' and not entry.get('local_http')
            if kind == 'remote' and not remote or kind == 'local' and remote:
                continue
            if category and entry["category"] != category:
                continue
            if query and query not in " ".join(tr(str(entry.get(k, ""))) for k in ("name", "publisher", "description", "category")).casefold():
                continue
            state = next((spec for spec in self.window.config.settings.mcp_servers if spec.get('library_id') == entry['id']), None)
            suffix = tr('Etkin') if state and state.get('enabled') else tr('Kapalı') if state else tr(entry['category'])
            item = QListWidgetItem(entry["name"] + "\n" + suffix)
            item.setToolTip(entry['name'] + '\n' + tr(entry['description']))
            item.setData(Qt.ItemDataRole.UserRole, entry)
            item.setIcon(icon(self.entry_icon(entry)))
            self.list.addItem(item)
            if entry['id'] == selected_id:
                selected_row = self.list.count()-1
        self.list.blockSignals(False)
        catalog = [e for e in self.library.entries if not self.apps_only or e.get('app')]
        self.count_label.setText(tr('{visible} / {total} eklenti · {installed} eklendi', visible=self.list.count(), total=len(catalog), installed=len(installed & {e['id'] for e in catalog})))
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
        self.detail_icon.setPixmap(icon(self.entry_icon(entry)).pixmap(32, 32))
        self.connection_kind.setText(tr('Yerel MCP · HTTP') if entry.get('local_http') else tr('Uzak MCP · HTTPS') if entry['kind'] == 'http' else tr('Yerel MCP · Node.js') if entry['kind'] == 'npm' else tr('Yerel MCP · Python'))
        self.title.setText(entry["name"])
        self.publisher.setText(entry["publisher"] + " · " + tr(entry["category"]))
        self.description.setText(tr(entry["description"]))
        self.access.setText(tr(entry["permissions"]))
        required = requirement(entry)
        prefix = 'Ortam değişkeni gerekli: '
        self.requirements.setText(_auth_message(entry) or (tr(prefix) + required[len(prefix):] if required.startswith(prefix) else tr(required)))
        self.workspace_row.setVisible(bool(entry.get("workspace")))
        self.command.setPlainText(entry.get("package") or entry.get("url", ""))
        configured = next((spec for spec in self.window.config.settings.mcp_servers if spec.get("library_id") == entry["id"]), None)
        already = configured is not None
        self._selecting = True
        self.enable.setText(tr('Etkin') if already else tr('Kurulumdan sonra etkinleştir'))
        self.enable.setChecked(bool(configured and configured.get('enabled')))
        self._selecting = False
        self.test_button.setVisible(already)
        self.install_button.setText(tr('Bağlantı eklendi') if already else tr('Bağlantıyı ekle') if entry["kind"] == "http" else tr('Kur ve ekle'))
        self.install_button.setEnabled(not already and not (self.worker and self.worker.isRunning()))
        self.status.setText("" if not already else tr('Yapılandırıldı · bağlantı doğrulaması için Test et seç. Hesapların izinleri kendi sağlayıcında yönetilir.'))

    def toggle_enabled(self, enabled):
        if self._selecting or not self.selected_entry:
            return
        for spec in self.window.config.settings.mcp_servers:
            if spec.get('library_id') != self.selected_entry['id']:
                continue
            issue = authentication_issue(self.selected_entry) if enabled else ''
            if issue:
                self.enable.blockSignals(True)
                self.enable.setChecked(False)
                self.enable.blockSignals(False)
                self.status.setText(_auth_message(self.selected_entry))
                return
            spec['enabled'] = enabled
            self.window.config.save()
            self.window.refresh_mcp()
            self.refresh()
            return

    def test_connection(self):
        if not self.selected_entry or self.worker and self.worker.isRunning():
            return
        if self.window.config.settings.offline:
            self.status.setText(tr('Çevrimdışı modda bağlantı testi kapalı.'))
            return
        spec = next((copy.deepcopy(spec) for spec in self.window.config.settings.mcp_servers if spec.get('library_id') == self.selected_entry['id']), None)
        if spec is None:
            return
        from ..mcp import MCPClient
        self.set_installing(True)
        self.cancel_button.setText(tr('Testi durdur'))
        self.status.setText(tr('Bağlantı deneniyor…'))
        def action(worker):
            client = MCPClient(spec, cancel=worker.cancel, timeout=20)
            try:
                client.open()
                if worker.cancel.is_set():
                    return None
                return client.tools()
            except InterruptedError:
                return None
            finally:
                client.close()
        def done(tools):
            self.set_installing(False)
            self.select(self.list.currentItem())
            self.status.setText(tr('Bağlantı testi durduruldu.') if tools is None else tr('Bağlantı doğrulandı · {count} araç', count=len(tools)))
            self.status.setToolTip('\n'.join(tool.get('name', '') for tool in tools or []))
        self.worker = self.window.run_task(action, done, self.status.setText)
        self.worker.operation = 'test'
        self.worker.failed.connect(lambda message: (self.set_installing(False), self.status.setText(message)))

    @staticmethod
    def entry_icon(entry):
        return entry.get('icon') or {'Dosyalar': 'folder', 'Belgeler': 'file', 'Araştırma': 'globe', 'Bellek ve plan': 'thinking', 'Geliştirme': 'code', 'Yardımcılar': 'clock', 'Dokümantasyon': 'book'}.get(entry['category'], 'tools')

    def set_installing(self, active):
        self.install_progress.setVisible(active)
        self.cancel_button.setVisible(active)
        for control in (self.search, self.category, self.type_filter, self.list, self.workspace, self.enable, self.test_button):
            control.setEnabled(not active)
        self.install_button.setEnabled(not active)

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
        if enabled and authentication_issue(entry):
            self.status.setText(_auth_message(entry))
            return
        self.set_installing(True)
        self.cancel_button.setText(tr('Kurulumu durdur'))
        self.status.setText(tr('Kurulum hazırlanıyor…'))
        def action(worker):
            try:
                return self.library.install(ident, workspace, cancel=worker.cancel, status=worker.status.emit)
            except InterruptedError:
                return None
        def complete(spec):
            if spec is None:
                self.set_installing(False)
                self.refresh()
                self.status.setText(tr('Kurulum durduruldu. İstediğinde yeniden deneyebilirsin.'))
                return
            spec["enabled"] = enabled
            servers = self.window.config.settings.mcp_servers
            if not any(s.get("library_id") == ident for s in servers):
                servers.append(spec)
                self.window.config.save()
                self.window.refresh_mcp()
            self.set_installing(False)
            self.refresh()
            self.status.setText(tr('Bağlantı eklendi. ') + (tr('Sohbette kullanılabilir.') if enabled else tr('Bağlantılar sayfasında test edip etkinleştirebilirsin.')))
        self.worker = self.window.run_task(action, complete, self.status.setText)
        def failed(message):
            self.status.setText(message)
            self.set_installing(False)
        self.worker.failed.connect(failed)

    def cancel(self):
        if self.worker:
            self.worker.cancel.set()
            self.status.setText(tr('Bağlantı testi durduruluyor…') if getattr(self.worker, 'operation', '') == 'test' else tr('Kurulum durduruluyor…'))

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


class SkillsBrowser(QWidget):
    def __init__(self, window):
        super().__init__()
        from ..skills import SkillLibrary
        self.window = window
        self.library = SkillLibrary(window.config)
        self.selected_id = None
        self._selecting = False
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        layout.addWidget(label(tr('Beceriler modeline çalışma kılavuzu sağlar. Etkin beceriler görevle eşleştiğinde kullanılır; yeni bir model veya araç yetkisi eklemez.'), 'subtitle'))
        actions = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText(tr('Beceri adı veya açıklamasında ara…'))
        self.search.setClearButtonEnabled(True)
        actions.addWidget(self.search, 1)
        actions.addWidget(button(tr('SKILL.md seç'), self.import_file, icon_name='file'))
        actions.addWidget(button(tr('Klasörden ekle'), self.import_folder, icon_name='folder'))
        layout.addLayout(actions)
        self.scope = FilterTabs()
        for title, value in [('Tümü', ''), ('Kütüphane', 'available'), ('Yerleşik', 'bundled'), ('İçe aktarılan', 'imported'), ('Etkin', 'enabled')]:
            self.scope.addItem(tr(title), value)
        layout.addWidget(self.scope)
        split = QSplitter(Qt.Orientation.Horizontal)
        split.setChildrenCollapsible(False)
        self.list = QListWidget()
        self.list.setObjectName('extensionList')
        self.list.setIconSize(QSize(24, 24))
        self.list.setSpacing(4)
        self.list.setMinimumWidth(220)
        split.addWidget(self.list)
        right = QWidget()
        column = QVBoxLayout(right)
        column.setContentsMargins(18, 8, 0, 8)
        self.title = label('', 'brand')
        self.description = label('', 'subtitle')
        self.source = label('', 'status')
        self.source.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.support = label(tr('Metin kılavuzları ve kaynaklar yüklenir. Başlatıcılar, scriptler, tarayıcı veya hesap yetkileri ayrıca kullanılabilir araç gerektirir.'), 'status')
        self.enabled = QCheckBox(tr('Etkin'))
        self.preview = QPlainTextEdit()
        self.preview.setReadOnly(True)
        self.preview.setAccessibleName(tr('Beceri kılavuzu'))
        self.resource = ChoiceBox()
        self.resource.setAccessibleName(tr('Beceri kaynak dosyası'))
        self.resource.currentIndexChanged.connect(self.read_resource)
        for field in (self.title, self.description, self.source, self.support, self.enabled):
            column.addWidget(field)
        column.addWidget(self.resource)
        column.addWidget(self.preview, 1)
        self.remove_button = button(tr('Beceriyi kaldır'), self.remove, icon_name='trash')
        skill_actions = QHBoxLayout()
        self.source_button = button(tr('Resmî kaynak'), self.open_source, icon_name='globe')
        self.source_button.setObjectName('ghost')
        self.install_button = button(tr('Beceriyi ekle'), self.install_curated, True, 'download')
        skill_actions.addWidget(self.source_button)
        skill_actions.addStretch()
        skill_actions.addWidget(self.remove_button)
        skill_actions.addWidget(self.install_button)
        column.addLayout(skill_actions)
        split.addWidget(right)
        split.setSizes([280, 500])
        self.details = right
        layout.addWidget(split, 1)
        self.status = label('', 'status')
        layout.addWidget(self.status)
        layout.addWidget(label(tr('Yalnızca seçtiğin SKILL.md ve sınırlı metin kaynakları içe aktarılır. Kişisel klasörlerin taranmaz; scriptler çalıştırılmaz.'), 'status'))
        self.search.textChanged.connect(self.refresh)
        self.scope.currentChanged.connect(self.refresh)
        self.list.currentItemChanged.connect(self.select)
        self.enabled.toggled.connect(self.toggle_enabled)
        self.refresh()

    def refresh(self):
        selected = self.selected_id
        self.list.blockSignals(True)
        self.list.clear()
        query, scope = self.search.text().casefold().strip(), self.scope.currentData()
        row = 0
        for entry in sorted(self.library.entries(include_available=True), key=lambda entry: (not entry.get('curated'), entry['name'].casefold())):
            if (scope == 'available' and not entry.get('curated') or scope == 'bundled' and not entry['bundled']
                    or scope == 'imported' and (entry['bundled'] or entry.get('curated')) or scope == 'enabled' and not entry['enabled']):
                continue
            if query and query not in (entry['name'] + ' ' + entry['description']).casefold():
                continue
            text = entry['name'] + '\n' + (tr('Eklenebilir') if entry.get('installed') is False else tr('Etkin') if entry['enabled'] else tr('Kapalı'))
            item = QListWidgetItem(text)
            item.setData(Qt.ItemDataRole.UserRole, entry)
            item.setIcon(icon('book'))
            self.list.addItem(item)
            if entry['id'] == selected:
                row = self.list.count()-1
        self.list.blockSignals(False)
        self.details.setVisible(bool(self.list.count()))
        if self.list.count():
            self.list.setCurrentRow(row)
            self.select(self.list.currentItem())
        else:
            self.selected_id = None
            self.status.setText(tr('Eşleşen beceri yok. Filtreyi değiştir veya kendi SKILL.md dosyanı ekle.'))

    def select(self, item, previous=None):
        if item is None:
            return
        entry = item.data(Qt.ItemDataRole.UserRole)
        self.selected_id = entry['id']
        self.title.setText(entry['name'])
        self.description.setText(entry['description'])
        self.source.setText(tr('Yerleşik') if entry['bundled'] else entry['license'] + ' · ' + entry['revision'][:12] if entry.get('curated') else str(entry['source']))
        self.source_button.setVisible(bool(entry.get('curated')))
        available = entry.get('installed') is False
        self.install_button.setVisible(available)
        self.enabled.setVisible(not available)
        self._selecting = True
        self.enabled.setChecked(entry['enabled'])
        self._selecting = False
        self.remove_button.setVisible(not entry['bundled'] and not available)
        try:
            value = self.library.read(entry['id'], require_enabled=False)
            self.preview.setPlainText(value['content'])
            self.status.setText(tr('Kılavuzun sınırlı bir bölümü gösteriliyor.') if value.get('limited') else tr('Kılavuz önizlemesi · metin düzenlenmez, script çalıştırılmaz.'))
            resources = value.get('resources', [])
            missing = value.get('missing_resources', [])
            self.source.setToolTip('')
            self.resource.blockSignals(True)
            self.resource.clear()
            self.resource.addItem('SKILL.md', 'SKILL.md')
            for resource in resources:
                self.resource.addItem(str(resource), str(resource))
            self.resource.blockSignals(False)
            self.resource.setVisible(bool(resources))
            if resources or missing:
                self.source.setToolTip(tr('{available} kaynak hazır · {missing} kaynak alınamadı', available=len(resources), missing=len(missing)))
        except (ValueError, OSError) as exc:
            self.preview.clear()
            self.status.setText(str(exc))

    def read_resource(self):
        if not self.selected_id or not self.resource.currentData():
            return
        try:
            value = self.library.read(self.selected_id, path=self.resource.currentData(), require_enabled=False)
            self.preview.setPlainText(value['content'])
            self.status.setText(tr('Kılavuzun sınırlı bir bölümü gösteriliyor.') if value.get('limited') else tr('Kılavuz önizlemesi · metin düzenlenmez, script çalıştırılmaz.'))
        except (ValueError, OSError) as exc:
            self.status.setText(str(exc))

    def install_curated(self):
        if not self.selected_id:
            return
        try:
            self.library.install_curated(self.selected_id)
            self.refresh()
            self.status.setText(tr('Özgün beceri ve kaynakları doğrulandı; gerektiğinde sohbette kullanılabilir.'))
        except (ValueError, OSError) as exc:
            self.status.setText(str(exc))

    def open_source(self):
        entry = next((entry for entry in self.library.entries(include_available=True) if entry['id'] == self.selected_id), None)
        if entry and entry.get('curated'):
            QDesktopServices.openUrl(QUrl(entry['source']))

    def toggle_enabled(self, enabled):
        if self._selecting or not self.selected_id:
            return
        try:
            self.library.set_enabled(self.selected_id, enabled)
            self.refresh()
        except (ValueError, OSError) as exc:
            self.status.setText(str(exc))

    def import_file(self):
        raw, _ = QFileDialog.getOpenFileName(self, tr('Beceri kılavuzu seç'), str(self.window.config.root), 'SKILL.md (SKILL.md);;Markdown (*.md)')
        if raw:
            self.import_path(raw)

    def import_folder(self):
        raw = QFileDialog.getExistingDirectory(self, tr('SKILL.md içeren klasörü seç'), str(self.window.config.root))
        if raw:
            self.import_path(raw)

    def import_path(self, raw):
        try:
            entry = self.library.import_path(Path(raw))
            self.selected_id = entry['id']
            self.search.clear()
            self.scope.setCurrentIndex(0)
            self.refresh()
            self.status.setText(tr('Beceri içe aktarıldı. Etkinlik durumunu buradan değiştirebilirsin.'))
        except (ValueError, OSError) as exc:
            self.status.setText(str(exc))

    def remove(self):
        if not self.selected_id:
            return
        try:
            self.library.remove(self.selected_id)
            self.selected_id = None
            self.refresh()
        except (ValueError, OSError) as exc:
            self.status.setText(str(exc))


class IntegrationHub(QWidget):
    """One management area; app rows reuse actual MCP configurations."""
    def __init__(self, window):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.tabs = QTabWidget()
        self.mcp = ExtensionBrowser(window)
        self.apps = ExtensionBrowser(window, apps_only=True)
        self.skills = SkillsBrowser(window)
        self.tabs.addTab(self.mcp, 'MCP')
        self.tabs.addTab(self.apps, tr('Uygulamalar'))
        self.tabs.addTab(self.skills, tr('Beceriler'))
        self.tabs.currentChanged.connect(self.refresh_current)
        layout.addWidget(self.tabs)

    @property
    def worker(self):
        return next((panel.worker for panel in (self.mcp, self.apps) if panel.worker and panel.worker.isRunning()), None)

    def refresh_current(self, index):
        self.tabs.widget(index).refresh()


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


def show_extension_library(window, initial_tab=0):
    dialog = InlineDialog(window.centralWidget(), tr('Eklenti kütüphanesi'), 980, 720, _surfaces(window))
    try:
        panel = IntegrationHub(window)
        panel.tabs.setCurrentIndex(initial_tab)
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
