from pathlib import Path
import subprocess
import sys


def test_daily_health_report_supports_direct_execution_from_repository_root():
    repository_root = Path(__file__).resolve().parents[1]
    script = repository_root / "scripts" / "daily_health_report.py"
    result = subprocess.run(
        [sys.executable, str(script), "--help"],
        cwd=repository_root,
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "--test-status" in result.stdout
