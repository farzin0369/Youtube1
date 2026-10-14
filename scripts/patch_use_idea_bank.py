#!/usr/bin/env python3
"""Prefer curated idea bank before live LLM Shorts generation."""
from __future__ import annotations

from pathlib import Path

TARGET = Path(__file__).resolve().parents[1] / "app" / "spiritual_shorts.py"


def main() -> int:
    text = TARGET.read_text(encoding="utf-8")
    if "next_bank_idea" in text:
        print("PATCH_NOOP")
        return 0

    needle = 'def generate_shorts_content(history: dict[str, Any]) -> dict[str, Any]:\n    """Generate one short and reject weak, generic, duplicated or mismatched drafts."""\n    recent = history.get("recent", []) if isinstance(history, dict) else []\n'
    insert = (
        'def generate_shorts_content(history: dict[str, Any]) -> dict[str, Any]:\n'
        '    """Generate one short and reject weak, generic, duplicated or mismatched drafts."""\n'
        '    # Prefer a curated, pre-validated idea when available so daily production\n'
        '    # does not depend on non-deterministic cloud model quality.\n'
        '    try:\n'
        '        from app.idea_bank import next_bank_idea\n'
        '        bank_item = next_bank_idea(history if isinstance(history, dict) else {})\n'
        '        if bank_item is not None:\n'
        '            LOGGER.info(\n'
        '                "using curated idea bank id=%s topic=%r",\n'
        '                bank_item.get("idea_id"),\n'
        '                bank_item.get("topic"),\n'
        '            )\n'
        '            return bank_item\n'
        '    except Exception as exc:  # bank is optional; fall through to live generation\n'
        '        LOGGER.warning("idea bank unavailable (%s); falling back to live generation", type(exc).__name__)\n'
        '    recent = history.get("recent", []) if isinstance(history, dict) else []\n'
    )
    if needle not in text:
        raise SystemExit("PATCH_FAIL: generate_shorts_content header not found")
    text = text.replace(needle, insert, 1)
    compile(text, str(TARGET), "exec")
    TARGET.write_text(text, encoding="utf-8")
    print("PATCH_APPLIED use idea bank")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
