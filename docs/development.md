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
./kayriva.sh build             # Build the Linux single-file application
./kayriva.sh run               # Launch the compiled Linux application
./kayriva.sh build-windows     # Build the Windows installer through Wine
./kayriva.sh run-windows       # Launch the Windows build through Wine
./kayriva.sh test              # Run tests
./kayriva.sh release           # Verify both builds and generate update assets
./kayriva.sh status            # Show environments and output paths
```

| Platform | Single file to distribute | Notes |
| --- | --- | --- |
| **Linux** | `dist/linux/Kayriva` | Includes Python/Qt and the MCP bridge. Requires compatible system libraries/ABI; rebuild on an older target distribution when necessary. |
| **Windows x64** | `dist/windows/Kayriva-Setup.exe` | Installs shortcuts and an uninstaller without requiring administrator privileges. |

Windows builds require **Wine, winepath and curl** on the build host. Initial setup installs official Python, pinned PySide6 and Inno Setup into the project's `build/wine-prefix`. A Qt DLL loading check runs before packaging. Build logs are stored in `build/linux/` and `build/windows/`. `clean` removes build output while preserving the prepared Wine environment.

The installer itself can run offline. **Model weights, local runtime packages and personal data are not included in the distribution.** Downloading models or preparing a runtime requires internet access; existing files can also be added manually. Optional Transformers dependencies are not included in the standard package.

### Verification scope

```bash
./kayriva.sh test
```

Tests cover chat/modal behavior, project boundaries, file-change checks, download verification/resume, memory budgets, image transport, MCP and GitHub previews. Some HTTP/model tests use simulated responses; they do not prove compatibility for every model or GPU. The Windows installer is checked under Wine, which does not replace inference testing on physical Windows hardware.

The optional Transformers text backend supports CPU/GPU/hybrid placement with additional dependencies and compatible weights. End-to-end inference with real Transformers weights has not yet been verified.

