"""Conditionally repair an incompatible TorchAO install in Colab, then verify CogVideoX import.

This intentionally keeps Colab's CUDA-enabled PyTorch wheel. It removes only the
TorchAO import package directory when that installed package is missing FqnToConfig
or cannot be imported; it does not reinstall torch or torchvision.
"""
from __future__ import annotations

import importlib
import importlib.util
import shutil
import site
import sys
from pathlib import Path


def find_torchao_dirs() -> list[Path]:
    roots: list[Path] = []
    try:
        roots.extend(Path(path) for path in site.getsitepackages())
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


def torchao_needs_repair() -> bool:
    spec = importlib.util.find_spec("torchao")
    if spec is None:
        return False
    try:
        import torchao.quantization as quantization
        return not hasattr(quantization, "FqnToConfig")
    except Exception:
        return True


def repair_torchao_if_needed() -> list[str]:
    if not torchao_needs_repair():
        print("TorchAO is absent or compatible; no removal needed.")
        return []
    removed = []
    for name in list(sys.modules):
        if name == "torchao" or name.startswith("torchao."):
            del sys.modules[name]
    for path in find_torchao_dirs():
        print("Removing incompatible TorchAO package directory:", path)
        shutil.rmtree(path)
        removed.append(str(path))
    importlib.invalidate_caches()
    return removed


def main() -> None:
    import torch
    print("Python:", sys.version.split()[0])
    print("PyTorch:", torch.__version__)
    print("CUDA available:", torch.cuda.is_available())
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA GPU is not active. Select a Colab GPU runtime before CogVideoX generation.")
    print("GPU:", torch.cuda.get_device_name(0))
    removed = repair_torchao_if_needed()
    if removed:
        print("Removed incompatible TorchAO package directories:", len(removed))
    from diffusers import CogVideoXPipeline
    print("SUCCESS: CogVideoXPipeline import works; the model stack is ready.")


if __name__ == "__main__":
    main()
