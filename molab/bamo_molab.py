import marimo

__generated_with = "0.19.0"
app = marimo.App(width="medium")

@app.cell
def _():
    import marimo as mo
    mo.md("""
    # BAMO · OpenMontage GPU workspace

    This notebook prepares the experimental BAMO branch on molab.
    It does **not** publish videos or expose account secrets.
    Enable the GPU from the notebook Specs menu before running the GPU check.
    """)
    return (mo,)

@app.cell
def _(mo):
    import os, subprocess, json, pathlib, textwrap, sys
    REPO_URL = "https://github.com/farzin0369/Youtube1.git"
    BRANCH = "feat/bamo-openmontage-autonomous-studio"
    WORKDIR = pathlib.Path("/tmp/Youtube1-bamo-openmontage")
    def run(cmd, cwd=None, timeout=1800):
        p = subprocess.run(cmd, cwd=cwd, text=True, stdout=subprocess.PIPE,
                           stderr=subprocess.STDOUT, timeout=timeout)
        return p.returncode, p.stdout[-12000:]
    mo.md("## 1. Prepare the isolated experimental checkout")
    if not (WORKDIR / ".git").exists():
        rc, out = run(["git", "clone", "--depth", "1", "--recurse-submodules",
                       "--shallow-submodules", "--branch", BRANCH, REPO_URL, str(WORKDIR)])
    else:
        rc, out = run(["git", "status", "--short", "--branch"], cwd=WORKDIR)
    clone_status = "READY" if rc == 0 and (WORKDIR / ".git").exists() else "FAILED"
    mo.vstack([
        mo.md(f"**Checkout:** {clone_status}"),
        mo.code(out[-5000:] or "No output")
    ])
    return WORKDIR, run, clone_status

@app.cell
def _(WORKDIR, clone_status, mo, run):
    import pathlib, subprocess, json, os, sys
    if clone_status != "READY":
        report = {"status": "BLOCKED", "reason": "Repository checkout failed"}
    else:
        guide = WORKDIR / "vendor/openmontage/AGENT_GUIDE.md"
        submodule = (WORKDIR / "vendor/openmontage").exists()
        guide_ok = guide.exists()
        rc, git_sub = run(["git", "submodule", "status"], cwd=WORKDIR)
        report = {
            "status": "READY" if submodule and guide_ok else "INCOMPLETE",
            "branch": "feat/bamo-openmontage-autonomous-studio",
            "openmontage_directory_present": submodule,
            "agent_guide_present": guide_ok,
            "submodules": git_sub[-3000:],
            "note": "This validates the upstream checkout only; it does not claim a finished render."
        }
    mo.md("## 2. Verify OpenMontage source")
    mo.json(report)
    return (report,)

@app.cell
def _(mo):
    import subprocess, json, os, sys
    gpu = {"torch_available": False, "cuda_available": False, "gpu_name": None, "vram_gb": None}
    try:
        import torch
        gpu["torch_available"] = True
        gpu["cuda_available"] = bool(torch.cuda.is_available())
        if gpu["cuda_available"]:
            gpu["gpu_name"] = torch.cuda.get_device_name(0)
            gpu["vram_gb"] = round(torch.cuda.get_device_properties(0).total_memory / (1024**3), 1)
    except Exception as e:
        gpu["torch_error"] = str(e)
    try:
        p = subprocess.run(["nvidia-smi"], text=True, stdout=subprocess.PIPE,
                           stderr=subprocess.STDOUT, timeout=20)
        gpu["nvidia_smi"] = p.stdout[:5000]
    except Exception as e:
        gpu["nvidia_smi_error"] = str(e)
    mo.md("## 3. GPU availability")
    mo.json(gpu)
    return (gpu,)

@app.cell
def _(WORKDIR, clone_status, mo, report):
    import subprocess, sys, pathlib
    checks = {}
    if clone_status == "READY":
        for name, cmd in {
            "python": [sys.executable, "--version"],
            "ffmpeg": ["ffmpeg", "-version"],
            "node": ["node", "--version"],
            "npm": ["npm", "--version"],
        }.items():
            try:
                p = subprocess.run(cmd, cwd=WORKDIR, text=True, stdout=subprocess.PIPE,
                                   stderr=subprocess.STDOUT, timeout=20)
                checks[name] = {"available": p.returncode == 0, "output": p.stdout.splitlines()[0] if p.stdout else ""}
            except Exception as e:
                checks[name] = {"available": False, "output": str(e)}
    mo.md("## 4. Runtime preflight")
    mo.json(checks)
    mo.md("""
    ### Important production gate

    The current repository runner contains a provisional FFmpeg composition path and explicitly
    says it does not yet execute every OpenMontage stage-director skill. This notebook therefore
    stops at verified environment preparation. It will not label a placeholder composition as
    a professional OpenMontage render, and it will not upload anything to YouTube.
    """)
    return (checks,)

if __name__ == "__main__":
    app.run()
