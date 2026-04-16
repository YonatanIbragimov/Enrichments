# Rev Whisper Enrichment Bridge

Thin Chrome extension that lets the GitHub Pages site talk to the local
enrichment listener running on `http://127.0.0.1:5055`.

## Install (unpacked)

1. Start the listener (see `../listener/README.md`).
2. Open `chrome://extensions` → toggle **Developer mode** (top-right).
3. Click **Load unpacked** → select this `extension/` folder.
4. Open the GitHub Pages tool page. You should see the extension marked as active
   (a `<meta name="revwhisper-bridge" content="1">` tag is injected).

## What it does

- **Toolbar popup** shows two status lights: the Python listener on `:5055`, and
  the Anthropic API (Claude). Click the refresh button to re-check; the Claude
  check is cached for 60s to avoid burning quota.
- Content script listens for `revwhisper:enrich-*` custom events on the page.
- Forwards each event to the background worker.
- Background worker fetches `http://127.0.0.1:5055/...` (content scripts can't do
  this directly from an HTTPS page — MV3 host_permissions let the background
  worker bypass mixed-content rules).
- Dispatches a `revwhisper:enrich-response` event back to the page with the result.

## Status light meanings

The popup shows three rows: **Listener**, **Claude Code (OAuth)**, **Claude API (key)**. Either Claude row green is enough — OAuth is preferred.

| Light | Listener            | Claude Code (OAuth)                                   | Claude API (key)                                    |
|-------|---------------------|-------------------------------------------------------|-----------------------------------------------------|
| 🟢    | Flask on :5055 up   | `claude auth status` exits 0 (logged in)              | `ANTHROPIC_API_KEY` set + api.anthropic.com replied |
| 🟡    | —                   | Binary missing, or installed but not logged in        | No key set (expected when using OAuth)              |
| 🔴    | Listener not running| Unknown error running `claude`                        | 401, network error, listener down                    |

**Auth modes:**
- **OAuth / Claude Code** — uses your existing `claude` CLI login. No key to manage, no env vars needed. Status check runs `claude auth status` (no billed API calls).
- **API key** — set `ANTHROPIC_API_KEY` in the listener's environment (plist `EnvironmentVariables`). Used only as a fallback when OAuth is unavailable.

## Permissions

- `http://127.0.0.1:5055/*` + `http://localhost:5055/*` — talk to the listener
- `https://yonatanibragimov.github.io/*` — inject into the published site
- `file:///*/Enrichments/*` — inject when you open the tool HTML locally for testing

Nothing leaves your machine.
