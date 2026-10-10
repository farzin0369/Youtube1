"""Write a privacy-safe daily health report for GitHub Actions artifacts."""
from __future__ import annotations

import argparse
import json
import os
import platform
import subprocess
from pathlib import Path

from app.channel_ops import channel_health
from app.utils import utc_now_iso


def _git_sha() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True, timeout=5).strip()
    except Exception:
        return os.environ.get("GITHUB_SHA", "unknown")


def _recent_changes() -> list[str]:
    try:
        raw = subprocess.check_output(
            ["git", "log", "--since=24 hours", "--pretty=format:%h %s", "-n", "30"],
            text=True, timeout=5,
        )
        return [line.strip() for line in raw.splitlines() if line.strip()]
    except Exception:
        return []


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--test-status", default="unknown")
    args = parser.parse_args()
    report_dir = Path("output")
    report_dir.mkdir(parents=True, exist_ok=True)
    health = channel_health()
    data = {
        "created_at": utc_now_iso(),
        "git_sha": _git_sha(),
        "python": platform.python_version(),
        "test_status": args.test_status,
        "channel_health": health,
        "recent_changes": _recent_changes(),
        "secrets_present": {
            "youtube_oauth": all(os.environ.get(k) for k in ("YOUTUBE_CLIENT_ID", "YOUTUBE_CLIENT_SECRET", "YOUTUBE_REFRESH_TOKEN")),
            "qwen": bool(os.environ.get("QWEN_API_KEY") or os.environ.get("DASHSCOPE_API_KEY")),
            "openai": bool(os.environ.get("OPENAI_API_KEY")),
        },
    }
    (report_dir / "daily_health_report.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [
        "# ImamAli110 — Daily Health Report",
        "",
        f"- Created: {data['created_at']}",
        f"- Commit: `{data['git_sha']}`",
        f"- Python: {data['python']}",
        f"- Unit tests: **{args.test_status}**",
        f"- YouTube OAuth/API: **{'OK' if health.get('youtube') else 'FAILED'}**",
        f"- Qwen configured: **{'yes' if health.get('qwen_configured') else 'no'}**",
        f"- OpenAI configured: **{'yes' if health.get('openai_configured') else 'no'}**",
        "",
        "## Channel status",
        "",
        f"- Channel URL: {health.get('channel', 'not configured')}",
        f"- Channel title: {health.get('channel_title', 'unavailable')}",
        "",
        "## Changes in the last 24 hours",
        "",
        *([f"- `{line}`" for line in data["recent_changes"]] or ["- No repository commits found in the last 24 hours."]),
        "",
        "## Notes",
        "",
        "- This report does not include credentials or tokens.",
        "- GitHub-hosted runners have no CUDA GPU; this is a health/test report, not proof of a successful Colab GPU render.",
        "- Public publishing remains disabled unless explicitly enabled in channel configuration.",
    ]
    stats = health.get("statistics")
    if isinstance(stats, dict):
        lines += ["", "## Public channel counters", ""]
        for key in ("viewCount", "subscriberCount", "videoCount"):
            if key in stats:
                lines.append(f"- {key}: {stats[key]}")
    if health.get("youtube_error"):
        lines += ["", "## Error", "", f"`{health['youtube_error']}`"]
    (report_dir / "daily_health_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print((report_dir / "daily_health_report.md").read_text(encoding="utf-8"))
    return 0 if health.get("youtube") else 1


if __name__ == "__main__":
    raise SystemExit(main())
