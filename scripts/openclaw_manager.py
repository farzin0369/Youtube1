#!/usr/bin/env python3
"""OpenClaw editorial supervisor for the Persian Shorts pipeline.

Each workflow run provisions an isolated native OpenClaw team (coordinator,
researcher, writer, reviewer), starts a temporary Gateway, and obtains a
validated editorial brief through role-specific agent turns. The team and
Gateway live only for the current job; GitHub-hosted runners are ephemeral.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MODEL = "cloudflare/@cf/meta/llama-3.1-8b-instruct-fast"
BRIEF_PATH = ROOT / "state" / "openclaw_brief.json"
TEAM_IDS = ("editorial-coordinator", "editorial-researcher", "editorial-writer", "editorial-reviewer")
