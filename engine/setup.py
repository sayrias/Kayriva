"""Build a user-selected llama.cpp revision inside this application.

Network activity occurs only when this script is explicitly run. No remote
installer script is executed; source builds use git + CMake. The tool itself
must be trusted because building third-party source executes its build rules.
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description="Build the app's private llama.cpp engine")
    parser.add_argument("--ref", required=True, help="Exact upstream release tag or commit to build")
    parser.add_argument("--backend", choices=["cpu", "cuda", "vulkan"], default="cpu")
    parser.add_argument("--jobs", type=int, default=2)
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    source, build = root / "vendor/llama.cpp", root / "build"
    for command in ("git", "cmake"):
        if not shutil.which(command):
            raise SystemExit(f"Gerekli araç kurulu değil: {command}")
    if args.jobs < 1:
        raise SystemExit("jobs en az 1 olmalı")
    if not source.exists():
        source.parent.mkdir(exist_ok=True)
        subprocess.run(["git", "clone", "--filter=blob:none", "https://github.com/ggml-org/llama.cpp.git", str(source)], check=True)
    if subprocess.check_output(["git", "-C", str(source), "status", "--porcelain"], text=True).strip():
        raise SystemExit("Motor kaynaklarında yerel değişiklikler var; korunmaları için kurulum durduruldu.")
    subprocess.run(["git", "-C", str(source), "fetch", "origin", args.ref], check=True)
    subprocess.run(["git", "-C", str(source), "checkout", "--detach", "FETCH_HEAD"], check=True)
    revision = subprocess.check_output(["git", "-C", str(source), "rev-parse", "HEAD"], text=True).strip()
    flags = [f"-DGGML_CUDA={'ON' if args.backend == 'cuda' else 'OFF'}", f"-DGGML_VULKAN={'ON' if args.backend == 'vulkan' else 'OFF'}",
             "-DCMAKE_BUILD_TYPE=Release", "-DBUILD_SHARED_LIBS=OFF", "-DGGML_BACKEND_DL=OFF", "-DLLAMA_CURL=OFF", "-DLLAMA_BUILD_TESTS=OFF"]
    subprocess.run(["cmake", "-S", str(source), "-B", str(build), *flags], check=True)
    subprocess.run(["cmake", "--build", str(build), "--config", "Release", "--parallel", str(args.jobs), "--target", "llama-server"], check=True)
    candidates = [build / "bin/llama-server", build / "bin/Release/llama-server.exe", build / "bin/llama-server.exe"]
    binary = next((p for p in candidates if p.exists()), None)
    if not binary:
        raise SystemExit("Derleme tamamlandı ama llama-server dosyası bulunamadı")
    destination = root / "bin" / binary.name
    destination.parent.mkdir(exist_ok=True)
    shutil.copy2(binary, destination)
    destination.chmod(0o755)
    (root / "bin/build-info.txt").write_text(f"revision={revision}\nbackend={args.backend}\n", encoding="utf-8")
    print(f"Motor hazır: {destination}\nSürüm: {revision}")


if __name__ == "__main__":
    main()
