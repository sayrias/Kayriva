#!/usr/bin/env bash
# Kayriva: kaynak koddan çalıştırma ve Linux / Wine-Windows paketleme.
set -Eeuo pipefail
kayriva_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
kayriva_python="${KAYRIVA_PYTHON:-$kayriva_root/.venv/bin/python}"
[[ -x "$kayriva_python" ]] || command -v "$kayriva_python" >/dev/null 2>&1 || kayriva_python=python3
kayriva_prefix="${KAYRIVA_WINE_PREFIX:-$kayriva_root/build/wine-prefix}"
kayriva_windows_python='C:\KayrivaPython\python.exe'
trap 'printf "\nİşlem tamamlanamadı (satır %s). Yukarıdaki hata ayrıntılarını kontrol et.\n" "$LINENO" >&2' ERR

help_text() {
    cat <<'HELP'
Kayriva — tek dosyadan yönetim

  ./kayriva.sh                 Etkileşimli menü
  ./kayriva.sh start [arg...]  Uygulamayı kaynak koddan aç
  ./kayriva.sh setup           Linux Python ortamını ve bağımlılıkları kur
  ./kayriva.sh build           Linux tek dosyalı uygulamasını derle
  ./kayriva.sh archive-linux   Mevcut Linux paketinden .tar.gz arşivi üret
  ./kayriva.sh run [arg...]    Derlenmiş Linux uygulamasını aç
  ./kayriva.sh setup-windows   Wine içinde Windows Python ve bağımlılıkları kur
  ./kayriva.sh build-windows   Wine üzerinden Windows Setup.exe derle
  ./kayriva.sh run-windows     Derlenen Windows uygulamasını Wine ile aç
  ./kayriva.sh release [arg..] Derlenmiş iki platform için güncelleme manifesti üret
  ./kayriva.sh clean           Derleme çıktılarını temizle (kurulum ortamını korur)
  ./kayriva.sh test            Testleri çalıştır
  ./kayriva.sh status          Ortam ve çıktı konumlarını göster
  ./kayriva.sh help            Bu açıklamayı göster

Çıktılar: dist/linux/Kayriva, Linux .tar.gz ve dist/windows/Kayriva-Setup.exe
Linux arşivi aynı uygulamayı içerir; sistem uyumluluğunu değiştirmez.
Ayarlar ve indirilen modeller kullanıcı veri klasöründe korunur.
Model ağırlıkları, sohbetler ve kurulu motorlar pakete kopyalanmaz.
Kurulum internet gerektirir. Sistem paketleri / sudo kullanılmaz.
Windows derlemesi için wine, winepath ve curl sistemde kurulu olmalıdır.
İsteğe bağlı: KAYRIVA_PYTHON, KAYRIVA_WINE_PREFIX ortam değişkenleri.
HELP
}

check_python() {
    "$kayriva_python" -c 'import sys; assert sys.version_info >= (3, 11), "Python 3.11 veya üzeri gerekli"'
}

setup_linux() {
    check_python
    if [[ ! -x "$kayriva_root/.venv/bin/python" ]]; then
        "$kayriva_python" -m venv --system-site-packages "$kayriva_root/.venv"
    fi
    kayriva_python="$kayriva_root/.venv/bin/python"
    "$kayriva_python" -m pip install -e "$kayriva_root[package]"
    printf '\nLinux ortamı hazır. Başlatmak için: ./kayriva.sh start\n'
}

require_modules() {
    check_python
    if ! "$kayriva_python" -c 'import PySide6, httpx' 2>/dev/null; then
        printf 'Uygulama bağımlılıkları kuruluyor...\n'
        setup_linux
    fi
}

start_app() {
    require_modules
    AI_STUDIO_ROOT="$kayriva_root" PYTHONPATH="$kayriva_root/src${PYTHONPATH:+:$PYTHONPATH}" \
        "$kayriva_python" -m ai_studio "$@"
}

prepare_entries() {
    mkdir -p "$kayriva_root/build/entries"
    cat > "$kayriva_root/build/entries/Kayriva.py" <<'PY'
from ai_studio.distribution import initialize_bundle
initialize_bundle()
from ai_studio.__main__ import main
if __name__ == '__main__':
    raise SystemExit(main())
PY
    cat > "$kayriva_root/build/entries/KayrivaBridge.py" <<'PY'
from ai_studio.bridge import main
if __name__ == '__main__':
    main()
PY
    QT_QPA_PLATFORM=offscreen PYTHONPATH="$kayriva_root/src" "$kayriva_python" - "$kayriva_root/build/entries/Kayriva.ico" <<'PY'
import sys
from PySide6.QtWidgets import QApplication
from ai_studio.ui.icons import icon
app = QApplication([])
assert icon('kayriva').pixmap(64, 64).toImage().save(sys.argv[1], 'ICO')
PY
}

record_build() {
    "$kayriva_python" - "$kayriva_root" "$1" "$2" "$3" <<'PY'
import hashlib, json, sys, tomllib
from pathlib import Path
root, platform, artifact, architecture = sys.argv[1:]
path = Path(artifact)
version = tomllib.loads((Path(root) / 'pyproject.toml').read_text())['project']['version']
digest = hashlib.file_digest(path.open('rb'), 'sha256').hexdigest()
metadata = {'version': version, 'platform': platform, 'architecture': architecture,
            'filename': path.name, 'size': path.stat().st_size, 'sha256': digest}
(path.parent / 'build-info.json').write_text(json.dumps(metadata, indent=2) + '\n')
PY
}

build_linux() {
    require_modules
    if ! "$kayriva_python" -c 'import PyInstaller' 2>/dev/null; then
        setup_linux
    fi
    prepare_entries
    mkdir -p "$kayriva_root/build/linux/helpers" "$kayriva_root/dist/linux"
    local common=(--noconfirm --clean --onefile --paths "$kayriva_root/src"
        --workpath "$kayriva_root/build/linux/work" --specpath "$kayriva_root/build/linux"
        --exclude-module torch --exclude-module transformers)
    "$kayriva_python" -m PyInstaller "${common[@]}" --name KayrivaBridge --console \
        --distpath "$kayriva_root/build/linux/helpers" \
        "$kayriva_root/build/entries/KayrivaBridge.py" 2>&1 | tee "$kayriva_root/build/linux/bridge.log"
    "$kayriva_python" -m PyInstaller "${common[@]}" --name Kayriva --windowed \
        --distpath "$kayriva_root/dist/linux" \
        --add-data "$kayriva_root/src/ai_studio/ui/assets:ai_studio/ui/assets" \
        --add-data "$kayriva_root/models/catalog.json:models" \
        --add-data "$kayriva_root/engine/releases.json:engine" \
        --add-data "$kayriva_root/extensions/catalog.json:extensions" \
        --add-binary "$kayriva_root/build/linux/helpers/KayrivaBridge:helpers" \
        "$kayriva_root/build/entries/Kayriva.py" 2>&1 | tee "$kayriva_root/build/linux/build.log"
    record_build linux "$kayriva_root/dist/linux/Kayriva" "$(uname -m)"
    if [[ "${KAYRIVA_SKIP_FILE_ICON:-0}" != 1 ]]; then
        if ! PYTHONPATH="$kayriva_root/src" "$kayriva_python" -c 'from ai_studio.desktop import install_file_icon; raise SystemExit(0 if install_file_icon() else 1)'; then
            printf 'Dosya ikonu bu ortamda kaydedilemedi; uygulama ilk açılışta yeniden deneyecek.\n' >&2
        fi
    fi
    archive_linux
    printf '\nLinux tek dosyalı uygulama hazır: %s/dist/linux/Kayriva\n' "$kayriva_root"
}

archive_linux() {
    check_python
    "$kayriva_python" "$kayriva_root/scripts/package_linux.py" --root "$kayriva_root"
}

wine_env() {
    WINEPREFIX="$kayriva_prefix" WINEDEBUG=-all PYTHONUTF8=1 PYTHONIOENCODING=utf-8 wine "$@"
}

windows_path() {
    WINEPREFIX="$kayriva_prefix" WINEDEBUG=-all winepath -w "$1" | tr -d '\r'
}

check_wine() {
    local program
    for program in wine winepath; do
        command -v "$program" >/dev/null || {
            printf '%s bulunamadı. Dağıtımının paket yöneticisinden Wine kur, sonra tekrar dene.\n' "$program" >&2
            return 1
        }
    done
    [[ "$kayriva_prefix" = /* ]] || { printf 'Wine ortamının yolu mutlak olmalı.\n' >&2; return 1; }
    mkdir -p "$kayriva_prefix"
}

setup_windows() {
    check_wine
    if [[ ! -f "$kayriva_prefix/drive_c/KayrivaPython/python.exe" ]]; then
        command -v curl >/dev/null || { printf 'Python kurulumunu indirmek için curl gerekli.\n' >&2; return 1; }
        local installer="$kayriva_root/build/python-3.12.10-amd64.exe"
        printf 'Resmi Windows Python kurulumu indiriliyor; ayrı Wine ortamı hazırlanıyor...\n'
        curl --fail --location --retry 3 --connect-timeout 20 \
            'https://www.python.org/ftp/python/3.12.10/python-3.12.10-amd64.exe' -o "$installer.part"
        mv -- "$installer.part" "$installer"
        wine_env "$(windows_path "$installer")" /quiet InstallAllUsers=0 \
            'TargetDir=C:\KayrivaPython' Include_pip=1 Include_test=0 Include_launcher=0 PrependPath=0
    fi
    wine_env "$kayriva_windows_python" -c 'import sys; assert sys.version_info >= (3,11); assert sys.platform == "win32"'
    # Qt 6.8 LTS: Wine'da da doğrulanabilen, Windows derlemesi için sabit sürüm.
    wine_env "$kayriva_windows_python" -m pip install 'PySide6==6.8.3' 'httpx>=0.28,<1' 'pyinstaller>=6'
    wine_env "$kayriva_windows_python" -c 'from PySide6 import QtCore, QtGui, QtWidgets, QtNetwork, QtSvg; print("Qt hazır:", QtCore.qVersion())'
    printf '\nWindows derleme ortamı hazır.\n'
}

setup_installer() {
    if [[ -f "$kayriva_prefix/drive_c/KayrivaInno/ISCC.exe" ]]; then
        return
    fi
    command -v curl >/dev/null || { printf 'Kurulum derleyicisini indirmek için curl gerekli.\n' >&2; return 1; }
    local installer="$kayriva_root/build/innosetup-6.7.3.exe"
    curl --fail --location --retry 3 --connect-timeout 20 \
        'https://github.com/jrsoftware/issrc/releases/download/is-6_7_3/innosetup-6.7.3.exe' -o "$installer.part"
    mv -- "$installer.part" "$installer"
    wine_env "$(windows_path "$installer")" /VERYSILENT /SUPPRESSMSGBOXES /NORESTART /SP- \
        '/DIR=C:\KayrivaInno'
}

prepare_installer() {
    "$kayriva_python" - "$kayriva_root" \
        "$(windows_path "$kayriva_root/build/windows/package/Kayriva")" \
        "$(windows_path "$kayriva_root/dist/windows")" \
        "$(windows_path "$kayriva_root/build/entries/Kayriva.ico")" <<'PY'
import sys
import tomllib
import re
from pathlib import Path
root, package, output, icon = sys.argv[1:]
version = tomllib.loads((Path(root) / 'pyproject.toml').read_text())['project']['version']
match = re.fullmatch(r'(\d+\.\d+\.\d+)(?:-[A-Za-z0-9.-]+)?', version)
if not match:
    raise ValueError('Sürüm X.Y.Z veya X.Y.Z-beta.N biçiminde olmalı')
numeric_version = match.group(1)
script = r'''[Setup]
AppId={{5F17CD5E-C536-4D65-A694-7F280460C5AF}
AppName=Kayriva
AppVersion=@VERSION@
AppVerName=Kayriva @VERSION@
VersionInfoVersion=@NUMERIC_VERSION@
VersionInfoTextVersion=@VERSION@
VersionInfoProductTextVersion=@VERSION@
AppPublisher=Kayriva
DefaultDirName={localappdata}\Programs\Kayriva
DefaultGroupName=Kayriva
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
OutputDir=@OUTPUT@
OutputBaseFilename=Kayriva-Setup
SetupIconFile=@ICON@
UninstallDisplayIcon={app}\Kayriva.exe
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
CloseApplications=no
RestartApplications=no

[Languages]
Name: "turkish"; MessagesFile: "compiler:Languages\Turkish.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Masaüstü kısayolu oluştur"; GroupDescription: "Kısayollar:"; Flags: unchecked

[InstallDelete]
Type: filesandordirs; Name: "{app}\_internal"

[Files]
Source: "@PACKAGE@\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Kayriva"; Filename: "{app}\Kayriva.exe"
Name: "{autodesktop}\Kayriva"; Filename: "{app}\Kayriva.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\Kayriva.exe"; Description: "Kayriva'yı aç"; Flags: nowait postinstall skipifsilent
'''
for key, value in {'VERSION': version, 'NUMERIC_VERSION': numeric_version, 'PACKAGE': package, 'OUTPUT': output, 'ICON': icon}.items():
    script = script.replace('@' + key + '@', value)
(Path(root) / 'build/windows/Kayriva.iss').write_text(script, encoding='utf-8')
PY
}

build_windows() {
    check_wine
    require_modules
    if [[ ! -f "$kayriva_prefix/drive_c/KayrivaPython/python.exe" ]] || \
       ! wine_env "$kayriva_windows_python" -c 'import PySide6, httpx, PyInstaller; from PySide6 import QtCore; assert PySide6.__version__ == "6.8.3"' 2>/dev/null; then
        setup_windows
    fi
    setup_installer
    prepare_entries
    mkdir -p "$kayriva_root/build/windows/package" "$kayriva_root/dist/windows"
    local common=(--noconfirm --clean --onedir --paths "$(windows_path "$kayriva_root/src")"
        --distpath "$(windows_path "$kayriva_root/build/windows/package")"
        --workpath "$(windows_path "$kayriva_root/build/windows/work")"
        --specpath "$(windows_path "$kayriva_root/build/windows")"
        --exclude-module torch --exclude-module transformers)
    wine_env "$kayriva_windows_python" -m PyInstaller "${common[@]}" --name Kayriva --windowed \
        --icon "$(windows_path "$kayriva_root/build/entries/Kayriva.ico")" \
        --add-data "$(windows_path "$kayriva_root/src/ai_studio/ui/assets");ai_studio/ui/assets" \
        --add-data "$(windows_path "$kayriva_root/models/catalog.json");models" \
        --add-data "$(windows_path "$kayriva_root/engine/releases.json");engine" \
        --add-data "$(windows_path "$kayriva_root/extensions/catalog.json");extensions" \
        "$(windows_path "$kayriva_root/build/entries/Kayriva.py")" 2>&1 | tee "$kayriva_root/build/windows/build.log"
    wine_env "$kayriva_windows_python" -m PyInstaller "${common[@]}" --name KayrivaBridge --console \
        "$(windows_path "$kayriva_root/build/entries/KayrivaBridge.py")" 2>&1 | tee "$kayriva_root/build/windows/bridge.log"
    cp -a -- "$kayriva_root/build/windows/package/KayrivaBridge/." "$kayriva_root/build/windows/package/Kayriva/"
    prepare_installer
    wine_env 'C:\KayrivaInno\ISCC.exe' "$(windows_path "$kayriva_root/build/windows/Kayriva.iss")" \
        2>&1 | tee "$kayriva_root/build/windows/installer.log"
    record_build windows "$kayriva_root/dist/windows/Kayriva-Setup.exe" x86_64
    printf '\nTek dosyalı Windows kurulumu hazır: %s/dist/windows/Kayriva-Setup.exe\n' "$kayriva_root"
}

release_files() {
    require_modules
    local version linux_arch
    version="$("$kayriva_python" - "$kayriva_root" <<'PY'
import hashlib, json, sys, tomllib
from pathlib import Path
root = Path(sys.argv[1])
version = tomllib.loads((root / 'pyproject.toml').read_text())['project']['version']
for platform in ('linux', 'windows'):
    info = root / 'dist' / platform / 'build-info.json'
    if not info.is_file():
        raise SystemExit(f'{platform}: önce güncel kaynakla derle; build-info.json eksik.')
    metadata = json.loads(info.read_text())
    artifact = info.parent / metadata['filename']
    if (metadata['version'] != version or metadata['platform'] != platform
            or not artifact.is_file() or artifact.stat().st_size != metadata['size']):
        raise SystemExit(f'{platform}: derleme sürümü/dosyası eşleşmiyor; yeniden derle.')
    with artifact.open('rb') as stream:
        if hashlib.file_digest(stream, 'sha256').hexdigest() != metadata['sha256']:
            raise SystemExit(f'{platform}: derlenmiş dosya değişmiş; yeniden derle.')
print(version)
PY
)"
    linux_arch="$("$kayriva_python" -c 'import json,sys; print(json.load(open(sys.argv[1]))["architecture"])' "$kayriva_root/dist/linux/build-info.json")"
    archive_linux
    PYTHONPATH="$kayriva_root/src${PYTHONPATH:+:$PYTHONPATH}" "$kayriva_python" -m ai_studio.updater manifest \
        --version "$version" --output "$kayriva_root/dist/update-manifest.json" \
        --artifact "linux:$linux_arch:portable=$kayriva_root/dist/linux/Kayriva" \
        --artifact "windows:x86_64:installer=$kayriva_root/dist/windows/Kayriva-Setup.exe" "$@"
    (cd -- "$kayriva_root" && sha256sum dist/linux/Kayriva dist/windows/Kayriva-Setup.exe "dist/linux/Kayriva-$version-linux-$linux_arch.tar.gz" > dist/SHA256SUMS)
    printf '\nYayın dosyaları hazır: dist/update-manifest.json ve platform paketleri.\n'
}

clean_outputs() {
    rm -rf -- "$kayriva_root/dist" "$kayriva_root/build/linux" "$kayriva_root/build/windows" "$kayriva_root/build/entries"
    printf 'Derleme çıktıları temizlendi. Kaynaklar, modeller, sohbetler ve Wine ortamı korundu.\n'
}

run_package() {
    local executable="$kayriva_root/dist/linux/Kayriva"
    [[ -x "$executable" ]] || { printf 'Önce ./kayriva.sh build ile derle.\n' >&2; return 1; }
    AI_STUDIO_ROOT="$kayriva_root" "$executable" "$@"
}

run_windows_package() {
    check_wine
    local executable="$kayriva_root/build/windows/package/Kayriva/Kayriva.exe"
    [[ -f "$executable" ]] || { printf 'Önce ./kayriva.sh build-windows ile derle.\n' >&2; return 1; }
    # Windows paketi kendi yanındaki verileri kullanır; Linux motor yollarını almaz.
    env -u AI_STUDIO_ROOT WINEPREFIX="$kayriva_prefix" WINEDEBUG=-all wine "$(windows_path "$executable")" "$@"
}

show_status() {
    printf 'Proje: %s\nPython: %s\nWine ortamı: %s\n' "$kayriva_root" "$kayriva_python" "$kayriva_prefix"
    "$kayriva_python" --version
    command -v wine >/dev/null && wine --version || true
    local file
    for file in dist/linux/Kayriva dist/windows/Kayriva-Setup.exe; do
        if [[ -f "$kayriva_root/$file" ]]; then printf 'Hazır: %s\n' "$file"; else printf 'Henüz derlenmedi: %s\n' "$file"; fi
    done
}

dispatch() {
    local action="${1:-help}"
    shift || true
    case "$action" in
        start) start_app "$@" ;;
        setup) setup_linux ;;
        build|build-linux) build_linux ;;
        archive-linux) archive_linux ;;
        run) run_package "$@" ;;
        setup-windows) setup_windows ;;
        build-windows) build_windows ;;
        run-windows) run_windows_package "$@" ;;
        release) release_files "$@" ;;
        test) require_modules; QT_QPA_PLATFORM=offscreen PYTHONPATH="$kayriva_root/src${PYTHONPATH:+:$PYTHONPATH}" "$kayriva_python" -m unittest discover -s "$kayriva_root/src/tests" ;;
        status) show_status ;;
        clean) clean_outputs ;;
        help|--help|-h) help_text ;;
        *) printf 'Bilinmeyen seçenek: %s\n' "$action" >&2; help_text; return 2 ;;
    esac
}

if [[ $# -gt 0 ]]; then
    dispatch "$@"
elif [[ -t 0 ]]; then
    while true; do
        printf '\nKayriva\n  1) Başlat\n  2) Linux bağımlılıklarını kur\n  3) Linux tek dosya derle\n  4) Derlenmiş uygulamayı aç\n  5) Windows ortamını kur (Wine)\n  6) Windows Setup.exe derle (Wine)\n  7) Testleri çalıştır\n  8) Durum\n  9) Windows paketini aç (Wine)\n  10) Derleme çıktılarını temizle\n  11) Güncelleme yayın dosyalarını hazırla\n  12) Linux .tar.gz arşivi üret\n  0) Çıkış\n'
        read -r -p 'Seçim: ' kayriva_choice || break
        case "$kayriva_choice" in
            1) dispatch start ;; 2) dispatch setup ;; 3) dispatch build ;; 4) dispatch run ;;
            5) dispatch setup-windows ;; 6) dispatch build-windows ;; 7) dispatch test ;; 8) dispatch status ;;
            9) dispatch run-windows ;; 10) dispatch clean ;; 11) dispatch release ;; 12) dispatch archive-linux ;; 0) break ;; *) printf '0–12 arasında bir seçenek gir.\n' ;;
        esac
    done
else
    help_text
fi
