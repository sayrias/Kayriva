# Linux downloads and compatibility

Kayriva is available as a standalone executable or a `.tar.gz` containing the same executable, its icon and a short setup guide. Both formats have the same system requirements.

## Current build

- Architecture: **x86_64 (64-bit Intel/AMD)**.
- C library: **glibc 2.43 or newer**, measured from the ELF symbol requirements of the bundled libraries.
- A compatible X11 or Wayland desktop, system libraries and graphics drivers are also required.
- This build is not for musl-based systems, ARM or 32-bit installations. A separate build is needed for another architecture or libc.

These are necessary requirements; the package has not been tested on every distribution. The GLIBC version is measured from the actual artifacts, rather than inferred only from the build host. Each archive includes `compatibility.json` with its own result.

## Extract and start

Extract `Kayriva-1.0.0-beta.1-linux-x86_64.tar.gz`, open the extracted folder and run:

```bash
./Kayriva
```

If executable permissions were lost:

```bash
chmod +x Kayriva
```

The first launch registers the application menu entry and the dedicated file icon. Keep the executable named `Kayriva`. Models and inference runtimes are separate downloads; existing user conversations and models stay in the user data directory.

## Verify the archive contents

Inside the extracted folder:

```bash
sha256sum --check SHA256SUMS
```

## Supporting older distributions

Compressing a binary or wrapping it in another container does not lower its GLIBC requirements. Build on the oldest GNU/Linux baseline intended for support, using dependencies compatible with that baseline, then test the resulting application on the target distributions. The current build must not be advertised as universal Linux support. This follows the [PyInstaller GNU/Linux compatibility guidance](https://pyinstaller.org/en/stable/usage.html#making-gnu-linux-apps-forward-compatible).
