#!/bin/bash
set -e
cd "$(dirname "$0")"

# Bootstrap venv on first run (checks for pip, not just the directory)
if [ ! -f .venv/bin/pip ]; then
  python3 -m venv .venv
  .venv/bin/pip install -q -r requirements.txt
fi

# Kill any leftover server from a previous run
fuser -k 8000/tcp 2>/dev/null || true

# Start the backend
.venv/bin/python core/server.py &
SERVER_PID=$!

# Wait until the server is accepting connections
until curl -sf http://localhost:8000/api/config > /dev/null 2>&1; do
  sleep 0.2
done

# Map touch input to the Xeneon display
# Adjust the xinput device ID if it changes (check with: xinput list)
xinput map-to-output 22 DP-1

# Launch Chromium in kiosk mode on the Xeneon
# Adjust --window-position to match your display layout (x offset = width of primary display)
python3 core/kiosk.py

# Kill server when Chromium exits
kill "$SERVER_PID" 2>/dev/null
