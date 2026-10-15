"""Normalize Persian text so free TTS engines pronounce more clearly."""
from __future__ import annotations

import re

_ARABIC_YE = "\u064a"  # ي
_PERSIAN_YE = "\u06cc"  # ی
_ARABIC_KE = "\u0643"  # ك
_PERSIAN_KE = "\u06a9"  # ک
_ZWNJ = "\u200c"
_TATWEEL = "\u0640"

# Spoken-friendly replacements (literary → clearer oral forms for TTS)
_REPLACEMENTS: list[tuple[str, str]] = [
    # oral-disambig-v1
    ("کارت را", "کار تو را"),
    ("کارت ", "کار تو "),
    ("کارِت", "کار تو"),
    ("بی معنا", "بی معنی"),
    ("دل سپاری", "سپردن دل"),
    ("می‌تواند", "می تواند"),
    ("می‌آورد", "می آورد"),
    ("می‌کند", "می کند"),
    ("می‌شود", "می شود"),
    ("می‌گیری", "می گیری"),
    ("می‌گیرد", "می گیرد"),
    ("می‌بینم", "می بینم"),
    ("می‌بیند", "می بیند"),
    ("بی‌معنا", "بی معنا"),
    ("دل‌سپردن", "دل سپردن"),
    ("سبک‌تر", "سبک تر"),
    ("نمی‌شود", "نمی شود"),
    ("نمی‌کند", "نمی کند"),
]


def normalize_for_tts(text: str) -> str:
    """Prepare Persian for Edge/Piper: letters, spacing, pause punctuation."""
    s = str(text or "")
    s = s.replace(_ARABIC_YE, _PERSIAN_YE).replace(_ARABIC_KE, _PERSIAN_KE)
    s = s.replace(_TATWEEL, "")
    # unify ZWNJ forms of mi-
    s = re.sub(rf"می{_ZWNJ}+", "می\u200c", s)
    for src, dst in _REPLACEMENTS:
        s = s.replace(src, dst)
    # strip leftover ZWNJ that often confuses weak phonemizers
    s = s.replace(_ZWNJ, "\u200c")  # keep single canonical
    # Prefer explicit space instead of ZWNJ for free TTS (clearer segmentation)
    s = s.replace("\u200c", " ")
    s = s.replace("،", "، ").replace("؟", "؟ ").replace("!", "! ")
    s = re.sub(r"\s+", " ", s).strip()
    # remove space before punctuation
    s = re.sub(r"\s+([،؟!.])", r"\1", s)
    return s
