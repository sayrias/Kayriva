# Linux downloads and compatibility

Download **`Kayriva-x86_64.AppImage`** for Linux. This is a genuine Type 2 AppImage with an AppDir, launcher and icon. The optional `.tar.gz` wraps the same AppImage, preserves its executable permission and adds a short setup guide. Both formats have the same system requirements.

## Current build

- Architecture: **x86_64 (64-bit Intel/AMD)**.
- C library: **glibc 2.43 or newer**, measured from the ELF symbol requirements of the bundled libraries.
- A compatible X11 or Wayland desktop, system libraries and graphics drivers are also required.
- This build is not for musl-based systems, ARM or 32-bit installations. A separate build is needed for another architecture or libc.

These are necessary requirements; the package has not been tested on every distribution. The GLIBC version is measured from the actual artifacts, rather than inferred only from the build host. Each archive includes `compatibility.json` with its own result.

## Extract and start

Extract `Kayriva-1.0.0-beta.2-linux-x86_64.tar.gz`, open the extracted folder and run:

```bash
./Kayriva-x86_64.AppImage
```

If executable permissions were lost:

```bash
chmod +x Kayriva-x86_64.AppImage
```

The first launch registers the application menu entry and the dedicated file icon. Keep the executable named `Kayriva-x86_64.AppImage`. Models and inference runtimes are separate downloads; existing user conversations and models stay in the user data directory.

## Verify the archive contents

Inside the extracted folder:

```bash
sha256sum --check SHA256SUMS
```

## Supporting older distributions

Compressing a binary or wrapping it in another container does not lower its GLIBC requirements. Build on the oldest GNU/Linux baseline intended for support, using dependencies compatible with that baseline, then test the resulting application on the target distributions. The current build must not be advertised as universal Linux support. This follows the [PyInstaller GNU/Linux compatibility guidance](https://pyinstaller.org/en/stable/usage.html#making-gnu-linux-apps-forward-compatible).


## When FUSE is unavailable

The AppImage runtime can extract and run without mounting:

```bash
./Kayriva-x86_64.AppImage --appimage-extract-and-run
```

[AppImage execution and extraction](https://docs.appimage.org/user-guide/run-appimages.html) do not change the application payload's system requirements. AppImage is a packaging format, not a promise of compatibility with older GLIBC versions.

## Packaging toolchain

`./kayriva.sh build` creates the private Python/Qt payload, then packages `build/linux/Kayriva.AppDir` using the official appimagetool and Type 2 runtime. Their download sizes and SHA-256 values are pinned in `scripts/appimage-tools.json`; verified downloads are cached under `build/appimage-tools`. An upstream digest change fails the build until the pin is reviewed. The build does not install system packages. The launcher and updater resolve the outer `APPIMAGE` path, so menu entries and updates target the real downloaded file rather than a temporary mount.
