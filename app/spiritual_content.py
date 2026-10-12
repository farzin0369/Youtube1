"""Source-conscious Persian spiritual and personal-growth script generation.

A free local model cannot emit an 800-word Persian script as a single JSON
document: it truncates, loses the schema, or pads the text with filler. The
generator therefore splits the job into

1. one small outline call (title, description, tags, section headings), and
2. one bounded call per section, each with its own word budget and repair pass,

and only then runs the assembled script through the publication quality gates.
Every provider failure is contained by :mod:`app.llm_provider`.
"""
from __future__ import annotations

import json
import logging
import re
from difflib import SequenceMatcher
from typing import Any

from app.llm_provider import generate_text
from app.utils import load_content_policy

LOGGER = logging.getLogger(__name__)

TITLE_PREFIX = "Imam Ali ✨ "
SECTION_COUNT = 6
TARGET_WORDS_PER_SECTION = 130
MIN_TOTAL_WORDS = 650
MAX_TOTAL_WORDS = 900
