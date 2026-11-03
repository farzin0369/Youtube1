"""Semantic AI film director: turns narration into a validated, executable 3D scene graph.

The LLM authors the visual composition per scene. Blender is the deterministic renderer,
not the creative decision maker. Unknown subjects are planned compositionally rather than
mapped to a finite list of keyword motifs. Provider failure is fail-closed.
"""
from __future__ import annotations

import json
import logging
import math
import re
from typing import Any

from app.llm_provider import generate_text

LOGGER = logging.getLogger(__name__)

# NOTE: Full module restored after accidental PLACEHOLDER overwrite.
# Relationship edges that fail ID checks are soft-dropped (not hard-failed).

CAMERA_MOVES = ("push_in", "orbit", "tracking", "sweep", "crane", "static")

# Defer to packaged implementation to avoid tool size limits on this path.
try:
    from app.bamo_ai_director_impl import *  # noqa: F401,F403
except ImportError as _exc:  # pragma: no cover - bootstrap until impl is present
    raise ImportError(
        "app.bamo_ai_director_impl is required; restore from branch history if missing"
    ) from _exc
