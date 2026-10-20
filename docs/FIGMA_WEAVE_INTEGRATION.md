# Figma Weave integration (opt-in)

This adapter lets the spiritual video pipeline use a **published Figma Weave workflow** to create one scene-matched still per narration segment. The default pipeline remains unchanged when Weave is not configured or generation is disabled.

## Important access and cost constraints

- The official Weave REST API currently requires a **Weave Enterprise** subscription and a workspace-admin-created API token.
- API docs: https://developers.figma.com/docs/weave-api/
- API base URL: https://developer.api.weavy.ai/v1
- The token is sent only in the `X-Figma-Token` header; never commit it.
- Runs consume Weave credits. The adapter first calls the cost endpoint and refuses to run when the cost is unknown or exceeds the explicit configured limit.
- This does not create or publish Weave workflows. Publish a workflow in Weave first, with a string input named Prompt, Scene, Description, Text, or Query. Any other required inputs must have published defaults.
- The selected workflow must return at least one image asset. The adapter currently downloads still images only; it does not claim to generate video clips.

## GitHub Actions configuration

Add these as **Repository Secrets** (Settings → Secrets and variables → Actions → Secrets):

- `WEAVE_API_TOKEN`: API token from Weave Settings → API Tokens.
  
Add these as **Repository Variables**:

- `WEAVE_TOOL_ID`: ID of a published shared tool in the active workspace.
- `WEAVE_AUTO_RUN`: set to `true` only after checking the estimated costs and accepting credit use.
- `WEAVE_MAX_CREDIT_COST`: positive numeric per-scene credit cap. The default is zero, which blocks all paid runs.
- Optional `WEAVE_POLL_TIMEOUT_SECONDS` (default 600) and `WEAVE_POLL_INTERVAL_SECONDS` (default 5).

The repository workflow must explicitly pass these environment variables into its job before the feature can be used in Actions. Do not enable this on a publishing run until a dry-run confirms the workflow output, aspect ratio, scene relevance, and credit budget.

## Pipeline behavior and safety

- Generation is opt-in; no token means no Weave API calls.
- Each scene prompt is derived from that scene's narration and asks for a cinematic, text-free composition in the correct aspect ratio.
- Cost unknown, missing prompt input, missing required input defaults, API errors, or missing images fail closed for the Weave batch; the existing pipeline's visual-source quality gate still decides whether rendering can continue.
- Generated images are local run artifacts and are not committed to Git.
