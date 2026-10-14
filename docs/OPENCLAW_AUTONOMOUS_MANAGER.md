# OpenClaw Autonomous YouTube Manager

## Mission

Make OpenClaw the supervisory AI for the ImamAli110 Persian channel. OpenClaw should coordinate specialist agent runs, while deterministic Python modules remain responsible for media rendering, validation, YouTube OAuth, scheduling, and bounded comment replies. The system must prefer quality and integrity over posting at any cost. Million-view performance is a goal, never a promise.

## Current verified boundary

- `.github/workflows/openclaw-smoke-test.yml` originally installed the CLI and ran `openclaw --help` only. That proves CLI startup, not an authenticated model completion, a live Gateway, agent orchestration, or YouTube publishing.
- `.github/workflows/daily_run.yml` is scheduled for 14:30 UTC (18:00 Tehran), but GitHub-hosted runners are ephemeral. A workflow run cannot truthfully be described as a persistent, always-on Gateway.
- The content pipeline already generates Persian Shorts, uses four scene-specific vertical Pexels clips, runs pre-upload media QA, and schedules YouTube through the existing OAuth client.
- The previous LLM provider chain silently fell back to local Ollama. This conflicts with the owner's explicit no-local-model requirement and is being removed.
- MoneyPrinterTurbo is an optional rendering engine, not a guarantee of cinematic footage. The current MPT test creates abstract animations and must not be described as high-quality live-action footage.

## Target architecture

1. **OpenClaw supervisor**: use an authenticated cloud model to inspect a run plan, delegate bounded specialist tasks, review their structured outputs, and produce a sanitized run report.
2. **Research/idea specialist**: choose one original, audience-relevant topic and a specific first-three-second hook; do not imitate any creator's distinctive style.
3. **Script specialist**: create natural Persian narration and title/description candidates consistent with the channel's source and safety policy.
4. **Production specialist**: select the configured production engine (current Python/FFmpeg/Pexels pipeline or MoneyPrinterTurbo when its dependencies and media sources are available). Do not silently substitute abstract clips for real footage.
5. **Quality reviewer**: verify media metadata, vertical format, audio/caption synchronization, scene relevance, legibility, duration, source credits, and policy compliance. Failed gates block upload.
6. **Release specialist**: call the existing deterministic uploader only after QA passes; default to private drafts during initial validation. Public scheduled publishing requires explicit workflow input or the existing scheduled production policy.
7. **Self-healing specialist**: classify failures from redacted logs, make only narrowly scoped changes on a dedicated branch, run regression tests, and propose a pull request. It must not rewrite secrets, bypass QA, disable tests, or automatically merge risky fixes.

## Cloud model policy

- Primary provider: Groq via `GROQ_API_KEY`.
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

## Delivery sequence

- Phase 1: cloud-only LLM behavior, tests, architecture documentation, and secret-safe preflight.
- Phase 2: OpenClaw cloud authentication and a real headless model-completion test.
- Phase 3: run specialist agent tasks with validated JSON handoffs and a central supervisor report.
- Phase 4: connect the supervisor to the existing video pipeline and MPT as a selectable engine, preserving QA gates.
- Phase 5: private upload test, then verify YouTube IDs and only then enable public scheduled release.
- Phase 6: bounded self-healing with branch-only repairs and regression tests.

## Reporting rule

Always distinguish `configured`, `tested`, `generated`, `uploaded privately`, and `published publicly`. Never claim an upload or view count without a real platform response.
