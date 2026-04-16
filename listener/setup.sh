#!/usr/bin/env bash
# One-time setup for the always-on Rev Whisper listener.
# Run with:  bash setup.sh        (install)
#            bash setup.sh stop   (stop + unload)
#            bash setup.sh tail   (tail the logs)

set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
PLIST_SRC="$HERE/com.revwhisper.listener.plist"
PLIST_DST="$HOME/Library/LaunchAgents/com.revwhisper.listener.plist"
LABEL="com.revwhisper.listener"
LOGS="$HERE/logs"

# Pick a python3.11 that has pip. The browser-use venv's python3.11 ships
# without pip, so we prefer Homebrew's binary explicitly, then fall back.
pick_python() {
  for candidate in \
    /opt/homebrew/bin/python3.11 \
    /usr/local/bin/python3.11 \
    /opt/homebrew/opt/python@3.11/bin/python3.11; do
    if [ -x "$candidate" ] && "$candidate" -m pip --version >/dev/null 2>&1; then
      echo "$candidate"; return 0
    fi
  done
  # Last resort: try whatever python3.11 is on PATH, bootstrapping pip if needed
  if command -v python3.11 >/dev/null 2>&1; then
    local p; p="$(command -v python3.11)"
    if "$p" -m pip --version >/dev/null 2>&1; then echo "$p"; return 0; fi
    if "$p" -m ensurepip --default-pip >/dev/null 2>&1; then echo "$p"; return 0; fi
  fi
  return 1
}

cmd="${1:-install}"

case "$cmd" in
  install)
    PY="$(pick_python)" || { echo "✗ No usable python3.11 with pip found. Install via Homebrew: brew install python@3.11"; exit 1; }
    echo "→ Using Python: $PY"
    echo "→ Installing deps (flask, flask-cors)…"
    "$PY" -m pip install --user -r "$HERE/requirements.txt"

    # Rewrite the plist so ProgramArguments[0] matches the python we just used.
    sed -e "s|<string>/usr/local/bin/python3.11</string>|<string>$PY</string>|" \
        -e "s|<string>/opt/homebrew/bin/python3.11</string>|<string>$PY</string>|" \
        "$PLIST_SRC" > "$PLIST_SRC.tmp"
    mv "$PLIST_SRC.tmp" "$PLIST_SRC"

    mkdir -p "$LOGS" "$HOME/Library/LaunchAgents"
    cp "$PLIST_SRC" "$PLIST_DST"

    # Unload if already loaded (idempotent reinstall)
    launchctl unload "$PLIST_DST" 2>/dev/null || true
    launchctl load "$PLIST_DST"

    sleep 1
    echo
    echo "→ Health check:"
    curl -s http://127.0.0.1:5055/health || echo "  (not responding yet — wait a few seconds and retry)"
    echo
    echo "✓ Listener installed. It will auto-start at login."
    echo "  Stop:   bash setup.sh stop"
    echo "  Logs:   bash setup.sh tail"
    ;;

  stop|uninstall)
    launchctl unload "$PLIST_DST" 2>/dev/null || true
    if [ "$cmd" = "uninstall" ]; then
      rm -f "$PLIST_DST"
      echo "✓ Uninstalled."
    else
      echo "✓ Stopped (will restart on next login unless you uninstall)."
    fi
    ;;

  tail)
    touch "$LOGS/listener.out.log" "$LOGS/listener.err.log"
    tail -f "$LOGS/listener.out.log" "$LOGS/listener.err.log"
    ;;

  status)
    launchctl list | grep "$LABEL" || echo "not loaded"
    curl -s http://127.0.0.1:5055/health || echo "  (not responding)"
    ;;

  *)
    echo "Usage: bash setup.sh [install|stop|uninstall|tail|status]"
    exit 1
    ;;
esac
