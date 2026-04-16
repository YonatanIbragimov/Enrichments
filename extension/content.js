// Runs in the page's world. Bridges custom DOM events to the background worker,
// which in turn talks to the localhost listener.
//
// Page → extension:
//   window.dispatchEvent(new CustomEvent("revwhisper:enrich-start", { detail: { csv, filename }}))
//   window.dispatchEvent(new CustomEvent("revwhisper:enrich-status", { detail: { jobId }}))
//   window.dispatchEvent(new CustomEvent("revwhisper:enrich-result", { detail: { jobId }}))
//
// Extension → page:
//   window.dispatchEvent(new CustomEvent("revwhisper:enrich-response", { detail: {...} }))
//
// Also exposes a boolean on window so the page can detect the extension is present.

(() => {
  const MARK = "__revwhisperBridge";
  if (window[MARK]) return;
  window[MARK] = true;

  // Expose presence to the page via a DOM attribute (safer than touching window from the isolated world).
  const marker = document.createElement("meta");
  marker.name = "revwhisper-bridge";
  marker.content = "1";
  (document.head || document.documentElement).appendChild(marker);

  function relay(event, req) {
    chrome.runtime.sendMessage(req, (resp) => {
      window.dispatchEvent(new CustomEvent("revwhisper:enrich-response", {
        detail: { event, ...resp },
      }));
    });
  }

  window.addEventListener("revwhisper:enrich-start", (e) => {
    relay("start", { type: "start", csv: e.detail.csv, filename: e.detail.filename || "batch.csv" });
  });

  window.addEventListener("revwhisper:enrich-status", (e) => {
    relay("status", { type: "status", jobId: e.detail.jobId });
  });

  window.addEventListener("revwhisper:enrich-result", (e) => {
    relay("result", { type: "result", jobId: e.detail.jobId });
  });

  window.addEventListener("revwhisper:enrich-health", () => {
    relay("health", { type: "health" });
  });
})();
