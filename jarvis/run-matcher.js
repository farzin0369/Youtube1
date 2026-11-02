(function (root) {
  "use strict";

  function findRun(runs, requestId, branch) {
    const expectedTitle = `Jarvis chat / ${requestId}`;
    return (runs || []).find((run) =>
      run.event === "workflow_dispatch" &&
      run.head_branch === branch &&
      run.display_title === expectedTitle
    ) || null;
  }

  function findCheck(checks, runId) {
    return (checks || []).find((check) =>
      check.name === "Jarvis response" &&
      String(check.external_id) === String(runId)
    ) || null;
  }

  const api = { findRun, findCheck };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  if (root) root.JarvisRunMatcher = api;
})(typeof globalThis !== "undefined" ? globalThis : this);
