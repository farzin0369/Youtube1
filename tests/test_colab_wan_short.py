from __future__ import annotations

import subprocess

from scripts import colab_wan_real_short


def test_colab_cli_preinstalled_dependencies_skip_kernel_pip(monkeypatch):
    monkeypatch.setenv("COLAB_DEPS_READY", "1")

    def unexpected_install(*args, **kwargs):
        raise AssertionError("pip must not run inside the active Colab kernel")

    monkeypatch.setattr(subprocess, "check_call", unexpected_install)
    monkeypatch.setattr(colab_wan_real_short.shutil, "which", lambda _name: "/usr/bin/ffmpeg")
    colab_wan_real_short.ensure_deps()
