#!/usr/bin/env python3
"""Prefer curated idea bank before live LLM Shorts generation when USE_IDEA_BANK=1."""
from __future__ import annotations

from pathlib import Path

TARGET = Path(__file__).resolve().parents[1] / "app" / "spiritual_shorts.py"


def main() -> int:
    text = TARGET.read_text(encoding="utf-8")
    # Replace any previous bank-first block with env-gated version.
    old_block = '''    # Prefer a curated, pre-validated idea when available so daily production\n    # does not depend on non-deterministic cloud model quality.\n    try:\n        from app.idea_bank import next_bank_idea\n        bank_item = next_bank_idea(history if isinstance(history, dict) else {})\n        if bank_item is not None:\n            LOGGER.info(\n                "using curated idea bank id=%s topic=%r",\n                bank_item.get("idea_id"),\n                bank_item.get("topic"),\n            )\n            return bank_item\n    except Exception as exc:  # bank is optional; fall through to live generation\n        LOGGER.warning("idea bank unavailable (%s); falling back to live generation", type(exc).__name__)\n'''
    new_block = '''    # Prefer curated idea bank when explicitly enabled (production).\n    # Tests leave USE_IDEA_BANK unset so live generation path stays covered.\n    if (os.getenv("USE_IDEA_BANK") or "").strip().lower() in {"1", "true", "yes"}:\n        try:\n            from app.idea_bank import next_bank_idea\n            bank_item = next_bank_idea(history if isinstance(history, dict) else {})\n            if bank_item is not None:\n                LOGGER.info(\n                    "using curated idea bank id=%s topic=%r",\n                    bank_item.get("idea_id"),\n                    bank_item.get("topic"),\n                )\n                return bank_item\n        except Exception as exc:  # bank is optional; fall through to live generation\n            LOGGER.warning("idea bank unavailable (%s); falling back to live generation", type(exc).__name__)\n'''
    if "USE_IDEA_BANK" in text and "os.getenv(\"USE_IDEA_BANK\")" in text:
        print("PATCH_NOOP")
        return 0
    if old_block in text:
        text = text.replace(old_block, new_block, 1)
    elif "next_bank_idea" not in text:
        needle = 'def generate_shorts_content(history: dict[str, Any]) -> dict[str, Any]:\n    """Generate one short and reject weak, generic, duplicated or mismatched drafts."""\n    recent = history.get("recent", []) if isinstance(history, dict) else []\n'
        insert = (
            'def generate_shorts_content(history: dict[str, Any]) -> dict[str, Any]:\n'
            '    """Generate one short and reject weak, generic, duplicated or mismatched drafts."""\n'
            + new_block
            + '    recent = history.get("recent", []) if isinstance(history, dict) else []\n'
        )
        if needle not in text:
            raise SystemExit("PATCH_FAIL: header not found")
        text = text.replace(needle, insert, 1)
    else:
        # Already has bank but not gated — force replace the try block loosely
        raise SystemExit("PATCH_FAIL: unexpected bank wiring; inspect spiritual_shorts.py")
    if "import os" not in text.split("def generate_shorts_content")[0]:
        # os is already imported at module level in this file
        pass
    compile(text, str(TARGET), "exec")
    TARGET.write_text(text, encoding="utf-8")
    print("PATCH_APPLIED gated idea bank")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
