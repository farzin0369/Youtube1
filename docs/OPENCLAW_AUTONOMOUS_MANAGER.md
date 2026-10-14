# OpenClaw Autonomous YouTube Manager

## Mission

Make OpenClaw the supervisory AI for the ImamAli110 Persian channel. OpenClaw should coordinate specialist agent runs, while deterministic Python modules remain responsible for media rendering, validation, YouTube OAuth, scheduling, and bounded comment replies. The system must prefer quality and integrity over posting at any cost. Million-view performance is a goal, never a promise.

## Current verified boundary

- `.github/workflows/openclaw-smoke-test.yml` originally installed the CLI and ran `openclaw --help` only. That proves CLI startup, not an authenticated model completion, a live Gateway, agent orchestration, or YouTube publishing.
- `.github/workflows/daily_run.yml` is scheduled for 14:30 UTC (18:00 Tehran), but GitHub-hosted runners are ephemeral. A workflow run cannot truthfully be described as a persistent, always-on Gateway.
- The content pipeline already generates Persian Shorts, uses four scene-specific vertical Pexels clips, runs pre-upload media QA, and schedules YouTube through the existing OAuth client.
- The Python LLM provider chain is cloud-only: Groq first, then an explicitly configured OpenAI-compatible cloud endpoint. It has no local Ollama fallback.
- MoneyPrinterTurbo is an optional rendering engine, not a guarantee of cinematic footage. The current MPT test creates abstract animations and must not be described as high-quality live-action footage.

## Target architecture

1. **OpenClaw supervisor**: on each production run, use an authenticated cloud model to create a temporary coordinated team (coordinator, researcher, writer, reviewer), validate structured outputs, and pass a sanitized editorial brief to the Shorts pipeline.
2. **Research/idea specialist**: choose one original, audience-relevant topic and a specific first-three-second hook; do not imitate any creator's distinctive style.
3. **Script specialist**: create natural Persian narration and title/description candidates consistent with the channel's source and safety policy.
4. **Production specialist**: select the configured production engine (current Python/FFmpeg/Pexels pipeline or MoneyPrinterTurbo when its dependencies and media sources are available). Do not silently substitute abstract clips for real footage.
5. **Quality reviewer**: verify media metadata, vertical format, audio/caption synchronization, scene relevance, legibility, duration, source credits, and policy compliance. Failed gates block upload.
6. **Release specialist**: call the existing deterministic uploader only after QA passes; default to private drafts during initial validation. Public scheduled publishing requires explicit workflow input or the existing scheduled production policy.
7. **Self-healing specialist**: classify failures from redacted logs, make only narrowly scoped changes on a dedicated branch, run regression tests, and propose a pull request. It must not rewrite secrets, bypass QA, disable tests, or automatically merge risky fixes.

## Cloud model policy

- Primary provider: Groq via `GROQ_API_KEY` when configured.
- OpenClaw-native fallback: OpenAI via `OPENAI_API_KEY` and `openai/gpt-4.1-mini`; this fallback can incur API charges.
- Optional cloud fallback: `LLM_BASE_URL`, `LLM_API_KEY`, and `LLM_MODEL` together.
- Never start Ollama or another local model.
- If no cloud provider is configured or all cloud providers fail, fail closed before upload and explain the missing configuration without printing secret values.
- OpenClaw itself must also be configured for a cloud provider; a Python LLM key alone does not configure OpenClaw.

## Autonomy and guardrails

Allowed without approval: topic ideation, script drafting, media retrieval, rendering, deterministic QA, sanitized diagnosis, bounded retries, and non-destructive test runs.

Require explicit authorization or a protected workflow input: public release during manual runs, changing GitHub secrets/permissions, deleting resources, merging code, disabling a quality gate, and changing the channel's safety policy.

Self-healing rules:
- classify and redact errors before an agent sees them;
- allow at most one retry per transient stage and a bounded repair attempt per failure;
- apply code repairs only on a non-default branch;
- run focused tests and the full regression suite after code changes;
- revert or stop if the tests fail;
- never print credentials or include raw environment dumps in artifacts;
- do not repeat uploads or replies when a prior result is uncertain; verify IDs and use an idempotency ledger.

## Acceptance gates

A change is not complete merely because `openclaw --help` succeeds. Required evidence, reported separately:

1. Cloud provider configuration is detected without displaying the key.
2. A real OpenClaw model completion succeeds in CI.
3. Specialist tasks produce validated structured outputs.
4. Regression tests pass.
5. A video file and QA report exist and pass all deterministic gates.
6. A private YouTube upload returns a real video ID before any public scheduling is enabled.
7. A scheduled release is verified by its actual YouTube video ID/status; workflow success alone is insufficient.
8. Recovery tests demonstrate that a simulated provider outage fails safely and does not invoke a local model.

## Delivery status

- Implemented in the feature branch: cloud-only Python provider chain, Groq/OpenAI model selection, temporary OpenClaw specialist team, validated editorial brief handoff into Shorts generation, bounded cloud-based comment moderation, secret-safe health reporting, and a self-healing job that can propose a draft PR after a regression-tested source-only repair.
- Verified so far: the full repository self-test completed successfully on an earlier revision of this branch. The cloud integration job intentionally fails closed when neither `GROQ_API_KEY` nor `OPENAI_API_KEY` is available; no live model completion, video upload, or public release has been proven by that failure.
- Still required before production activation: a successful cloud-model smoke test, a successful private YouTube upload with a real video ID, and a review of the generated video quality. Keep the branch separate until those checks pass.
- MoneyPrinterTurbo remains optional. The existing MPT workflow currently makes abstract test visuals, so it must not be selected as the production engine until it can produce scene-matched real footage and pass the same QA gates.

## Reporting rule

Always distinguish `configured`, `tested`, `generated`, `uploaded privately`, and `published publicly`. Never claim an upload or view count without a real platform response.
