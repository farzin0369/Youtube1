#!/usr/bin/env python3
from pathlib import Path
TARGET = Path(__file__).resolve().parents[1] / "app" / "youtube_client.py"
text = TARGET.read_text(encoding="utf-8")
old = '''                result["thumbnail_error"] = str(te)
                result.update({"ok": False, "error": "Custom thumbnail upload failed; video was left private."})
'''
new = '''                result["thumbnail_error"] = str(te)
                # Private drafts remain usable even when daily thumbnail quota is exhausted.
                if privacy == "private":
                    result["thumbnail_set"] = False
                    result["ok"] = True
                    result["warning"] = "thumbnail_quota_or_error; private video kept without custom thumb"
                else:
                    result.update({"ok": False, "error": "Custom thumbnail upload failed; video was left private."})
'''
if old not in text:
    raise SystemExit("FAIL match")
TARGET.write_text(text.replace(old, new, 1), encoding="utf-8")
print("OK")
