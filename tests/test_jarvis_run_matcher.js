const assert = require("node:assert/strict");
const { findRun, findCheck } = require("../jarvis/run-matcher.js");

const requestId = "req-current-123";
const runs = [
  { id: 77, event: "workflow_dispatch", head_branch: "feat/jarvis-chat-openrouter-integration", display_title: "Jarvis chat / req-old", created_at: "2026-01-01T00:00:00Z" },
  { id: 88, event: "workflow_dispatch", head_branch: "feat/jarvis-chat-openrouter-integration", display_title: `Jarvis chat / ${requestId}`, created_at: "2026-01-01T00:00:01Z" },
  { id: 99, event: "workflow_dispatch", head_branch: "main", display_title: `Jarvis chat / ${requestId}` },
  { id: 111, event: "push", head_branch: "feat/jarvis-chat-openrouter-integration", display_title: `Jarvis chat / ${requestId}` },
];
assert.equal(findRun(runs, requestId, "feat/jarvis-chat-openrouter-integration").id, 88);
assert.equal(findRun(runs, "missing", "feat/jarvis-chat-openrouter-integration"), null);

const checks = [
  { name: "Jarvis response", external_id: "77", output: { summary: "stale" } },
  { name: "Jarvis response", external_id: "88", output: { summary: "## پاسخ Jarvis\n\nanswer" } },
  { name: "Unrelated check", external_id: "88", output: { summary: "wrong check" } },
];
assert.equal(findCheck(checks, 88).output.summary, "## پاسخ Jarvis\n\nanswer");
assert.equal(findCheck(checks, 999), null);
console.log("PASS exact request/run correlation");
