# Rev Whisper Local Listener

A tiny always-on Flask server on `http://127.0.0.1:5055` that receives
scored-CSV uploads from the Chrome extension and kicks off `enrich_batch.py`.

## Install (always-on)

```bash
cd "/Users/trinity/Desktop/Enrichments/listener"
bash setup.sh
```

That:
1. Installs `flask` + `flask-cors` into your user Python.
2. Copies the LaunchAgent plist to `~/Library/LaunchAgents/`.
3. Loads it (starts immediately + auto-starts at every login).
4. Health-checks `http://127.0.0.1:5055/health`.

## Manage

```bash
bash setup.sh status      # show launchd state + health
bash setup.sh tail        # follow the logs
bash setup.sh stop        # stop (will re-start on next login)
bash setup.sh uninstall   # stop + remove the LaunchAgent
```

## Endpoints

| Method | Path                | Purpose                                                  |
|--------|---------------------|----------------------------------------------------------|
| GET    | `/health`           | Liveness + config snapshot                               |
| POST   | `/enrich`           | Body: `{csv, filename}` → kicks off `enrich_batch.py`   |
| GET    | `/status/<job_id>`  | Current progress + status                                |
| GET    | `/result/<job_id>`  | Enriched CSV (when `status == "completed"`)              |
| GET    | `/log/<job_id>`     | Raw stdout from the enrich run                           |

## Where things land

- Input CSVs:   `~/Desktop/Enrichments/25-49 Listings/batches/job_<id>.csv`
- Output CSVs:  `~/Desktop/Enrichments/25-49 Listings/enriched/job_<id>_enriched.csv`
- Job state:    `~/Desktop/Enrichments/listener/jobs/job_<id>.json`
- Run logs:     `~/Desktop/Enrichments/listener/logs/job_<id>.log`
- Server logs:  `~/Desktop/Enrichments/listener/logs/listener.{out,err}.log`

## Security posture

- Binds to `127.0.0.1` only — not reachable over LAN.
- CORS allowlist: `yonatanibragimov.github.io` + `localhost` only.
- No auth token (localhost-only + CORS is enough for this use case).
- If you expose it beyond localhost, add a shared secret header check.
