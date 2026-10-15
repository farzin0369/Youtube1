#!/usr/bin/env python3
from pathlib import Path
TARGET = Path(__file__).resolve().parents[1] / "scripts" / "openclaw_manager.py"
text = TARGET.read_text(encoding="utf-8")
if "USE_IDEA_BANK" in text and "idea-bank skip" in text:
    print("NOOP")
    raise SystemExit(0)
# Prepend early exit when idea bank is enabled
marker = "def main("
if "idea-bank skip" not in text:
    inject = '''
def _idea_bank_enabled() -> bool:
    import os
    return os.getenv("USE_IDEA_BANK", "").strip() in {"1", "true", "True", "yes"}

'''
    # find if main exists
    if "if __name__" in text and "_idea_bank_enabled" not in text:
        text = inject + text
        # wrap exit at start of main body - find first main definition
        import re
        m = re.search(r"(def main\([^)]*\)\s*->\s*[^:]+:\s*\n)", text)
        if m:
            pos = m.end()
            text = text[:pos] + "    if _idea_bank_enabled():  # idea-bank skip\n        print(\"OpenClaw skipped: USE_IDEA_BANK enabled\")\n        return 0\n" + text[pos:]
        else:
            # try without return type
            m2 = re.search(r"(def main\([^)]*\):\s*\n)", text)
            if m2:
                pos = m2.end()
                text = text[:pos] + "    if _idea_bank_enabled():  # idea-bank skip\n        print(\"OpenClaw skipped: USE_IDEA_BANK enabled\")\n        return 0\n" + text[pos:]
            else:
                raise SystemExit("no main")
compile(text, str(TARGET), "exec")
TARGET.write_text(text, encoding="utf-8")
print("SKIP_APPLIED")
