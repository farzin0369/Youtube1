const JSON_HEADERS = { "content-type": "application/json; charset=utf-8" };
const REPO = "farzin0369/Youtube1";
const ALLOWED_PREFIXES = ["mobile-assistant/", "docs/", "scripts/"];

function json(data, status = 200) {
  return new Response(JSON.stringify(data), { status, headers: JSON_HEADERS });
}
function cors(request, env) {
  const origin = request.headers.get("Origin") || "";
  const allowed = (env.ALLOWED_ORIGIN || "").split(",").map(s => s.trim()).filter(Boolean);
  if (!origin || allowed.includes(origin)) return {
    "Access-Control-Allow-Origin": origin || "*",
    "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Confirm-Action",
    "Vary": "Origin"
  };
  return null;
}
function respond(request, env, data, status = 200) {
  const headers = cors(request, env);
  if (!headers) return json({ error: "Origin is not allowed." }, 403);
  return new Response(JSON.stringify(data), { status, headers: { ...JSON_HEADERS, ...headers } });
}
async function gh(path, env, init = {}) {
  if (!env.GITHUB_TOKEN) throw new Error("Server is missing GITHUB_TOKEN.");
  const response = await fetch("https://api.github.com/repos/" + REPO + path, {
    ...init,
    headers: {
      "Accept": "application/vnd.github+json",
      "Authorization": "Bearer " + env.GITHUB_TOKEN,
      "X-GitHub-Api-Version": "2022-11-28",
      "Content-Type": "application/json",
      ...(init.headers || {})
    }
  });
  const body = await response.text();
  let data; try { data = body ? JSON.parse(body) : {}; } catch { data = {}; }
  if (!response.ok) throw new Error("GitHub API returned HTTP " + response.status + (data.message ? ": " + data.message : ""));
  return data;
}
function validPath(path) {
  return typeof path === "string" && path.length < 240 &&
    !path.startsWith("/") && !path.split("/").includes("..") &&
    ALLOWED_PREFIXES.some(prefix => path.startsWith(prefix));
}
export default {
  async fetch(request, env) {
    if (request.method === "OPTIONS") {
      const headers = cors(request, env);
      return headers ? new Response(null, { status: 204, headers }) : new Response(null, { status: 403 });
    }
    const url = new URL(request.url);
    try {
      if (url.pathname === "/health" && request.method === "GET")
        return respond(request, env, { ok: true, service: "hamrah-github-backend", repo: REPO, mode: "restricted" });

      // CORS is not authentication. Require a separate secret for all non-health routes.
      if (!env.APP_ACCESS_SECRET || request.headers.get("Authorization") !== "Bearer " + env.APP_ACCESS_SECRET)
        return respond(request, env, { error: "Unauthorized." }, 401);

      if (url.pathname === "/github/tree" && request.method === "GET") {
        const branch = url.searchParams.get("branch") || "main";
        if (!/^(main|feat\/[a-zA-Z0-9._-]+)$/.test(branch)) return respond(request, env, { error: "Invalid branch." }, 400);
        const tree = await gh("/git/trees/" + encodeURIComponent(branch) + "?recursive=1", env);
        return respond(request, env, { branch, truncated: Boolean(tree.truncated), files: (tree.tree || []).filter(x => x.type === "blob").map(x => x.path).filter(validPath).slice(0, 250) });
      }

      if (url.pathname === "/github/file" && request.method === "GET") {
        const path = url.searchParams.get("path") || "";
        const ref = url.searchParams.get("ref") || "main";
        if (!validPath(path)) return respond(request, env, { error: "File path is outside the allowlist." }, 400);
        const data = await gh("/contents/" + path.split("/").map(encodeURIComponent).join("/") + "?ref=" + encodeURIComponent(ref), env);
        if (Array.isArray(data) || !data.content) return respond(request, env, { error: "Expected a text file." }, 400);
        const decoded = atob(data.content.replace(/\n/g, ""));
        const bytes = Uint8Array.from(decoded, c => c.charCodeAt(0));
        return respond(request, env, { path, ref, sha: data.sha, content: new TextDecoder().decode(bytes) });
      }

      if (url.pathname === "/github/propose-change" && request.method === "POST") {
        if (request.headers.get("X-Confirm-Action") !== "I_APPROVE_WRITE")
          return respond(request, env, { error: "Explicit write confirmation required." }, 428);
        const body = await request.json();
        const path = body.path, content = body.content, message = body.message;
        if (!validPath(path)) return respond(request, env, { error: "File path is outside the allowlist." }, 400);
        if (typeof content !== "string" || content.length > 120000) return respond(request, env, { error: "Content must be text under 120 KB." }, 400);
        if (typeof message !== "string" || !message.trim() || message.length > 120) return respond(request, env, { error: "A short commit message is required." }, 400);
        const branch = "ai-assistant/" + new Date().toISOString().replace(/[-:.TZ]/g, "").slice(0, 14) + "-" + crypto.randomUUID().slice(0, 8);
        const base = await gh("/git/ref/heads/main", env);
        const commit = await gh("/git/commits/" + base.object.sha, env);
        const created = await gh("/git/refs", env, { method: "POST", body: JSON.stringify({ ref: "refs/heads/" + branch, sha: commit.sha }) });
        const filePath = "/contents/" + path.split("/").map(encodeURIComponent).join("/");
        let existingSha;
        try {
          const existing = await gh(filePath + "?ref=main", env);
          if (!Array.isArray(existing) && existing.sha) existingSha = existing.sha;
        } catch (error) {
          if (!String(error.message).includes("HTTP 404")) throw error;
        }
        const encoded = btoa(String.fromCharCode(...new TextEncoder().encode(content)));
        await gh(filePath, env, {
          method: "PUT",
          body: JSON.stringify({ message: message.trim(), content: encoded, branch, ...(existingSha ? { sha: existingSha } : {}) })
        });
        const pr = await gh("/pulls", env, {
          method: "POST",
          body: JSON.stringify({
            title: message.trim().slice(0, 100),
            head: branch,
            base: "main",
            draft: true,
            body: "Created by Hamrah mobile assistant. This is a draft for review; it has not been merged.\n\nChanged file: " + path
          })
        });
        return respond(request, env, { ok: true, branch, pull_request: pr.html_url, draft: true, merged: false });
      }

      if (url.pathname === "/chat" && request.method === "POST") {
        // Primary route is the user's own OpenClaw Gateway, not a third-party model API.
        // Configure OPENCLAW_CHAT_URL as the complete OpenAI-compatible chat-completions URL,
        // and keep OPENCLAW_GATEWAY_TOKEN in Worker secrets.
        if (!env.OPENCLAW_CHAT_URL || !env.OPENCLAW_GATEWAY_TOKEN)
          return respond(request, env, {
            error: "OpenClaw is not connected. Configure OPENCLAW_CHAT_URL and OPENCLAW_GATEWAY_TOKEN as Worker settings/secrets."
          }, 503);
        const body = await request.json();
        if (!Array.isArray(body.messages) || body.messages.length < 1 || body.messages.length > 30)
          return respond(request, env, { error: "Invalid messages." }, 400);
        const upstream = await fetch(env.OPENCLAW_CHAT_URL, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "Authorization": "Bearer " + env.OPENCLAW_GATEWAY_TOKEN
          },
          body: JSON.stringify({
            model: env.OPENCLAW_MODEL || "openclaw",
            messages: body.messages,
            temperature: 0.6,
            stream: false
          })
        });
        const result = await upstream.text();
        const headers = cors(request, env);
        if (!headers) return json({ error: "Origin is not allowed." }, 403);
        return new Response(result, {
          status: upstream.status,
          headers: { ...JSON_HEADERS, ...headers, "Cache-Control": "no-store" }
        });
      }
      return respond(request, env, { error: "Not found." }, 404);
    } catch (error) {
      return respond(request, env, { error: error.message || "Request failed." }, 500);
    }
  }
};
