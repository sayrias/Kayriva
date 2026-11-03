from pathlib import Path

STYLE = """
QWidget#chatContext { background: transparent; }
QComboBox#chatProject { background: transparent; border: 1px solid transparent; padding: 4px 24px 4px 2px; font-size: 12px; }
QComboBox#chatProject:hover, QComboBox#chatProject:focus { border-color: #686475; background: #242832; }
QFrame#modelVariantRow { background: #24272f; border: 1px solid #3a414d; border-radius: 10px; }
QFrame#modelVariantRow:hover { border-color: #656379; background: #272c35; }
QLabel#modelVariantName { font-size: 13px; font-weight: 600; }
QLabel#modelVariantMeta { font-size: 12px; color: #bac0cd; }

QPushButton#attachmentImage { padding: 2px; border: 1px solid #444b59; background: #20242b; border-radius: 7px; }
QPushButton#attachmentImage:hover { border-color: #c9bcec; background: #303441; }
QDialog#imagePreview QScrollArea { background: #14161b; border: 1px solid #3c4350; border-radius: 8px; }
QLabel#activityNarrative { color: #d9dbe3; font-size: 14px; padding: 6px 0 10px; }
QWidget#activityGroup, QWidget#activityOperation { background: transparent; }
QPushButton#activityGroupToggle { background: transparent; color: #b8bbc8; text-align: left; border: none; padding: 5px 2px; font-size: 12px; }
QPushButton#activityGroupToggle:hover, QPushButton#activityGroupToggle:focus { color: #f0e9ff; background: #262b35; }
QPushButton#activityGroupArrow { background: transparent; border: none; padding: 5px; }
QScrollArea#activityGroupDetails, QScrollArea#activityGroupDetails QWidget { background: transparent; border: none; }

QLineEdit#chatSearch { background: #1d2027; border: 1px solid #303541; border-radius: 9px; font-size: 12px; padding: 6px 8px; }
QLineEdit#chatSearch:focus { border-color: #a491c7; background: #242832; }
QListWidget#promptList, QListWidget#promptList QWidget { background: #20232a; }
QListWidget#promptList::item { margin: 2px 0; padding: 8px 12px; border-radius: 9px; }
QListWidget#promptList::item:selected { background: #373c49; }
QPushButton:focus, QLineEdit:focus, QPlainTextEdit:focus { border-color: #a491c7; }
QPushButton#destructiveButton { background: #b54453; color: #ffffff; border: 1px solid #c85766; border-radius: 8px; padding: 6px 12px; }
QPushButton#destructiveButton:hover { background: #c65262; }
QPushButton#destructiveButton:pressed { background: #973a47; }

QWidget#memoryControl { background: transparent; }
QLabel#memoryAmount { color: #d7c8ef; font-weight: 500; }
QSlider#memorySlider { background: transparent; }
QSlider#memorySlider::groove:horizontal { background: #424048; height: 5px; border-radius: 2px; }
QSlider#memorySlider::sub-page:horizontal { background: #b9a1de; border-radius: 2px; }
QSlider#memorySlider::handle:horizontal { background: #e2d3f6; border: 2px solid #a78bce; width: 12px; margin: -5px 0; border-radius: 7px; }
QSlider#memorySlider::handle:horizontal:hover { background: #f1e9ff; border-color: #d3b6f9; }
QSlider#memorySlider::sub-page:horizontal:disabled { background: #504858; }
QSlider#memorySlider::handle:horizontal:disabled { background: #675e72; border-color: #5a5065; }
QWidget#messageActions { background: transparent; }
QPushButton#activitySummary { background: transparent; color: #a39aa9; border: none; border-radius: 6px; padding: 3px 6px; font-size: 12px; text-align: left; }
QPushButton#activitySummary:hover { color: #ded3eb; background: #262a33; }
QFrame#activityDivider, QFrame#menuDivider { background: #383e49; border: none; }
QFrame#activityDetails { background: transparent; border: none; }
QWidget#activityTimeline, QWidget#activityStep { background: transparent; }
QLabel#activityTime { color: #a4a8b6; font-size: 11px; }
QLabel#activityStepTitle { color: #cbc3d3; font-size: 12px; }
QLabel#activityStepHint { color: #a4a8b6; font-size: 12px; }
QPushButton#messageAction { background: transparent; border: none; border-radius: 7px; padding: 5px; }
QPushButton#messageAction:hover, QPushButton#messageAction:focus { background: #302b36; }
QPushButton#messageAction:pressed { background: #403647; }
* { font-family: 'Adwaita Sans', 'Noto Sans', sans-serif; font-size: 14px; color: #ececf1; }
QMainWindow, QDialog, QWidget { background: #1b1d23; }
QLabel { background: transparent; }
QFrame#sidebar { background: #15171c; border: none; border-right: 1px solid #292d37; }
QFrame#topbar { background: #1b1d23; border: none; }
QFrame#welcome { border: none; background: transparent; }
QFrame#card { background: #24272f; border: 1px solid #3b404b; border-radius: 16px; }
QFrame#brandPopup { background: #242831; border: 1px solid #626375; border-radius: 10px; }
QFrame#brandPopup QListWidget { background: transparent; }
QFrame#brandPopup QListWidget::item { padding: 8px 10px; border-radius: 6px; }
QFrame#brandPopup QListWidget::item:selected { background: #454053; }
QPushButton#activityTool { background: transparent; border: none; padding: 2px 3px; font-size: 12px; color: #b9bfcd; text-align: left; }
QPushButton#activityTool:hover { background: #292d36; color: #ececf1; }
QTextBrowser#documentPreview { background: #20242c; border: 1px solid #424855; border-radius: 10px; padding: 20px; font-size: 14px; }
QPlainTextEdit#activityPayload { font-size: 11px; background: #171a20; border: 1px solid #363c48; border-radius: 6px; padding: 8px; }
QPushButton#resumeTask { background: #302f3d; border: 1px solid #665b78; color: #ded1f2; padding: 6px 12px; }
QScrollArea#attachmentStrip, QScrollArea#attachmentStrip QWidget { background: transparent; border: none; }
QFrame#attachmentTile { background: #20242d; border: 1px solid #48505f; border-radius: 9px; }
QFrame#composer { background: #282b34; border: 1px solid #434956; border-radius: 20px; }
QFrame#userMessage { background: #30333f; border: none; border-radius: 17px; }
QFrame#assistantMessage { background: #1b1d23; border: none; }
QLabel#brand { font-size: 21px; font-weight: 600; }
QLabel#hero { font-family: 'Adwaita Sans', 'Noto Sans', sans-serif; font-size: 34px; font-weight: 500; }
QLabel#title { font-size: 24px; font-weight: 600; }
QLabel#subtitle { color: #adb0be; font-size: 13px; }
QLabel#pill { color: #ccbfeb; background: #35303f; border: none; border-radius: 8px; padding: 6px 10px; font-size: 11px; }
QLabel#fitBadge { color: #c1bcce; background: #313036; border-radius: 7px; padding: 7px 10px; font-size: 11px; }
QFrame#preferences QComboBox#quantPicker { background: #29282d; border-color: #403d47; font-size: 12px; }
QLabel#status { color: #9a9dab; font-size: 11px; }
QLabel#sectionLabel { color: #a2a9ba; font-size: 12px; font-weight: 500; padding-left: 10px; }
QLabel#sidebarShortcut { color: #adb3c4; font-size: 10px; background: transparent; }
QFrame#sidebarDivider { background: #2b303a; border: none; }
QPushButton#sidebarSettings { text-align: left; background: transparent; border: 1px solid transparent; padding: 6px 10px; font-size: 13px; }
QPushButton#sidebarSettings:hover { background: #242832; }
QPushButton#sidebarSettings:focus { border-color: #a898c6; background: #242832; }
QLabel#topTitle { color: #bfb8cb; font-size: 13px; }
QPushButton { background: #2c3039; border: 1px solid #424652; border-radius: 10px; padding: 6px 10px; }
QPushButton:hover { background: #363b46; border-color: #77708b; }
QPushButton:pressed { background: #494151; }
QPushButton:disabled { color: #68616e; background: #26242b; border-color: #302d36; }
QPushButton#primary, QPushButton#applyUpdate { color: #282031; background: #c9bcec; border: none; font-weight: 600; }
QPushButton#primary:hover, QPushButton#applyUpdate:hover { background: #ded3f8; }
QPushButton#primary:disabled, QPushButton#applyUpdate:disabled { color: #756d80; background: #3b3546; }
QPushButton#newChat { text-align: left; background: #272c36; border: 1px solid #3d4453; padding: 7px 10px; padding-right: 62px; font-size: 13px; border-radius: 9px; }
QPushButton#newChat:hover { background: #313744; border-color: #777185; }
QPushButton#newChat:focus { border-color: #b9a8d8; }
QPushButton#newChat:pressed { background: #383847; }
QPushButton#sectionToggle { background: transparent; border: none; color: #aaa0b6; text-align: left; padding: 5px 4px; }
QFrame#projectHeader { border: none; background: transparent; }
QFrame#projectHeader QWidget { background: transparent; }
QPushButton#iconButton { background: transparent; border: none; padding: 5px; }
QPushButton#iconButton:hover { background: #2e3340; }
QPushButton#iconButton:focus { background: #2e3340; border: 1px solid #a898c6; }
QPushButton#ghost { background: transparent; border: none; color: #b4a9c2; }
QPushButton#ghost:hover { background: #312b39; }
QPushButton#modelPicker { background: #252a34; color: #ddd6eb; border: 1px solid #434b5b; padding: 6px 10px; border-radius: 9px; font-size: 12px; }
QPushButton#suggestion { text-align: left; background: #24272f; border: 1px solid #3c424e; padding: 13px; border-radius: 12px; }
QPushButton#suggestion:hover { background: #303541; border-color: #817293; }
QPushButton#welcomeLink { background: transparent; color: #bba6d9; border: none; padding: 12px; }
QPushButton#composerPlus { border-radius: 20px; padding: 6px; background: transparent; border: none; }
QPushButton#composerPlus:hover { background: #44384f; }
QPushButton#sendButton { border-radius: 20px; background: #d9cee9; border: none; padding: 6px; }
QPushButton#sendButton:hover { background: #eee4fa; }
QPushButton#sendButton:disabled { background: #504359; }
QLineEdit, QPlainTextEdit, QTextEdit, QSpinBox, QDoubleSpinBox, QComboBox { background: #1c1f26; border: 1px solid #414754; border-radius: 8px; padding: 7px; selection-background-color: #5b4d72; selection-color: #f5efff; }
QLineEdit:focus, QPlainTextEdit:focus, QComboBox:focus { border-color: #9780af; }
QPlainTextEdit#input { background: #282b34; border: none; padding: 10px 4px; font-size: 13px; }
QComboBox { combobox-popup: 0; padding-right: 34px; min-height: 18px; }
QComboBox:hover { background: #252a34; border-color: #6d7183; }
QComboBox:on { background: #2c303b; border-color: #b9a8d8; }
QComboBox:disabled { color: #9398a6; background: #21242b; border-color: #363b45; }
QComboBox::drop-down { border: none; width: 32px; background: transparent; }
QComboBox::down-arrow { image: url("__ASSETS__/down.svg"); width: 16px; height: 16px; }
QComboBox QAbstractItemView { background: #252a34; border: 1px solid #535b6c; border-radius: 8px; selection-background-color: #3c4052; selection-color: #f5efff; outline: none; padding: 5px; }
QComboBox QAbstractItemView::item { min-height: 26px; padding: 3px 9px; border-radius: 5px; }
QComboBox QAbstractItemView::item:hover { background: #333a48; }
QSpinBox, QDoubleSpinBox { padding-right: 28px; }
QSpinBox::up-button, QDoubleSpinBox::up-button { subcontrol-origin: border; subcontrol-position: top right; width: 25px; border: none; background: transparent; }
QSpinBox::down-button, QDoubleSpinBox::down-button { subcontrol-origin: border; subcontrol-position: bottom right; width: 25px; border: none; background: transparent; }
QSpinBox::up-arrow, QDoubleSpinBox::up-arrow { image: url("__ASSETS__/up.svg"); width: 12px; height: 12px; }
QSpinBox::down-arrow, QDoubleSpinBox::down-arrow { image: url("__ASSETS__/down.svg"); width: 12px; height: 12px; }
QCheckBox { spacing: 10px; background: transparent; }
QCheckBox::indicator { width: 18px; height: 18px; border-radius: 5px; border: 1px solid #756780; background: #25222d; }
QCheckBox::indicator:checked { background: #b9a3d8; border-color: #b9a3d8; image: url("__ASSETS__/check.svg"); }
QListWidget, QTreeWidget { background: #15171c; border: none; outline: none; font-size: 13px; }
QListWidget QWidget, QTreeWidget QWidget { background: #15171c; }
QTreeWidget#sidebarProjects::item, QListWidget#sidebarChats::item { padding: 0; margin: 0; background: transparent; border: none; }
QTreeWidget#sidebarProjects::item:selected, QListWidget#sidebarChats::item:selected { background: transparent; }
QListWidget::item, QTreeWidget::item { padding: 6px 8px; border: none; border-radius: 7px; }
QListWidget::item:selected, QTreeWidget::item:selected { background: #303542; color: #eee6f8; }
QListWidget::item:hover, QTreeWidget::item:hover { background: #242832; }
QTreeWidget::branch { background: transparent; border: none; }
QTextBrowser { border: none; background: #1b1d23; font-size: 15px; selection-background-color: #5b4669; }
QTextBrowser#messageText { padding: 0; border: none; }
QFrame#userMessage QTextBrowser { background: transparent; }
QScrollArea { border: none; background: #1b1d23; }
QScrollBar:vertical { border: none; background: transparent; width: 11px; margin: 0; }
QScrollBar::handle:vertical { background: #554b5f; border-radius: 5px; min-height: 36px; }
QScrollBar::handle:vertical:hover { background: #8f80a7; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }
QProgressBar { background: #35303e; border: none; border-radius: 5px; text-align: center; min-height: 10px; font-size: 10px; }
QProgressBar::chunk { background: #a78bbf; border-radius: 5px; }
QSplitter::handle { background: #37303f; width: 1px; }
QWidget#preferencesOverlay, QWidget#deleteChatOverlay { background: rgba(0, 0, 0, 155); }
QFrame#preferences { background: #20232a; border: 1px solid #48434e; border-radius: 18px; }
QFrame#preferences QLabel { font-size: 13px; }
QFrame#preferences QLabel#status { font-size: 11px; }
QFrame#preferences QFrame#card { border-radius: 12px; }
QFrame#preferences QPlainTextEdit, QFrame#preferences QTextBrowser { font-size: 12px; }
QFrame#preferences QPushButton#iconButton { padding: 4px; background: transparent; border: none; }
QFrame#preferences QPushButton#iconButton:hover { background: #39333e; }
QFrame#preferences QPushButton#closePreferences { background: transparent; border: none; padding: 3px; border-radius: 15px; }
QFrame#preferences QPushButton#closePreferences:hover { background: #3b3541; }
QListWidget#taskList { background: #1c1f26; border-radius: 10px; }
QListWidget#taskList::item { padding: 6px 9px; font-size: 12px; }
QFrame#preferences QLabel#title { font-size: 20px; font-weight: 500; }
QFrame#preferences QLabel#brand { font-size: 16px; font-weight: 500; }
QFrame#preferences QLabel#subtitle { font-size: 12px; }
QFrame#preferences QPushButton { font-size: 12px; padding: 5px 9px; }
QFrame#preferences QLineEdit, QFrame#preferences QSpinBox, QFrame#preferences QDoubleSpinBox { font-size: 12px; padding: 6px; padding-right: 26px; }
QFrame#preferences QComboBox { font-size: 12px; padding: 6px; padding-right: 30px; }
QFrame#preferences QFrame#modelCard { background: #242832; border: 1px solid #3c4351; border-radius: 14px; }
QFrame#preferences QFrame#modelCard QLabel#brand { color: #f0ecf6; font-size: 15px; font-weight: 600; }
QFrame#preferences QLabel#modelSkills { color: #c0c2d3; font-size: 12px; }
QTabBar#filterTabs { background: transparent; }
QTabBar#filterTabs::tab { background: transparent; color: #b8bece; border: 1px solid transparent; border-radius: 8px; margin: 0 4px 0 0; padding: 7px 12px; font-size: 12px; }
QTabBar#filterTabs::tab:hover { background: #2b303c; }
QTabBar#filterTabs::tab:selected { background: #353443; border-color: #716780; color: #f3eefb; }
QTabBar#filterTabs::tab:focus { border-color: #b9a8d8; }
QListWidget#extensionList { background: transparent; border: none; padding: 0; }
QListWidget#extensionList::item { background: #222630; border: 1px solid #343b49; border-radius: 9px; padding: 12px 10px; min-height: 42px; }
QListWidget#extensionList::item:hover { background: #2b303c; border-color: #65637a; }
QListWidget#extensionList::item:selected { background: #343344; border-color: #a898c6; color: #f3eefb; }
QFrame#extensionDetails { background: #222630; border: 1px solid #3b4250; border-radius: 12px; }

QWidget#libraryFilters { background: transparent; }
QSlider#librarySlider { background: transparent; min-height: 22px; }
QSlider#librarySlider::groove:horizontal { background: #444957; height: 4px; border-radius: 2px; }
QSlider#librarySlider::sub-page:horizontal { background: #b5a3d6; border-radius: 2px; }
QSlider#librarySlider::handle:horizontal { background: #e6dcf5; border: 2px solid #aa91ce; width: 11px; margin: -5px 0; border-radius: 7px; }
QSlider#librarySlider::handle:horizontal:hover, QSlider#librarySlider::handle:horizontal:focus { background: #f5edff; border-color: #e1cef7; }
QFrame#preferences QPushButton:checked { background: #3d374d; border-color: #9983b8; color: #f0e6fc; }
QLabel#modelImportFeedback[error="true"] { color: #f1b2bd; }
QListWidget#preferenceNav, QListWidget#preferenceNav QWidget { background: #20232a; font-size: 12px; }
QListWidget#preferenceNav::item { padding: 7px 10px; border-radius: 9px; margin: 2px 0px; }
QListWidget#preferenceNav::item:selected { background: #373c49; color: #eee6f6; }
QListWidget#preferenceNav::item:hover { background: #2a2f39; }
QTabWidget::pane { border: none; }
QTabBar { background: #20232a; }
QTabBar::tab { color: #a99cb6; padding: 12px 12px; background: #20232a; border: none; border-radius: 10px; margin: 0px 3px 8px 0px; font-size: 12px; }
QTabBar::tab:selected { color: #eadbf8; background: #343947; }
QTabBar::tab:hover { background: #302936; }
QFrame#composerMenu { background: #262a33; border: 1px solid #494e5d; border-radius: 15px; }
QFrame#composerMenu QWidget { background: transparent; }
QFrame#composerMenu QFrame#menuDivider { background: #423b49; border: none; }
QFrame#composerMenu QLabel { font-size: 13px; background: transparent; }
QFrame#composerMenu QLabel#menuHint { color: #959099; font-size: 12px; }
QFrame#composerMenu QLabel#menuSection { color: #a09aa7; font-size: 11px; padding: 7px 10px 5px; }
QFrame#composerMenu QPushButton#menuRow { background: transparent; border: none; border-radius: 8px; padding: 0; text-align: left; }
QFrame#composerMenu QPushButton#menuRow:hover, QFrame#composerMenu QPushButton#menuRow:focus { background: #3b393f; }
QFrame#composerMenu QPushButton#modelOption { background: transparent; border: 1px solid transparent; border-radius: 10px; padding: 0; }
QFrame#composerMenu QPushButton#modelOption:hover, QFrame#composerMenu QPushButton#modelOption:focus { background: #37323e; border-color: #4a4154; }
QFrame#composerMenu QPushButton#modelOption[selected="true"] { background: #37303f; border-color: #4f435c; }
QFrame#composerMenu QLabel#modelName { color: #e0d8e8; font-size: 13px; font-weight: 500; }
QFrame#composerMenu QLabel#modelDetail { color: #a79bae; font-size: 11px; }
QMenu { background: #252932; border: 1px solid #494e5d; border-radius: 12px; padding: 7px; }
QMenu::item { padding: 7px 18px; border-radius: 6px; }
QMenu::item:selected { background: #3a3e4c; }
QMenu::separator { height: 1px; background: #424958; margin: 6px 9px; }
QFrame#downloadPanel { background: #262a33; border: 1px solid #414755; border-radius: 12px; }
QFrame#metricCard { background: #262a33; border: 1px solid #3f4552; border-radius: 12px; }
QFrame#preferences QLabel#metricValue { font-size: 25px; font-weight: 600; color: #e1d4f2; }
QFrame#preferences QPushButton#periodButton { background: transparent; border: none; color: #a89daf; border-radius: 8px; padding: 6px 12px; }
QFrame#preferences QPushButton#periodButton:checked { background: #3e334b; color: #e4d5f3; }
QFrame#preferences QPushButton#periodButton:hover { background: #352d3e; }
QTableWidget#usageTable { background: #1c1f26; border: 1px solid #39323f; border-radius: 10px; font-size: 12px; selection-background-color: #3d304b; }
QTableWidget#usageTable::item { padding: 5px 9px; border: none; }
QHeaderView::section { background: #252932; color: #a99bb7; border: none; border-bottom: 1px solid #39323f; padding: 7px 9px; font-size: 11px; }
QFrame#composerMenu QLineEdit { background: #1f232c; border: 1px solid #464e60; padding: 7px 10px; font-size: 12px; }
QFrame#composerMenu QLineEdit:focus { border-color: #b9a8d8; }
QFrame#composerMenu QScrollArea { background: transparent; }
QFrame#composerMenu QScrollArea QWidget { background: transparent; }
QPushButton#modelPicker { padding-right: 28px; }
QPushButton#modelPicker:hover { background: #313744; border-color: #8e819f; }
QPushButton#modelPicker:focus { border-color: #b9a8d8; }
QToolTip { background: #332b3c; color: #eaddf5; border: 1px solid #72607d; border-radius: 5px; padding: 6px; }
""".replace("__ASSETS__", (Path(__file__).parent / "assets").as_posix())
