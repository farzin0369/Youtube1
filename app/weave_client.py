"""Opt-in Figma Weave API adapter for scene-matched image generation.

The Weave API is Enterprise-only. Never run a paid workflow unless explicitly enabled
and its estimated credit cost is within WEAVE_MAX_CREDIT_COST.
"""
from __future__ import annotations

import logging
import os
import time
from pathlib import Path
from typing import Any
from urllib.parse import quote

import requests

BASE_URL = "https://developer.api.weavy.ai/v1"
LOG = logging.getLogger(__name__)


class WeaveError(RuntimeError):
    """A safe, user-actionable Weave API error."""


def scene_prompt(narration: str, *, format_name: str = "shorts") -> str:
    """Create a concrete visual prompt grounded in the narrated scene."""
    narration = " ".join(str(narration or "").split())
    if not narration:
        raise ValueError("Weave scene narration must not be empty")
    ratio = "9:16 vertical" if format_name == "shorts" else "16:9 landscape"
    return (
        "Create one cinematic, photorealistic, narration-matched visual for a Persian "
        "spiritual reflection video. Visualize this scene literally and respectfully; "
        "no text, letters, logos, watermarks, religious figure depictions, or collage. "
        f"Composition: {ratio}; premium natural lighting, coherent visual storytelling. "
        f"Scene narration context: {narration}"
    )


class WeaveClient:
    def __init__(self, token: str | None = None, *, session: requests.Session | None = None):
        self.token = (token if token is not None else os.getenv("WEAVE_API_TOKEN", "")).strip()
        if not self.token:
            raise WeaveError("WEAVE_API_TOKEN is not configured")
        self.session = session or requests.Session()
        self.session.headers.update({
            "X-Figma-Token": self.token,
            "Accept": "application/json",
            "Content-Type": "application/json",
        })

    def _request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        try:
            response = self.session.request(
                method, f"{BASE_URL}{path}", timeout=(10, 45), **kwargs
            )
            response.raise_for_status()
            if not response.content:
                return {}
            data = response.json()
            if not isinstance(data, dict):
                raise WeaveError("Weave API returned an unexpected response shape")
            return data
        except requests.RequestException as exc:
            status = getattr(getattr(exc, "response", None), "status_code", None)
            if status in (401, 403):
                raise WeaveError(
                    "Weave authentication/permission failed; check Enterprise access and token."
                ) from None
            if status == 429:
                raise WeaveError("Weave rate limit reached; retry in a later run.") from None
            raise WeaveError(f"Weave API request failed ({status or type(exc).__name__}).") from None
        except ValueError:
            raise WeaveError("Weave API returned invalid JSON.") from None

    def list_tools(self) -> list[dict[str, str]]:
        return [
            item for item in self._request("GET", "/tools").get("tools", [])
            if isinstance(item, dict) and item.get("id")
        ]

    def inspect_tool(self, tool_id: str) -> dict[str, Any]:
        return self._request("GET", f"/tools/{quote(tool_id, safe='')}/inspect")

    @staticmethod
    def _inputs_for_prompt(inspect: dict[str, Any], prompt: str) -> list[dict[str, Any]]:
        inputs = inspect.get("inputs")
        if not isinstance(inputs, list) or not inputs:
            raise WeaveError("The selected Weave tool has no inspectable inputs.")
        result = []
        prompt_was_set = False
        for item in inputs:
            if not isinstance(item, dict) or not item.get("id") or not item.get("type"):
                raise WeaveError("Weave tool input schema is malformed.")
            name = " ".join(str(item.get("name") or "").lower().replace("_", " ").split())
            input_type = item["type"]
            if input_type == "string" and any(word in name for word in ("prompt", "scene", "description", "text", "query")):
                result.append({"id": item["id"], "value": {"type": "string", "value": prompt}})
                prompt_was_set = True
            elif item.get("default_value") is not None:
                result.append({"id": item["id"], "use_default": True})
            else:
                raise WeaveError(
                    f"Required Weave input '{item.get('name') or item['id']}' has no published default."
                )
        if not prompt_was_set:
            raise WeaveError(
                "This Weave tool has no string input named prompt/scene/description/text/query; "
                "rename its prompt input or publish a compatible tool."
            )
        return result

    def generate_scene_image(
        self, *, tool_id: str, prompt: str, output_dir: Path,
        format_name: str = "shorts",
    ) -> Path:
        """Estimate cost, enforce explicit opt-in, run one workflow, and download its first image."""
        enabled = os.getenv("WEAVE_AUTO_RUN", "").strip().lower() in {"1", "true", "yes"}
        if not enabled:
            raise WeaveError("Weave generation is disabled; set WEAVE_AUTO_RUN=true to opt in.")
        inspect = self.inspect_tool(tool_id)
        tool_version = inspect.get("tool_version")
        payload: dict[str, Any] = {"inputs": self._inputs_for_prompt(
            inspect, scene_prompt(prompt, format_name=format_name)
        )}
        if isinstance(tool_version, int):
            payload["tool_version"] = tool_version

        cost_data = self._request("POST", f"/tools/{quote(tool_id, safe='')}/cost", json=payload)
        cost = cost_data.get("estimated_credit_cost")
        if cost is None:
            raise WeaveError("Weave could not estimate this run's cost; refusing to spend unknown credits.")
        try:
            max_cost = float(os.getenv("WEAVE_MAX_CREDIT_COST", "0"))
        except ValueError:
            max_cost = 0
        if max_cost <= 0 or float(cost) > max_cost:
            raise WeaveError(
                f"Weave estimated {cost} credits; WEAVE_MAX_CREDIT_COST must be set to an explicit "
                "positive limit at least this high. No run was started."
            )

        started = self._request("POST", f"/tools/{quote(tool_id, safe='')}/runs", json=payload)
        runs = started.get("runs") or []
        if not runs or not runs[0].get("id"):
            raise WeaveError("Weave did not return a run ID.")
        run_id = str(runs[0]["id"])
        deadline = time.monotonic() + max(30, int(os.getenv("WEAVE_POLL_TIMEOUT_SECONDS", "600")))
        terminal: dict[str, Any] | None = None
        while time.monotonic() < deadline:
            state = self._request(
                "GET", f"/tools/{quote(tool_id, safe='')}/runs",
                params={"run_ids": run_id},
            )
            rows = state.get("runs") or []
            if rows:
                status = rows[0].get("status")
                if status in {"completed", "failed", "canceled"}:
                    terminal = rows[0]
                    break
            time.sleep(max(1, min(15, int(os.getenv("WEAVE_POLL_INTERVAL_SECONDS", "5")))))
        if terminal is None:
            raise WeaveError(f"Weave run {run_id} timed out; check the Weave workspace for its status.")
        if terminal.get("status") != "completed":
            error = terminal.get("error") or {}
            raise WeaveError(f"Weave run {terminal.get('status')}: {str(error.get('message') or 'no details')[:180]}")

        assets = [
            asset for output in (terminal.get("outputs") or [])
            for asset in (output.get("assets") or [])
            if isinstance(asset, dict) and asset.get("type") == "image" and asset.get("url")
        ]
        if not assets:
            raise WeaveError("The selected Weave tool completed but returned no image asset.")
        url = str(assets[0]["url"])
        if not url.startswith("https://"):
            raise WeaveError("Weave returned a non-HTTPS asset URL; refusing download.")
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        # Asset URLs are separate CDN resources: do not forward the workspace API token.
        target = output_dir / f"weave_scene_{int(time.time() * 1000)}.img"
        try:
            response = requests.get(url, timeout=(10, 90), stream=True)
            response.raise_for_status()
            content_type = response.headers.get("Content-Type", "").split(";", 1)[0].lower()
            suffix = { "image/png": ".png", "image/jpeg": ".jpg", "image/webp": ".webp" }.get(content_type)
            if not suffix:
                raise WeaveError("Weave returned an unsupported image content type.")
            target = target.with_suffix(suffix)
            total = 0
            with target.open("wb") as stream:
                for chunk in response.iter_content(1024 * 1024):
                    if not chunk:
                        continue
                    total += len(chunk)
                    if total > 25 * 1024 * 1024:
                        raise WeaveError("Weave image exceeded the 25 MiB safety limit.")
                    stream.write(chunk)
            response.close()
            if total < 10_000:
                raise WeaveError("Weave image download was empty or incomplete.")
        except Exception:
            target.unlink(missing_ok=True)
            raise
        return target


def generate_scene_stills(
    prompts: list[str], output_dir: Path, *, format_name: str = "shorts"
) -> list[Path]:
    """Generate one still per prompt. Any failure returns no partial set (fail closed)."""
    tool_id = os.getenv("WEAVE_TOOL_ID", "").strip()
    if not tool_id or not prompts:
        return []
    client = WeaveClient()
    paths: list[Path] = []
    try:
        for index, prompt in enumerate(prompts):
            paths.append(client.generate_scene_image(
                tool_id=tool_id,
                prompt=prompt,
                output_dir=Path(output_dir) / f"scene_{index + 1:02d}",
                format_name=format_name,
            ))
    except Exception as exc:
        for path in paths:
            path.unlink(missing_ok=True)
        LOG.warning("Weave scene generation unavailable (%s); existing provider policy applies.", type(exc).__name__)
        return []
    return paths
