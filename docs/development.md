# Development and packaging

Use Python 3.11 or later. Run commands from the project root.

**`kayriva.sh`** is the single management entry point. No separate `start.sh` is required.

```text
src/          Application source and tests
models/       Curated catalog; downloaded weights are not distributed
engine/       Local runtime setup and release manifest
extensions/   MCP extension catalog and sample configuration
docs/         Guides, design assets and release notes
kayriva.sh    Launch, test and package
```

```bash
./kayriva.sh setup             # Linux environment and packaging dependencies
./kayriva.sh start             # Run from source
./kayriva.sh build             # Build the Linux application and its .tar.gz archive
./kayriva.sh archive-linux     # Archive an existing verified Linux build
./kayriva.sh run               # Launch the compiled Linux application
./kayriva.sh build-windows     # Build the Windows installer through Wine
./kayriva.sh run-windows       # Launch the Windows build through Wine
./kayriva.sh test              # Run tests
./kayriva.sh release           # Verify both builds and generate update assets
./kayriva.sh status            # Show environments and output paths
```

| Platform | Single file to distribute | Notes |
| --- | --- | --- |
| **Linux** | `dist/linux/Kayriva-x86_64.AppImage` | Includes Python/Qt and the MCP bridge. Requires compatible system libraries/ABI; rebuild on an older target distribution when necessary. |
| **Windows x64** | `dist/windows/Kayriva-Setup.exe` | Installs shortcuts and an uninstaller without requiring administrator privileges. |

Windows builds require **Wine, winepath and curl** on the build host. Initial setup installs official Python, pinned PySide6 and Inno Setup into the project's `build/wine-prefix`. A Qt DLL loading check runs before packaging. Build logs are stored in `build/linux/` and `build/windows/`. `clean` removes build output while preserving the prepared Wine environment.

The installer itself can run offline. **Model weights, local runtime packages and personal data are not included in the distribution.** Downloading models or preparing a runtime requires internet access; existing files can also be added manually. Optional Transformers dependencies are not included in the standard package.

### Verification scope

```bash
./kayriva.sh test
```

Tests cover chat/modal behavior, project boundaries, file-change checks, download verification/resume, memory budgets, image transport, MCP and GitHub previews. Some HTTP/model tests use simulated responses; they do not prove compatibility for every model or GPU. The Windows installer is checked under Wine, which does not replace inference testing on physical Windows hardware.

The optional Transformers text backend supports CPU/GPU/hybrid placement with additional dependencies and compatible weights. End-to-end inference with real Transformers weights has not yet been verified.


## Linux desktop identity

The portable Linux executable registers a user-level application entry and a persistent SVG icon on its first normal launch. It remains a single download; extracted temporary files are not used as launcher targets.

- Application ID / desktop filename: `io.github.sayrias.Kayriva` / `io.github.sayrias.Kayriva.desktop`.
- Menu entry: `$XDG_DATA_HOME/applications/`, or `~/.local/share/applications/` when the variable is unset or relative.
- Icon: `icons/hicolor/scalable/apps/io.github.sayrias.Kayriva.svg` under the same data directory.
- X11 window class: `Kayriva`. Qt uses the application ID for Wayland desktop matching.
- `Exec` points to the actual portable executable. Opening the application after moving it refreshes the entry without creating duplicates.
- Source launches and screenshot captures do not register a menu entry. A read-only desktop-data directory is logged and does not prevent the application from opening.

To explicitly register the packaged executable without opening its window:

```bash
./Kayriva-x86_64.AppImage --install-desktop
```

The build and the packaged application's first normal launch also register a dedicated file type for the published **Kayriva-x86_64.AppImage** filename. KDE/GNOME file managers can then display **Kayriva application** and its icon directly on the portable file, independently of the application-menu entry. The file is a real Type 2 AppImage with an embedded SquashFS AppDir, desktop entry and icon; system-wide executable icons are not changed. Keep the published `Kayriva-x86_64.AppImage` filename for this file-type association.

This uses a user-level Shared MIME definition in `mime/packages/io.github.sayrias.Kayriva.xml` and the system `update-mime-database` utility. Existing user MIME definitions are preserved. If the utility is unavailable, menu/window integration still works and the file type will be registered on a later launch when available. A recipient must run the application once to install this local metadata; automatic file icon display before first launch depends on the file manager’s AppImage support. Refresh an already open folder after registration.

For builds in CI or a restricted sandbox, `KAYRIVA_SKIP_FILE_ICON=1 ./kayriva.sh build` skips host icon registration without changing the packaged application's first-launch behavior.

References: [Qt desktop file identity](https://doc.qt.io/qtforpython-6/PySide6/QtGui/QGuiApplication.html#PySide6.QtGui.QGuiApplication.setDesktopFileName), [desktop entry keys](https://specifications.freedesktop.org/desktop-entry/latest/recognized-keys.html), [executable-path quoting](https://specifications.freedesktop.org/desktop-entry/latest/exec-variables.html), [Shared MIME definitions](https://specifications.freedesktop.org/shared-mime-info/latest/), [KDE file icon resolution](https://invent.kde.org/frameworks/kio/-/blob/master/src/core/kfileitem.cpp).

## Linux archive and compatibility

`build` and `release` also produce `dist/linux/Kayriva-VERSION-linux-ARCH.tar.gz`. Use `archive-linux` to package the current verified executable without rebuilding it. The archive contains the app, its icon, a short installation guide, measured compatibility metadata, font license and file checksums. User data and model weights are excluded by a fixed file list.

The packaging helper checks the build version, architecture and binary SHA-256, then inspects ELF version requirements in the main app and its bundled bridge. It records the highest required GLIBC symbol version in `compatibility.json`; `readelf` from binutils is required on the packaging host. `dist/SHA256SUMS` covers both binaries and the current Linux archive. The application's automatic updater continues to use the raw portable executable.

An archive changes delivery, not system compatibility. See the [Linux distribution guide](linux-distribution.md) for the current baseline and supported environment.
