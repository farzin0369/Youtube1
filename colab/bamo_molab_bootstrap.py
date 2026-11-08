import marimo

__generated_with = "0.19.0"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo
    mo.md("""
    # BAMO × OpenMontage — molab bootstrap

    این نوت‌بوک برای آماده‌سازی محیط اجرای آزمایشی BAMO در molab است.
    فقط روی فضای موقت همین نشست کار می‌کند؛ به شاخه اصلی GitHub چیزی نمی‌نویسد.
    """)
    return (mo,)


@app.cell
def _(mo):
    import os, subprocess, sys, json, shutil, pathlib, textwrap
    repo_dir = pathlib.Path("/content/Youtube1")
    if not repo_dir.exists():
        repo_dir = pathlib.Path.cwd() / "Youtube1"
    mo.md("### مرحله ۱ — بررسی محیط و GPU")
    return json, mo, os, pathlib, repo_dir, shutil, subprocess, sys, textwrap


@app.cell
def _(mo, subprocess, sys):
    def run_cmd(args, cwd=None, timeout=900):
        p = subprocess.run(args, cwd=cwd, text=True, stdout=subprocess.PIPE,
                           stderr=subprocess.STDOUT, timeout=timeout)
        return p.returncode, p.stdout[-12000:]
    py = sys.executable
    code, gpu = run_cmd([py, "-c", "import torch; print('torch',torch.__version__); print('cuda_available',torch.cuda.is_available()); print('device',torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU')"])
    mo.output(code)
    mo.output(gpu)
    return (run_cmd,)


@app.cell
def _(mo, pathlib, repo_dir, run_cmd):
    mo.md("### مرحله ۲ — دریافت BAMO و زیرماژول OpenMontage")
    if not (repo_dir / ".git").exists():
        code, out = run_cmd(["git", "clone", "--branch", "feat/bamo-openmontage-autonomous-studio", "--depth", "1", "https://github.com/farzin0369/Youtube1.git", str(repo_dir)])
    else:
        code, out = run_cmd(["git", "status", "--short"], cwd=repo_dir)
    mo.output(out)
    if code == 0 and (repo_dir / ".gitmodules").exists():
        code2, out2 = run_cmd(["git", "submodule", "update", "--init", "--recursive", "--depth", "1"], cwd=repo_dir, timeout=1200)
        mo.output(out2)
    return


@app.cell
def _(mo, pathlib, repo_dir, run_cmd):
    mo.md("### مرحله ۳ — تشخیص موتور و دستورهای اجرا")
    if repo_dir.exists():
        for name in ["README.md", "package.json", "pyproject.toml", "requirements.txt", ".gitmodules"]:
            f = repo_dir / name
            if f.exists():
                mo.md(f"**{name}**")
                mo.output(f.read_text(errors="replace")[:6000])
        om = repo_dir / "vendor" / "openmontage"
        mo.md("**OpenMontage submodule:** " + ("دریافت شد" if (om / ".git").exists() or om.exists() else "پیدا نشد"))
        if (om / "package.json").exists():
            mo.output((om / "package.json").read_text(errors="replace")[:8000])
        if (om / "README.md").exists():
            mo.output((om / "README.md").read_text(errors="replace")[:8000])
    else:
        mo.output("مخزن دریافت نشد؛ خروجی مرحله قبل را بررسی کنید.")
    return


@app.cell
def _(mo):
    mo.md("""
    ### مرحله ۴ — نتیجه و اقدام بعدی

    این نسخه عمداً فقط محیط، دسترسی GPU، دریافت مخزن و ساختار OpenMontage را بررسی می‌کند.
    هیچ ویدئوی نمایشیِ جعلی تولید نمی‌کند و هیچ فایل یا شاخه‌ای در GitHub را تغییر نمی‌دهد.
    پس از تأیید نسخه موتور و دستور رسمی رندر، مرحله رندر واقعی 9:16 به همین نوت‌بوک اضافه می‌شود.
    """)
    return


if __name__ == "__main__":
    app.run()
