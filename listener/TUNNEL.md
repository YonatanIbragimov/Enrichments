# Tunnel Setup — expose the listener publicly

The listener binds to `127.0.0.1:5055` by default. To trigger enrichment from
other devices (phone, laptop, anyone on the GitHub Pages site), you need a
**public HTTPS URL** that forwards to that local port.

Recommended: **Tailscale Funnel** — free, stable URL, no domain required.

---

## Step 1 — Pick a strong auth token

Before anything else, generate a shared secret and store it where both the
listener and the page can see it.

```bash
openssl rand -hex 24
# → e.g.  a7f1c3... (copy this)
```

### Paste it into the LaunchAgent plist:
Edit `listener/com.revwhisper.listener.plist`:

```xml
<key>REVWHISPER_AUTH_TOKEN</key>
<string>a7f1c3...</string>
```

Then reload:

```bash
cd "/Users/trinity/Desktop/Enrichments/listener"
bash setup.sh stop
bash setup.sh install
```

The listener now requires `X-Auth: <token>` on every `POST /enrich*` request.
Without the token, those endpoints return `401`.

---

## Step 2 — Install + run Tailscale Funnel

### One-time install

```bash
brew install --cask tailscale     # app for the menubar
# …open the Tailscale app once → sign in with Google/GitHub
```

### Enable HTTPS for your tailnet

1. Go to https://login.tailscale.com/admin/dns
2. Under **HTTPS Certificates**, click **Enable HTTPS**
3. Under **Funnel**, add your machine name to the access control list (or just
   enable the "Allow all" Funnel policy for now).

### Expose the listener

```bash
# Forwards public HTTPS → http://localhost:5055
sudo tailscale funnel --bg 5055
```

Tailscale prints a URL like:

```
https://trinitys-mac-mini.tail1234.ts.net/
```

That's your public listener URL. Copy it.

### Make it survive reboots

Tailscale Funnel config persists — once you run `tailscale funnel --bg 5055`
once, it will re-establish on every boot automatically (as long as the
Tailscale app is running, which it does by default).

---

## Step 3 — Plug it into the page

Open https://yonatanibragimov.github.io/Enrichments/ on any device. The top
banner will say **"⚙ Configure listener URL"**. Click **Configure**:

- **Listener URL:** paste the Tailscale Funnel URL (e.g. `https://trinitys-mac-mini.tail1234.ts.net`)
- **Auth token:** paste the hex string from Step 1

The banner turns green and the tier buttons light up. The config is stored in
`localStorage` on that browser — each device you use has to configure once.

---

## Alternatives

### Cloudflare Quick Tunnel (no account, ephemeral URL)

Great for a 5-minute test, not for permanent use — the URL changes on every restart.

```bash
brew install cloudflared
cloudflared tunnel --url http://localhost:5055
# prints https://<random>.trycloudflare.com — good until you Ctrl+C
```

### Cloudflare Named Tunnel (stable, requires a domain)

```bash
cloudflared login
cloudflared tunnel create revwhisper
cloudflared tunnel route dns revwhisper listener.yourdomain.com
cloudflared tunnel run revwhisper
```

---

## Security posture

- **Auth token** is required for all mutating endpoints (`POST /enrich`,
  `POST /enrich/tier/*`). Read endpoints (`/health`, `/status`, `/result`) are
  intentionally open — they leak no source data and the tunnel URL is unguessable.
- **Rotate the token** any time by generating a new one, updating the plist +
  reloading the listener, then re-pasting into any browsers that use it.
- **Revoke the tunnel** instantly with `sudo tailscale funnel off` if something
  feels wrong.
