// Popup controller — polls the listener for /health and /claude/ping.

const TOOL_URL_DEFAULT = "https://yonatanibragimov.github.io/Enrichments/enrichment_tool.html";

const el = id => document.getElementById(id);

function setDot(id, cls) {
  const d = el(id);
  d.classList.remove("ok", "warn", "err", "idle", "pulse");
  d.classList.add(cls);
}

function setText(id, text) { el(id).textContent = text; }

async function ask(type, extra = {}) {
  return new Promise(resolve => {
    chrome.runtime.sendMessage({ type, ...extra }, resolve);
  });
}

async function checkListener() {
  setDot("dotListener", "pulse");
  setText("detListener", "Checking http://127.0.0.1:5055…");
  const r = await ask("health");
  if (r && r.ok) {
    setDot("dotListener", "ok");
    setText("detListener",
      `127.0.0.1:5055 · python ${(r.python || "").split("/").pop()} · ${r.jobs_total || 0} jobs`);
    el("jobs").innerHTML = `<strong>${r.jobs_running || 0}</strong> running · <strong>${r.jobs_total || 0}</strong> total this session`;
    return r;
  } else {
    setDot("dotListener", "err");
    const reason = r?.error ? `unreachable (${r.error})` : `unreachable (HTTP ${r?.status ?? 0})`;
    setText("detListener", reason);
    el("jobs").textContent = "—";
    return r;
  }
}

async function checkClaudeCode(force = false) {
  setDot("dotCC", "pulse");
  setText("detCC", "Checking…");
  const r = await ask("claudeCode", { force });
  if (!r || !r.ok) {
    if (r && r.reason === "not_installed") {
      setDot("dotCC", "warn");
      setText("detCC", "Not installed on PATH");
    } else if (r && r.reason === "not_authenticated") {
      setDot("dotCC", "warn");
      setText("detCC", `Installed (v${r.version || "?"}) · not logged in — run \`claude\` once in a terminal`);
    } else {
      setDot("dotCC", "err");
      setText("detCC", `Error: ${r?.reason || r?.error || "unknown"}`);
    }
    return r;
  }
  setDot("dotCC", "ok");
  const cacheTag = r.cached ? ` (cached ${r.age_sec}s)` : "";
  setText("detCC", `v${r.version || "?"} · authenticated${cacheTag}`);
  return r;
}

async function checkClaude(force = false) {
  setDot("dotClaude", "pulse");
  setText("detClaude", "Checking…");
  const r = await ask("claude", { force });
  if (!r || !r.ok) {
    if (r && (r.reason === "no_api_key" || r.reason === "bad_key_format")) {
      setDot("dotClaude", "warn");
      setText("detClaude",
        r.reason === "no_api_key"
          ? "No API key set (fallback only — OAuth is preferred)"
          : "API key format looks wrong (should start with sk-ant-)");
    } else if (r && r.reason === "unauthorized") {
      setDot("dotClaude", "err");
      setText("detClaude", "Unauthorized — API key rejected (401)");
    } else if (r && r.reason === "network") {
      setDot("dotClaude", "err");
      setText("detClaude", `Network error: ${r.error || "no route to api.anthropic.com"}`);
    } else {
      setDot("dotClaude", "err");
      setText("detClaude", `Error: ${r?.reason || r?.error || "unknown"}`);
    }
    return r;
  }
  setDot("dotClaude", "ok");
  const cacheTag = r.cached ? ` (cached ${r.age_sec}s)` : "";
  setText("detClaude",
    `${r.model || "reachable"} · ${r.latency_ms ?? "?"}ms${cacheTag}`);
  return r;
}

function summarize(cc, api) {
  const el = document.getElementById("summary");
  if (cc?.ok) {
    el.textContent = "✓ Claude ready via OAuth (Claude Code). API key not required.";
  } else if (api?.ok) {
    el.textContent = "✓ Claude ready via API key (fallback).";
  } else {
    el.textContent = "⚠ No working Claude auth — enrichment judgment calls will fail.";
  }
}

async function refreshAll(force = false) {
  const listener = await checkListener();
  if (listener && listener.ok) {
    const [cc, api] = await Promise.all([
      checkClaudeCode(force),
      checkClaude(force),
    ]);
    summarize(cc, api);
  } else {
    setDot("dotCC", "idle");
    setText("detCC", "Blocked — listener must be running");
    setDot("dotClaude", "idle");
    setText("detClaude", "Blocked — listener must be running");
    document.getElementById("summary").textContent = "";
  }
}

el("refresh").addEventListener("click", () => refreshAll(true));

el("openTool").addEventListener("click", (e) => {
  e.preventDefault();
  chrome.storage.sync.get({ toolUrl: TOOL_URL_DEFAULT }, ({ toolUrl }) => {
    chrome.tabs.create({ url: toolUrl });
  });
});

// Version from manifest
try {
  const m = chrome.runtime.getManifest();
  if (m?.version) el("ver").textContent = "v" + m.version;
} catch {}

refreshAll(false);
