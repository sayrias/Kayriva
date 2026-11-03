# Application updates

Kayriva includes a release checker, verified package staging, an optional differential update format, and a deferred installer. The configured public source is **`sayrias/Kayriva`**, as chosen by the maintainer. A missing repository/release produces a readable status and leaves the installation untouched.

## Checking and channels

The application uses GitHub's public [list releases endpoint](https://docs.github.com/en/rest/releases/releases#list-releases). It reads at most 30 published releases, ignores drafts, compares semantic versions, and selects a matching operating system and CPU architecture. A regular Git tag without a GitHub Release is insufficient. No GitHub credential is bundled or required for public release checks.

A beta installation accepts newer prereleases and stable releases. A stable installation accepts stable releases by default. `beta.10` sorts after `beta.2`; equal versions and downgrades are ignored, and build metadata does not change version precedence. This follows [SemVer 2.0.0](https://semver.org/).

Settings expose startup checks and automatic downloading/staging. Both are enabled by default and run in workers; network failure must not delay opening the workspace. Automatic downloading never replaces the running application, closes a workspace, or restarts in the background. Installation requires the visible **Restart to update** action and is blocked while generation or another active operation is running. After that explicit action, the UI quits gracefully only when the deferred installer has launched successfully. Downloading a package alone never changes the running application. Source-code installations can check and download, but automatic replacement refuses to overwrite the Python interpreter: update those installations through the source repository.

Default settings are `update_repository = "sayrias/Kayriva"`, `check_updates_on_startup = true`, `auto_install_updates = true`. The legacy internal name `auto_install_updates` controls automatic **download and staging**, not unattended application replacement. Disabling startup checks leaves manual checking available. A release's details link opens its exact GitHub release page.

## Manifest and release files

Every compatible release must include:

- `update-manifest.json`;
- the Linux portable executable and/or Windows installer named in the manifest;
- any optional `.kdelta` files referenced by the manifest.

Model weights, user settings, chats, engines, environment files and credentials are not update artifacts. Their persistent user-data directories remain separate from the installed application.

Minimal manifest:

```json
{
  "schema": 1,
  "version": "1.0.0-beta.2",
  "files": [
    {
      "name": "Kayriva-x86_64.AppImage",
      "platform": "linux",
      "arch": "x86_64",
      "kind": "portable",
      "size": 123456789,
      "sha256": "<64 lowercase hexadecimal characters>"
    },
    {
      "name": "Kayriva-Setup.exe",
      "platform": "windows",
      "arch": "x86_64",
      "kind": "installer",
      "size": 34567890,
      "sha256": "<64 lowercase hexadecimal characters>"
    }
  ]
}
```

The example sizes are illustrative. The builder computes real values from the final artifacts. The release tag should be `v1.0.0-beta.2`; its normalized version must match the manifest. Supported target keys are `linux`/`windows` and `x86_64`/`aarch64`. Only publish architectures that have actually been built and validated; merely listing an architecture does not produce its executable.

Build both platforms and run the release command:

```bash
./kayriva.sh build
./kayriva.sh build-windows
./kayriva.sh release
```

The shell release command checks build records against the current version and artifact hashes to avoid silently combining an old platform build with a new version. It then calls the backend manifest generator. Publishing the listed files is a separate maintainer action; the script does not upload a release.

Equivalent backend invocation:

```bash
PYTHONPATH=src python3 -m ai_studio.updater manifest \
  --version 1.0.0-beta.2 \
  --output dist/update-manifest.json \
  --artifact linux:x86_64:portable=dist/linux/Kayriva \
  --artifact windows:x86_64:installer=dist/windows/Kayriva-Setup.exe
```

The manifest contains asset names rather than arbitrary download URLs. The checker resolves each asset through the selected repository's actual GitHub Release and requires its browser download URL to belong to that exact repository and tag. A publisher-supplied GitHub asset digest, when present for the full artifact, must also agree with the manifest SHA-256.

## Differential downloads

PyInstaller's [one-file format](https://pyinstaller.org/en/stable/operating-mode.html#bundling-to-one-file) contains compressed support files and an embedded archive. A small source edit can change many bytes in a rebuilt executable. A compressed Windows installer has the same practical limitation: there is no honest guarantee that every update will transfer only a few changed source files.

The backend provides **`kayriva-block-v1`** without an extra runtime dependency:

1. The builder hashes 64 KiB blocks in the previous artifact.
2. Matching blocks in the new artifact become copy instructions. Changed blocks become bounded zlib-compressed literals.
3. A patch is retained only when it is smaller than **85%** of the full artifact. Otherwise the release uses the full file.
4. The client requires the exact prior version and SHA-256. Linux can use its installed portable executable as a base. Windows must use the previous verified cached **installer**, because installed `Kayriva.exe` is not the same file as `Kayriva-Setup.exe`.
5. It downloads and verifies the patch, reconstructs a new staged artifact, then verifies the complete target size and SHA-256 before any installation.
6. A missing/mismatched base or a failed patch falls back to the complete verified package. Cancellation propagates and does not trigger a fallback download.

To produce a later release with a known previous public artifact:

```bash
./kayriva.sh release \
  --previous linux:x86_64:1.0.0-beta.1=/absolute/path/to/previous/Kayriva \
  --previous windows:x86_64:1.0.0-beta.1=/absolute/path/to/previous/Kayriva-Setup.exe
```

Patch files are created beside `update-manifest.json`, with names such as `Kayriva.1.0.0-beta.1-to-1.0.0-beta.2.kdelta`. Upload only the patches referenced in the completed manifest. The first public beta has no required differential base. Keep each published version immutable and retain its original artifact for future patch generation.

[BSDiff](https://www.daemonology.net/bsdiff/) was considered: it can produce compact executable differences but its original builder has substantial memory requirements. The implemented block format avoids adding a compiled dependency to the app, at the cost of finding fewer matches when compression or offsets change. No measured savings for future Kayriva releases are claimed. A future uncompressed/component distribution could improve reuse, but would change the current single-file distribution contract.

## Installation and recovery

**Linux portable:** the client verifies the download, copies it beside the executable on the same filesystem, retains executable permissions, flushes it, and starts a system `sh` helper using positional arguments. The helper waits for the current process to exit, rechecks SHA-256, moves the current executable to `.Kayriva.previous`, then installs the staged executable. A failed replacement restores the previous file. A nonzero exit within the first five seconds of the attempted restart also restores and restarts the previous executable. This is a limited early-start check, not a complete health check; a later application failure can still require manual rollback using `.Kayriva.previous`. An unwritable installation directory or missing `sh`/`sha256sum` leaves a verified package for manual installation. The helper waits at most six minutes and never kills another process.

**Windows installer:** a generated PowerShell helper waits for the application to close and rechecks the installer's size/hash. It launches Inno Setup with `/SILENT /NORESTART /CURRENTUSER /NOCLOSEAPPLICATIONS` and the existing installation directory. The installer performs normal file installation and the helper restarts Kayriva only after exit code zero. Errors are recorded beside the staged package as `.install-error.log`. Windows PowerShell must be available. Company execution policy or a read-only install location can require manual installation. The updater does not force-close another application or restart Windows. Native Windows installation behavior still requires platform testing; Wine is not evidence for every Windows policy/driver configuration. See [Inno Setup command-line parameters](https://jrsoftware.org/ishelp/topic_setupcmdline.htm).

System helper processes receive a sanitized library search environment and `PYINSTALLER_RESET_ENVIRONMENT=1` so a restarted one-file process does not reuse the old extraction directory. Windows temporarily resets the inherited DLL directory before launching PowerShell, then restores the application's setting. This follows [PyInstaller subprocess guidance](https://pyinstaller.org/en/stable/common-issues-and-pitfalls.html#launching-external-programs-from-the-frozen-application).

## Bounds and trust

- Metadata is capped at 2 MiB; a full artifact/patch at 512 MiB; a manifest at 16 platform rows and 8 delta bases per row.
- HTTP connect/read timeouts are bounded, cancellation is checked between chunks, and redirects are capped. Every redirect must remain HTTPS on an explicit GitHub release host allowlist. No URL from release notes is executed.
- Asset names cannot contain paths or traversal segments. The updater does not unpack publisher archives into user directories. A patch can copy only bounded ranges from the verified base and produce at most its expected target size; decompressed literals are capped at one block.
- Downloads use unique private `.part` files and atomic publication. Incomplete or mismatched content is never treated as an installed update. Disk space is checked before staging.
- HTTPS plus hashes verifies transport and content consistency **within the trusted GitHub publisher account**. A publisher-account compromise can replace both manifest and binary. This system does not yet include independent Ed25519/Authenticode signing, a pinned signing key, or a reproducible-build attestation. Do not describe it as independently signed.
- Release checks disclose an ordinary public API request, app user-agent and network address to GitHub; they do not include prompts, chats, local paths, model files or account credentials.

## Verification

Offline HTTP fixtures cover stable/beta ordering, missing repositories, unavailable architectures, drafts/downgrades, malformed manifests, unsafe filenames, repository/asset mismatch, content corruption, cancellation, disallowed redirects, verified cache reuse, working delta reconstruction, decompression bounds, corrupt-delta full fallback and cached Windows installer selection. A real temporary-file Linux helper test covers replacement and early failure rollback, including spaces and quotes in installation paths. Test subprocesses touch only temporary fixtures.

No actual public release is available until the maintainer publishes the repository and compatible assets. Publication, signing-key ownership and real future delta savings remain outside this local verification.
