"""Provider-agnostic text generation for the daily pipeline.

No paid subscription is required. Providers are tried in this order:

1. ``GROQ_API_KEY`` — free tier of Groq (OpenAI-compatible).
2. ``LLM_BASE_URL`` + ``LLM_API_KEY`` — any OpenAI-compatible gateway
   (OpenRouter, Together, DeepInfra, a self-hosted vLLM, ...).
3. Local Ollama on ``OLLAMA_BASE_URL`` — always available, no key.

Every provider failure is isolated: a rate-limited or unreachable cloud
provider falls through to the next one instead of killing the run.
Credentials are never logged.
"""

from __future__ import annotations

import json
import logging
import time
import urllib.error
import urllib.request
from typing import Any, Callable

from app.utils import env

GROQ_BASE_URL = "https://api.groq.com/openai/v1"
DEFAULT_GROQ_MODEL = "openai/gpt-oss-20b"
DEFAULT_LOCAL_MODEL = "qwen2.5:3b"

RETRYABLE_STATUS = {408, 409, 425, 429, 500, 502, 503, 504}


class LLMUnavailable(RuntimeError):
    """Raised when no configured provider could return a usable completion."""


def _groq_config() -> tuple[str, str, str] | None:
    key = (env("GROQ_API_KEY") or "").strip()
    if not key:
        return None
    return GROQ_BASE_URL, key, (env("GROQ_MODEL") or DEFAULT_GROQ_MODEL).strip()


def _generic_config() -> tuple[str, str, str] | None:
    base = (env("LLM_BASE_URL") or "").strip()
    key = (env("LLM_API_KEY") or "").strip()
    model = (env("LLM_MODEL") or "").strip()
    if not (base and key and model):
        return None
    return base.rstrip("/"), key, model


def _chat_completions(
    base_url: str,
    api_key: str,
    model: str,
    system: str,
    prompt: str,
    *,
    max_tokens: int,
    temperature: float,
    json_mode: bool,
    timeout: float,
) -> str:
    """One OpenAI-compatible chat completion with bounded retry on transient errors."""
    body: dict[str, Any] = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        "temperature": temperature,
        "max_completion_tokens": max_tokens,
    }
    if json_mode:
        body["response_format"] = {"type": "json_object"}
    payload = json.dumps(body, ensure_ascii=False).encode("utf-8")
    last_error: Exception | None = None
    for attempt in range(3):
        request = urllib.request.Request(
            f"{base_url}/chat/completions",
            data=payload,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                result = json.loads(response.read().decode("utf-8"))
            choices = result.get("choices") or []
            if not choices:
                raise ValueError("provider returned no choices")
            content = ((choices[0].get("message") or {}).get("content")) or ""
            if not str(content).strip():
                raise ValueError("provider returned an empty completion")
            return str(content)
        except urllib.error.HTTPError as exc:
            last_error = RuntimeError(f"HTTP {exc.code}")
            if exc.code not in RETRYABLE_STATUS or attempt == 2:
                break
            try:
                retry_after = float(exc.headers.get("Retry-After", "0"))
            except (TypeError, ValueError):
                retry_after = 0.0
            time.sleep(min(8.0, max(float(2 ** attempt), retry_after, 1.0)))
        except (TimeoutError, urllib.error.URLError) as exc:
            last_error = exc
            if attempt == 2:
                break
            time.sleep(min(8.0, float(2 ** attempt)))
        except Exception as exc:  # malformed payload, empty completion, ...
            last_error = exc
            break
    raise LLMUnavailable(f"cloud provider failed ({type(last_error).__name__})") from last_error


def _ollama_call(
    system: str,
    prompt: str,
    *,
    max_tokens: int,
    temperature: float,
    json_mode: bool,
    timeout: float,
) -> str:
    from app.local_ai import ollama_available, ollama_generate

    if not ollama_available():
        raise LLMUnavailable("local Ollama is not running")
    model = (env("LOCAL_LLM_MODEL") or DEFAULT_LOCAL_MODEL).strip()
    return ollama_generate(
        prompt,
        system=system,
        model=model,
        format_json=json_mode,
        num_predict=max_tokens,
        temperature=temperature,
        timeout=timeout,
    )



def _cloudflare_call(
    system: str,
    prompt: str,
    *,
    max_tokens: int,
    temperature: float,
    json_mode: bool,
    timeout: float,
) -> str:
    """Call Cloudflare Workers AI on its free daily allocation."""
    account_id = (env("CLOUDFLARE_ACCOUNT_ID") or "").strip()
    token = (env("CLOUDFLARE_API_TOKEN") or "").strip()
    if not account_id or not token:
        raise LLMUnavailable("Cloudflare Workers AI credentials are not configured")
    model = (env("CLOUDFLARE_AI_MODEL") or "@cf/meta/llama-3.3-70b-instruct-fp8-fast").strip()
    url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run/{model}"
    user_prompt = prompt
    if json_mode:
        user_prompt += "\\nReturn only valid JSON, without markdown fences."
    payload = json.dumps({
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user_prompt},
        ],
        "max_tokens": max_tokens,
        "temperature": temperature,
    }, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        url, data=payload,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            result = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise LLMUnavailable(f"Cloudflare Workers AI failed (HTTP {exc.code})") from exc
    body = result.get("result") or {}
    content = body.get("response") or body.get("text") or ""
    if not str(content).strip():
        raise LLMUnavailable("Cloudflare Workers AI returned empty content")
    return str(content)


def provider_chain() -> list[tuple[str, Callable[..., str]]]:
    """Ordered provider candidates for the current environment.

    Prefer Groq when GROQ_API_KEY is configured; Cloudflare and generic
    OpenAI-compatible gateways are fallbacks. Credentials are never logged.
    """
    chain: list[tuple[str, Callable[..., str]]] = []
    groq = _groq_config()
    if groq:
        base, key, model = groq
        chain.append((
            f"groq:{model}",
            lambda system, prompt, **kw: _chat_completions(base, key, model, system, prompt, **kw),
        ))
    cf_token = (env("CLOUDFLARE_API_TOKEN") or "").strip()
    cf_account = (env("CLOUDFLARE_ACCOUNT_ID") or "").strip()
    if cf_token and cf_account:
        cf_model = (env("CLOUDFLARE_AI_MODEL") or "@cf/meta/llama-3.3-70b-instruct-fp8-fast").strip()
        chain.append((f"cloudflare:{cf_model}", _cloudflare_call))
    generic = _generic_config()
    if generic:
        base, key, model = generic
        chain.append((
            f"openai-compatible:{model}",
            lambda system, prompt, **kw: _chat_completions(base, key, model, system, prompt, **kw),
        ))
    # Production can explicitly forbid low-quality/local fallback models.
    require_cloud = (env("LLM_REQUIRE_CLOUD") or "").strip().lower() in {"1", "true", "yes", "on"}
    if not require_cloud:
        chain.append((f"ollama:{env('LOCAL_LLM_MODEL') or DEFAULT_LOCAL_MODEL}", _ollama_call))
    return chain

def generate_text(
    system: str,
    prompt: str,
    *,
    max_tokens: int = 1200,
    temperature: float = 0.6,
    json_mode: bool = False,
    timeout: float | None = None,
) -> tuple[str, str]:
    """Return ``(text, provider_name)`` from the first provider that answers.

    A failure in one provider only demotes it; the next candidate is tried.
    Raises :class:`LLMUnavailable` when every candidate fails.
    """
    logger = logging.getLogger(__name__)
    if timeout is None:
        try:
            timeout = max(30.0, min(900.0, float(env("LLM_TIMEOUT_SECONDS") or "180")))
        except (TypeError, ValueError):
            timeout = 180.0
    chain = provider_chain()
    # Report provider names only; never log keys, URLs containing credentials, or tokens.
    logger.info("LLM providers configured: %s", ", ".join(name for name, _ in chain))
    failures: list[str] = []
    for name, call in chain:
        try:
            provider_timeout = timeout
            if name.startswith("ollama:"):
                try:
                    provider_timeout = max(
                        30.0,
                        min(900.0, float(env("OLLAMA_TIMEOUT_SECONDS") or str(timeout))),
                    )
                except (TypeError, ValueError):
                    provider_timeout = timeout
            text = call(
                system,
                prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                json_mode=json_mode,
                timeout=provider_timeout,
            )
            if failures:
                logger.warning("fell back to %s after %s", name, ", ".join(failures))
            return text, name
        except Exception as exc:  # keep the chain alive; never log credentials
            failures.append(f"{name}:{type(exc).__name__}")
            logger.warning("provider %s unavailable (%s)", name, type(exc).__name__)
    raise LLMUnavailable("no LLM provider succeeded (" + ", ".join(failures) + ")")
