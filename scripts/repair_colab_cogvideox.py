"""Repair an orphaned TorchAO install in Colab, then test the CogVideoX import.

Run after installing requirements-local.txt. This only removes the TorchAO package
directory if the installed package lacks FqnToConfig, the exact symbol that
causes the reported Diffusers import failure.
"""
from __future__ import annotations

import importlib
import importlib.util
import shutil
import site
import sys
from pathlib import Path

def find_torchao_dirs() -> list[Path]:
    roots = []
    try:
        roots.extend(Path(p) for p in site.getsitepackages())
    except Exception:
        pass
    try:
        roots.append(Path(site.getusersitepackages()))
    except Exception:
        pass
    found = []
    for root in dict.fromkeys(roots):
        candidate = root / "torchao"
        if candidate.is_dir():
            found.append(candidate)
    return found

def main() -> None:
    print("Python:", sys.version.split()[0])
    print("CUDA torch available:", end=" ")
    try:
        import torch
        print(torch.cuda.is_available(), "|", torch.__version__)
    except Exception as exc:
        print("torch import failed:", repr(exc))

    bad_dirs = []
    spec = importlib.util.find_spec("torchao")
    if spec is not None:
        try:
            import torchao.quantization as tq
            if not hasattr(tq, "FqnToConfig"):
                bad_dirs = find_torchao_dirs()
        except Exception:
            bad_dirs = find_torchao_dirs()

    if bad_dirs:
        for name in list(sys.modules):
            if name == "torchao" or name.startswith("torchao."):
                del sys.modules[name]
        for path in bad_dirs:
            print("Removing incompatible/orphaned package:", path)
            shutil.rmtree(path)
        importlib.invalidate_caches()
    else:
        print("No orphaned incompatible TorchAO package detected.")

    try:
        from diffusers import CogVideoXPipeline
        print("SUCCESS: CogVideoXPipeline import works.")
        print("Next step: run your project with VIDEO_ENGINE=cogvideox.")
    except Exception as exc:
        print("CogVideoX import still fails:", type(exc).__name__, str(exc))
        print("Full traceback follows:")
        raise

if __name__ == "__main__":
    main()
