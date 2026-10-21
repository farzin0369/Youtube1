const $ = selector => document.querySelector(selector);
const chatForm = $("#chat-form");
const promptBox = $("#prompt");
const messages = $("#messages");
const welcome = $("#welcome");
const sendButton = $("#send");
const settingsDialog = $("#settings-dialog");
const keys = { url: "hamrah.apiUrl", model: "hamrah.model", key: "hamrah.apiKey", backend: "hamrah.backendUrl" };

function settings() {
  return {
    url: localStorage.getItem(keys.url) || "",
    model: localStorage.getItem(keys.model) || "",
    key: localStorage.getItem(keys.key) || "",
    backend: localStorage.getItem(keys.backend) || "",
    backendSecret: sessionStorage.getItem("hamrah.backendSecret") || ""
  };
}
function loadSettings() {
  const s = settings();
  $("#api-url").value = s.url;
  $("#model-name").value = s.model;
  $("#api-key").value = s.key;
  $("#backend-url").value = s.backend;
  $("#backend-secret").value = s.backendSecret;
}
function appendMessage(role, text, extraClass = "") {
  welcome.hidden = true;
  const el = document.createElement("article");
  el.className = "message " + role + (extraClass ? " " + extraClass : "");
  const label = document.createElement("div");
  label.className = "message-label";
  label.textContent = role === "user" ? "شما" : "همراه هوشمند";
  const body = document.createElement("div");
  body.textContent = text;
  el.append(label, body);
  messages.append(el);
  $("#chat").scrollTop = $("#chat").scrollHeight;
  return el;
}
function openAction(action) {
  if (action === "google") {
    window.open("https://www.google.com/search?q=" + encodeURIComponent(promptBox.value.trim() || ""), "_blank", "noopener");
    return true;
  }
  if (action === "github") {
    window.open("https://github.com/farzin0369/Youtube1", "_blank", "noopener");
    return true;
  }
  return false;
}
document.querySelectorAll('[data-action="google"], [data-action="github"]').forEach(button =>
  button.addEventListener("click", () => openAction(button.dataset.action))
);
document.querySelectorAll("[data-prompt]").forEach(button => button.addEventListener("click", () => {
  promptBox.value = button.dataset.prompt;
  promptBox.focus();
}));
$("#settings-open").addEventListener("click", () => { loadSettings(); settingsDialog.showModal(); });
$("#save-settings").addEventListener("click", () => {
  localStorage.setItem(keys.url, $("#api-url").value.trim().replace(/\/$/, ""));
  localStorage.setItem(keys.model, $("#model-name").value.trim());
  localStorage.setItem(keys.key, $("#api-key").value.trim());
  localStorage.setItem(keys.backend, $("#backend-url").value.trim().replace(/\/$/, ""));
  const secret = $("#backend-secret").value.trim();
  if (secret) sessionStorage.setItem("hamrah.backendSecret", secret);
  else sessionStorage.removeItem("hamrah.backendSecret");
});
$("#clear-settings").addEventListener("click", () => {
  Object.values(keys).forEach(key => localStorage.removeItem(key));
  sessionStorage.removeItem("hamrah.backendSecret");
  loadSettings();
});
promptBox.addEventListener("input", () => {
  promptBox.style.height = "auto";
  promptBox.style.height = Math.min(promptBox.scrollHeight, 180) + "px";
});
promptBox.addEventListener("keydown", event => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    chatForm.requestSubmit();
  }
});

let history = [];
function backendHeaders(s) {
  if (!s.backend || !s.backendSecret) throw new Error("نشانی بک‌اند و رمز دسترسی را در تنظیمات وارد کن.");
  return { "Content-Type": "application/json", "Authorization": "Bearer " + s.backendSecret };
}
async function askAI(text, assistantNode) {
  const s = settings();
  const systemMessage = {
    role: "system",
    content: "تو یک دستیار دقیق، مودب و توانمند هستی. به زبان کاربر پاسخ بده. درباره توانایی اجرای کارها صادق باش. این اپ تنها زمانی می‌تواند در GitHub تغییری ایجاد کند که کاربر صریحاً از دکمه پیشنهاد تغییر استفاده کند؛ ادغام و انتشار خودکار انجام نده."
  };
  const conversation = [...history, { role: "user", content: text }];
  try {
    let response;
    if (s.backend) {
      response = await fetch(s.backend + "/chat", {
        method: "POST",
        headers: backendHeaders(s),
        body: JSON.stringify({ messages: [systemMessage, ...conversation] })
      });
    } else {
      assistantNode.classList.add("error");
      assistantNode.lastChild.textContent = "برای استفاده از OpenClaw، نشانی بک‌اند مستقرشده و رمز دسترسی را در تنظیمات وارد کن. اتصال مستقیم به API عمومی غیرفعال است تا کلید مدل در مرورگر ذخیره نشود.";
      return;
    }
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.error?.message || data.error || ("خطای سرویس HTTP " + response.status));
    const answer = data.choices?.[0]?.message?.content;
    if (typeof answer !== "string" || !answer) throw new Error("پاسخ قابل‌خواندن از API دریافت نشد.");
    history.push({ role: "user", content: text }, { role: "assistant", content: answer });
    if (history.length > 24) history = history.slice(-24);
    assistantNode.lastChild.textContent = answer;
  } catch (error) {
    assistantNode.classList.add("error");
    assistantNode.lastChild.textContent = "اتصال برقرار نشد: " + (error.message || "خطای ناشناخته") + ". نشانی بک‌اند، رمز، تنظیمات CORS و وضعیت سرویس را بررسی کن.";
  }
}
chatForm.addEventListener("submit", async event => {
  event.preventDefault();
  const text = promptBox.value.trim();
  if (!text || sendButton.disabled) return;
  appendMessage("user", text);
  promptBox.value = "";
  promptBox.style.height = "auto";
  sendButton.disabled = true;
  const reply = appendMessage("assistant", "در حال آماده‌سازی پاسخ…");
  await askAI(text, reply);
  sendButton.disabled = false;
  promptBox.focus();
});

async function inspectRepository() {
  appendMessage("user", "مخزن GitHub را بررسی کن");
  const reply = appendMessage("assistant", "در حال خواندن فهرست فایل‌های مخزن…");
  try {
    const s = settings();
    let files;
    if (s.backend) {
      const response = await fetch(s.backend + "/github/tree?branch=main", { headers: backendHeaders(s) });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || ("HTTP " + response.status));
      files = data.files || [];
    } else {
      const response = await fetch("https://api.github.com/repos/farzin0369/Youtube1/git/trees/main?recursive=1", {
        headers: { "Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28" }
      });
      if (!response.ok) throw new Error("GitHub API پاسخ HTTP " + response.status + " داد.");
      const data = await response.json();
      files = (data.tree || []).filter(item => item.type === "blob").map(item => item.path);
    }
    const relevant = files.filter(path => /^(app|scripts|mobile-assistant|\.github\/workflows|docs)\//.test(path)).slice(0, 90);
    reply.lastChild.textContent = "بررسی انجام شد. تعداد فایل‌های قابل مشاهده: " + files.length +
      "\n\nفایل‌های مهم (حداکثر ۹۰ مورد):\n" + (relevant.length ? relevant.map(path => "• " + path).join("\n") : "فایلی در مسیرهای منتخب پیدا نشد.") +
      "\n\nاین عملیات فقط خواندن فایل‌هاست؛ برای نوشتن از «پیشنهاد تغییر GitHub» استفاده کن.";
  } catch (error) {
    reply.classList.add("error");
    reply.lastChild.textContent = "نتوانستم مخزن را بخوانم: " + error.message + "\nاگر از بک‌اند استفاده می‌کنی، مطمئن شو مستقر شده، رمز درست است و CORS تنظیم شده.";
  }
}
document.querySelectorAll('[data-action="inspect"]').forEach(button => button.addEventListener("click", inspectRepository));

async function proposeChange() {
  const s = settings();
  if (!s.backend || !s.backendSecret) {
    appendMessage("assistant", "برای پیشنهاد تغییر کد، ابتدا بک‌اند مستقرشده و رمز دسترسی را در تنظیمات وارد کن.", "error");
    return;
  }
  const path = window.prompt("مسیر فایل مجاز در مخزن (مثلاً docs/example.md):");
  if (!path) return;
  const message = window.prompt("عنوان کوتاه تغییر / پیام commit:");
  if (!message) return;
  const content = window.prompt("محتوای کامل فایل را وارد کن (برای متن طولانی بهتر است از نسخه وب استفاده کنی):");
  if (content === null) return;
  if (!window.confirm("یک شاخه جدید و Pull Request پیش‌نویس ساخته شود؟ هیچ mergeای انجام نمی‌شود.")) return;
  const reply = appendMessage("assistant", "در حال ایجاد شاخه و پیش‌نویس Pull Request…");
  try {
    const response = await fetch(s.backend + "/github/propose-change", {
      method: "POST",
      headers: { ...backendHeaders(s), "X-Confirm-Action": "I_APPROVE_WRITE" },
      body: JSON.stringify({ path: path.trim(), message: message.trim(), content })
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || ("HTTP " + response.status));
    reply.lastChild.textContent = "پیش‌نویس Pull Request ساخته شد: " + data.pull_request + "\nشاخه: " + data.branch + "\nاین تغییر هنوز ادغام نشده و نیاز به بازبینی دارد.";
  } catch (error) {
    reply.classList.add("error");
    reply.lastChild.textContent = "ساخت پیش‌نویس ناموفق بود: " + error.message;
  }
}
document.querySelectorAll('[data-action="propose"]').forEach(button => button.addEventListener("click", proposeChange));
if ("serviceWorker" in navigator && location.protocol.startsWith("http")) {
  window.addEventListener("load", () => navigator.serviceWorker.register("./sw.js").catch(() => {}));
}
