#!/usr/bin/env python3.11
"""
Rev Whisper local enrichment listener.

Receives CSV uploads from the Chrome extension, kicks off enrich_batch.py as a
subprocess, and exposes status + result over HTTP on localhost.

Start manually:
  python3.11 server.py

Or install as a LaunchAgent (see com.revwhisper.listener.plist + setup.sh).
"""

import csv
import io
import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time
import urllib.request
import urllib.error
import uuid
from pathlib import Path

from flask import Flask, jsonify, request, Response
from flask_cors import CORS

HOME = Path.home()
ROOT = Path(__file__).resolve().parent.parent              # ~/Desktop/Enrichments
TIER_DIR = ROOT / "25-49 Listings"                         # default tier
BATCHES_DIR = TIER_DIR / "batches"
ENRICHED_DIR = TIER_DIR / "enriched"
JOBS_DIR = ROOT / "listener" / "jobs"
LOGS_DIR = ROOT / "listener" / "logs"
ENRICH_SCRIPT = TIER_DIR / "enrich_batch.py"
PYTHON = "/usr/local/bin/python3.11" if Path("/usr/local/bin/python3.11").exists() else "python3.11"

for d in (BATCHES_DIR, ENRICHED_DIR, JOBS_DIR, LOGS_DIR):
    d.mkdir(parents=True, exist_ok=True)

app = Flask(__name__)
CORS(app, origins=[
    "https://yonatanibragimov.github.io",
    "http://localhost",
    "http://127.0.0.1",
], supports_credentials=False)

JOBS = {}  # in-memory job state; cleared on restart but files persist
JOBS_LOCK = threading.Lock()


def job_paths(job_id):
    return {
        "input":    BATCHES_DIR / f"job_{job_id}.csv",
        "output":   ENRICHED_DIR / f"job_{job_id}_enriched.csv",
        "log":      LOGS_DIR / f"job_{job_id}.log",
        "state":    JOBS_DIR / f"job_{job_id}.json",
    }


def save_state(job_id):
    with JOBS_LOCK:
        state = JOBS.get(job_id)
        if not state:
            return
        job_paths(job_id)["state"].write_text(json.dumps(state, default=str))


def load_state(job_id):
    p = job_paths(job_id)["state"]
    if p.exists():
        return json.loads(p.read_text())
    return None


# ─── progress parsing ────────────────────────────────────────────────────────

LEAD_START = re.compile(r"^\[(\d+)/(\d+)\] ─+$")
COMPANY    = re.compile(r"^\s*🔍 (.+)$")
BATCH_DONE = re.compile(r"^\s*BATCH COMPLETE:")


def tail_worker(job_id, proc):
    """Read stdout of enrich_batch.py line by line, update job state."""
    paths = job_paths(job_id)
    with open(paths["log"], "w") as log:
        for raw in iter(proc.stdout.readline, b""):
            line = raw.decode("utf-8", errors="replace")
            log.write(line); log.flush()

            m = LEAD_START.match(line.rstrip())
            if m:
                with JOBS_LOCK:
                    JOBS[job_id]["current"] = int(m.group(1))
                    JOBS[job_id]["total"]   = int(m.group(2))
                save_state(job_id)
                continue
            mc = COMPANY.match(line.rstrip())
            if mc:
                with JOBS_LOCK:
                    JOBS[job_id]["last_company"] = mc.group(1).strip()
                save_state(job_id)
                continue
            if BATCH_DONE.match(line):
                with JOBS_LOCK:
                    JOBS[job_id]["status"] = "completed"
                save_state(job_id)

    proc.wait()
    with JOBS_LOCK:
        rc = proc.returncode
        JOBS[job_id]["returncode"] = rc
        if JOBS[job_id].get("status") != "completed":
            JOBS[job_id]["status"] = "completed" if rc == 0 else "failed"
        JOBS[job_id]["finished_at"] = time.time()
    save_state(job_id)


# ─── endpoints ───────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    with JOBS_LOCK:
        running = sum(1 for j in JOBS.values() if j.get("status") == "running")
    return jsonify({
        "ok": True,
        "enrich_script": str(ENRICH_SCRIPT),
        "python": PYTHON,
        "jobs_total": len(JOBS),
        "jobs_running": running,
    })


# ─── Claude / Anthropic API reachability ────────────────────────────────────
# Cached so repeated popup opens don't burn tokens/quota.
_CLAUDE_CACHE = {"checked_at": 0, "result": None}
_CLAUDE_CACHE_TTL = 60  # seconds


def _check_claude():
    key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not key:
        return {"ok": False, "reason": "no_api_key",
                "hint": "Set ANTHROPIC_API_KEY in the listener environment to enable Claude API checks."}
    if not key.startswith("sk-ant-"):
        return {"ok": False, "reason": "bad_key_format"}

    body = json.dumps({
        "model": "claude-haiku-4-5-20251001",
        "max_tokens": 1,
        "messages": [{"role": "user", "content": "ping"}],
    }).encode("utf-8")

    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=body,
        method="POST",
        headers={
            "x-api-key": key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
    )
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=4) as resp:
            latency = int((time.time() - t0) * 1000)
            data = json.loads(resp.read().decode("utf-8"))
            return {"ok": True, "model": data.get("model", ""), "latency_ms": latency}
    except urllib.error.HTTPError as e:
        if e.code == 401:
            return {"ok": False, "reason": "unauthorized", "status": 401}
        return {"ok": False, "reason": f"http_{e.code}", "status": e.code}
    except urllib.error.URLError as e:
        return {"ok": False, "reason": "network", "error": str(e.reason)}
    except Exception as e:
        return {"ok": False, "reason": "error", "error": str(e)}


@app.get("/claude/ping")
def claude_ping():
    now = time.time()
    force = request.args.get("force") == "1"
    if not force and _CLAUDE_CACHE["result"] and (now - _CLAUDE_CACHE["checked_at"]) < _CLAUDE_CACHE_TTL:
        return jsonify({**_CLAUDE_CACHE["result"], "cached": True,
                        "age_sec": int(now - _CLAUDE_CACHE["checked_at"])})
    result = _check_claude()
    _CLAUDE_CACHE["result"] = result
    _CLAUDE_CACHE["checked_at"] = now
    return jsonify({**result, "cached": False})


# ─── Claude Code (OAuth CLI) reachability ───────────────────────────────────
# Uses the `claude` binary on PATH + `claude auth status` (exit 0 iff logged in).
# No billed API calls, no key required.
_CC_CACHE = {"checked_at": 0, "result": None}
_CC_CACHE_TTL = 30  # seconds — cheaper than API ping, fresher data


def _find_claude_bin():
    # shutil.which honors PATH; LaunchAgents typically have a stripped PATH so
    # also probe a few common install locations.
    candidates = [
        shutil.which("claude"),
        "/opt/homebrew/bin/claude",
        "/usr/local/bin/claude",
        str(Path.home() / ".local/bin/claude"),
        str(Path.home() / ".claude/local/claude"),
    ]
    for c in candidates:
        if c and Path(c).exists() and os.access(c, os.X_OK):
            return c
    return None


def _run(cmd, timeout=5):
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return p.returncode, (p.stdout or "").strip(), (p.stderr or "").strip()
    except subprocess.TimeoutExpired:
        return 124, "", "timeout"
    except FileNotFoundError:
        return 127, "", "not found"
    except Exception as e:
        return 1, "", str(e)


def _check_claude_code():
    path = _find_claude_bin()
    if not path:
        return {"ok": False, "reason": "not_installed",
                "hint": "Install Claude Code, then reload the listener."}

    # Version
    rc, out, err = _run([path, "--version"])
    version = out.split()[-1] if (rc == 0 and out) else ""

    # Auth status — exits 0 iff logged in
    rc_auth, out_auth, err_auth = _run([path, "auth", "status"])
    authed = rc_auth == 0
    if not authed:
        return {"ok": False, "reason": "not_authenticated", "path": path, "version": version,
                "hint": "Run `claude` in a terminal once to log in, then refresh."}

    return {"ok": True, "path": path, "version": version}


@app.get("/auth/claude-code/ping")
def claude_code_ping():
    now = time.time()
    force = request.args.get("force") == "1"
    if not force and _CC_CACHE["result"] and (now - _CC_CACHE["checked_at"]) < _CC_CACHE_TTL:
        return jsonify({**_CC_CACHE["result"], "cached": True,
                        "age_sec": int(now - _CC_CACHE["checked_at"])})
    result = _check_claude_code()
    _CC_CACHE["result"] = result
    _CC_CACHE["checked_at"] = now
    return jsonify({**result, "cached": False})


@app.post("/enrich")
def enrich():
    """
    Accept a scored CSV, write it to batches/, spawn enrich_batch.py.
    Body: { "filename": "batch_01.csv", "csv": "Rank,Licensee Name,..." }
    Returns: { "job_id": "...", "status": "running" }
    """
    data = request.get_json(silent=True) or {}
    csv_text = data.get("csv", "")
    if not csv_text.strip():
        return jsonify({"error": "empty csv"}), 400

    # Validate it has the expected columns
    try:
        reader = csv.DictReader(io.StringIO(csv_text))
        headers = reader.fieldnames or []
    except Exception as e:
        return jsonify({"error": f"invalid csv: {e}"}), 400

    required = {"Licensee Name", "Owner Name", "Owner Email", "Owner LinkedIn", "Website", "Notes"}
    missing = required - set(headers)
    if missing:
        return jsonify({"error": f"missing columns: {sorted(missing)}"}), 400

    job_id = uuid.uuid4().hex[:10]
    paths = job_paths(job_id)
    paths["input"].write_text(csv_text)

    total = sum(1 for _ in csv.DictReader(io.StringIO(csv_text)))

    with JOBS_LOCK:
        JOBS[job_id] = {
            "id":           job_id,
            "status":       "running",
            "total":        total,
            "current":      0,
            "last_company": "",
            "started_at":   time.time(),
            "input":        str(paths["input"]),
            "output":       str(paths["output"]),
        }
    save_state(job_id)

    # Spawn enrich_batch.py
    proc = subprocess.Popen(
        [PYTHON, str(ENRICH_SCRIPT), str(paths["input"])],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        cwd=str(TIER_DIR),
        env={**os.environ, "PYTHONUNBUFFERED": "1"},
    )
    threading.Thread(target=tail_worker, args=(job_id, proc), daemon=True).start()

    return jsonify({"job_id": job_id, "status": "running", "total": total})


@app.get("/status/<job_id>")
def status(job_id):
    with JOBS_LOCK:
        state = dict(JOBS.get(job_id, {}))
    if not state:
        state = load_state(job_id) or {}
    if not state:
        return jsonify({"error": "unknown job"}), 404
    return jsonify(state)


@app.get("/result/<job_id>")
def result(job_id):
    paths = job_paths(job_id)
    if not paths["output"].exists():
        return jsonify({"error": "result not ready"}), 404
    return Response(
        paths["output"].read_bytes(),
        mimetype="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{paths["output"].name}"'},
    )


@app.get("/log/<job_id>")
def log(job_id):
    paths = job_paths(job_id)
    if not paths["log"].exists():
        return jsonify({"error": "no log"}), 404
    return Response(paths["log"].read_text(), mimetype="text/plain")


if __name__ == "__main__":
    port = int(os.environ.get("REVWHISPER_PORT", "5055"))
    app.run(host="127.0.0.1", port=port, threaded=True)
