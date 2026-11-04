from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "bamo_autopilot_continuous.yml"


def test_autopilot_preview_is_branch_scoped_read_only_and_non_publishing():
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "contents: read" in text
    assert "ref: ${{ github.ref }}" in text
    assert 'BAMO_AUTOPILOT_PUBLISH: "false"' in text
    assert "git push" not in text
    assert "YOUTUBE_CLIENT_SECRET" not in text
    assert "YOUTUBE_REFRESH_TOKEN" not in text
