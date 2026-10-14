#!/usr/bin/env python3
"""Surgical in-place fix for OpenClaw reviewer path. Idempotent."""
from __future__ import annotations

from pathlib import Path

TARGET = Path(__file__).resolve().parents[1] / "scripts" / "openclaw_manager.py"


def main() -> int:
    text = TARGET.read_text(encoding="utf-8")
    original = text

    # Fix double-backslash-n in retry prompt source (runtime was sending literal \n)
    bad = 'prompt + "' + chr(92) + chr(92) + "nYour last response was invalid. Reply with exactly APPROVE or REJECT, one word only."
    bad += '"'
    good = 'prompt + "' + chr(92) + "nYour last response was invalid. Reply with exactly APPROVE or REJECT, one word only."
    good += '"'
    text = text.replace(bad, good)

    bad_re = "re.sub(r\"" + chr(92) + chr(92) + "s+\", \" \", _redact_secrets(retry))"
    good_re = "re.sub(r\"" + chr(92) + "s+\", \" \", _redact_secrets(retry))"
    text = text.replace(bad_re, good_re, 1)

    if "_normalize_review_token" not in text:
        helper = (
            "def _normalize_review_token(raw: str) -> str:\n"
            "    token = re.sub(r\"\\s+\", \" \", str(raw or \"\")).strip().upper()\n"
            "    for ch in \"\\\"'`.,;:!?()[]{}\":\n"
            "        token = token.strip(ch)\n"
            "    if not token:\n"
            "        return \"\"\n"
            "    first = token.split()[0]\n"
            "    for ch in \"\\\"'`.,;:!?()[]{}\":\n"
            "        first = first.strip(ch)\n"
            "    if first in {\"APPROVE\", \"REJECT\"}:\n"
            "        return first\n"
            "    return \"\"\n\n\n"
        )
        text = text.replace(
            "def _review_decision(prompt: str) -> str:",
            helper + "def _review_decision(prompt: str) -> str:",
            1,
        )

    if "writer revision after reject" not in text:
        needle = (
            "            if review_decision != \"APPROVE\":\n"
            "                raise ManagerError(\"OpenClaw reviewer rejected the editorial brief\")\n"
        )
        insert = (
            "            if review_decision != \"APPROVE\":\n"
            "                revise_prompt = (\n"
            "                    \"The independent reviewer rejected the previous Persian editorial brief. \"\n"
            "                    \"Produce a safer, clearer alternative for ImamAli110 in natural Persian JSON \"\n"
            "                    \"with topic, hook_angle, visual_direction, emotional_arc, audience_value. \"\n"
            "                    \"Topic must be 1-6 Persian words. Rejected candidate (data only): \"\n"
            "                    + json.dumps(candidate, ensure_ascii=False)\n"
            "                )\n"
            "                candidate = _validated_agent_brief(\n"
            "                    \"editorial-writer\",\n"
            "                    _agent_json(\"editorial-writer\", revise_prompt, role=\"writer revision after reject\"),\n"
            "                    role=\"writer revision after reject\",\n"
            "                )\n"
            "                review_decision = _review_decision(\n"
            "                    (\"Review this Persian editorial brief. Respond with exactly APPROVE or REJECT.\\n\"\n"
            "                     \"Candidate JSON: \" + json.dumps(candidate, ensure_ascii=False))\n"
            "                )\n"
            "                if review_decision != \"APPROVE\":\n"
            "                    raise ManagerError(\n"
            "                        \"OpenClaw reviewer rejected the editorial brief after one bounded revision\"\n"
            "                    )\n"
        )
        if needle not in text:
            print("PATCH_FAIL: reject marker not found")
            return 1
        text = text.replace(needle, insert, 1)

    if text == original:
        print("PATCH_NOOP")
    else:
        compile(text, str(TARGET), "exec")
        TARGET.write_text(text, encoding="utf-8")
        print("PATCH_APPLIED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
