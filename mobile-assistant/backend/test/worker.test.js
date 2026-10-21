import test from "node:test";
import assert from "node:assert/strict";
import worker from "../src/index.js";

const ORIGIN = "https://example.pages.dev";
const baseEnv = {
  ALLOWED_ORIGIN: ORIGIN,
  APP_ACCESS_SECRET: "test-app-secret",
  GITHUB_TOKEN: "test-github-token",
  OPENCLAW_CHAT_URL: "https://gateway.example.test/v1/chat/completions",
  OPENCLAW_GATEWAY_TOKEN: "test-gateway-token"
};

function request(path, { method = "GET", auth = true, origin = ORIGIN, body, headers = {} } = {}) {
  return new Request("https://worker.example.test" + path, {
    method,
    headers: {
      ...(origin ? { Origin: origin } : {}),
      ...(auth ? { Authorization: "Bearer test-app-secret" } : {}),
      ...(body !== undefined ? { "Content-Type": "application/json" } : {}),
      ...headers
    },
    ...(body !== undefined ? { body: JSON.stringify(body) } : {})
  });
}

test("health endpoint reports restricted mode without credentials", async () => {
  const response = await worker.fetch(request("/health", { auth: false }), {});
  assert.equal(response.status, 200);
  assert.equal((await response.json()).mode, "restricted");
});

test("rejects non-health requests without app secret", async () => {
  const response = await worker.fetch(request("/github/tree", { auth: false }), baseEnv);
  assert.equal(response.status, 401);
});

test("rejects unapproved browser origins", async () => {
  const response = await worker.fetch(request("/github/tree", { origin: "https://evil.example" }), baseEnv);
  assert.equal(response.status, 403);
});

test("chat returns 503 when OpenClaw is not configured", async () => {
  const env = { ALLOWED_ORIGIN: ORIGIN, APP_ACCESS_SECRET: baseEnv.APP_ACCESS_SECRET };
  const response = await worker.fetch(request("/chat", { method: "POST", body: { messages: [{ role: "user", content: "hello" }] } }), env);
  assert.equal(response.status, 503);
});

test("chat rejects malformed message collections before contacting Gateway", async () => {
  const originalFetch = globalThis.fetch;
  let called = false;
  globalThis.fetch = async () => { called = true; throw new Error("unexpected network request"); };
  try {
    const response = await worker.fetch(request("/chat", { method: "POST", body: { messages: [] } }), baseEnv);
    assert.equal(response.status, 400);
    assert.equal(called, false);
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test("chat forwards valid messages with the Gateway token and returns its response", async () => {
  const originalFetch = globalThis.fetch;
  let captured;
  globalThis.fetch = async (url, init) => {
    captured = { url: String(url), init };
    return new Response(JSON.stringify({ choices: [{ message: { role: "assistant", content: "سلام" } }] }), {
      status: 200, headers: { "content-type": "application/json" }
    });
  };
  try {
    const response = await worker.fetch(request("/chat", {
      method: "POST",
      body: { messages: [{ role: "user", content: "سلام" }] }
    }), baseEnv);
    assert.equal(response.status, 200);
    assert.equal(response.headers.get("cache-control"), "no-store");
    assert.equal(captured.url, baseEnv.OPENCLAW_CHAT_URL);
    assert.equal(captured.init.headers.Authorization, "Bearer test-gateway-token");
    assert.equal(JSON.parse(captured.init.body).messages[0].content, "سلام");
    assert.equal((await response.json()).choices[0].message.content, "سلام");
  } finally {
    globalThis.fetch = originalFetch;
  }
});
