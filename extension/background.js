// Service worker. Talks to the localhost listener on behalf of the content script
// (which can't fetch localhost directly from an HTTPS page).

const BASE = "http://127.0.0.1:5055";

async function jsonFetch(path, options = {}) {
  try {
    const resp = await fetch(BASE + path, {
      ...options,
      headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    });
    const body = await resp.text();
    let parsed;
    try { parsed = JSON.parse(body); } catch { parsed = { raw: body }; }
    return { ok: resp.ok, status: resp.status, ...parsed };
  } catch (err) {
    return { ok: false, status: 0, error: String(err) };
  }
}

chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
  (async () => {
    switch (msg.type) {
      case "health":
        sendResponse(await jsonFetch("/health"));
        break;

      case "claude":
        sendResponse(await jsonFetch(`/claude/ping${msg.force ? "?force=1" : ""}`));
        break;

      case "claudeCode":
        sendResponse(await jsonFetch(`/auth/claude-code/ping${msg.force ? "?force=1" : ""}`));
        break;

      case "start": {
        const r = await jsonFetch("/enrich", {
          method: "POST",
          body: JSON.stringify({ csv: msg.csv, filename: msg.filename }),
        });
        sendResponse(r);
        break;
      }

      case "status":
        sendResponse(await jsonFetch(`/status/${encodeURIComponent(msg.jobId)}`));
        break;

      case "result": {
        // Fetch the CSV text directly (not JSON)
        try {
          const resp = await fetch(`${BASE}/result/${encodeURIComponent(msg.jobId)}`);
          if (!resp.ok) {
            sendResponse({ ok: false, status: resp.status, error: "result not ready" });
            break;
          }
          const csv = await resp.text();
          sendResponse({ ok: true, csv });
        } catch (err) {
          sendResponse({ ok: false, error: String(err) });
        }
        break;
      }

      default:
        sendResponse({ ok: false, error: `unknown type ${msg.type}` });
    }
  })();
  return true; // keep channel open for async sendResponse
});
