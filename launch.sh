#!/bin/bash
set -e
cd "$(dirname "$0")"

# Start the backend
python core/server.py &
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
chromium \
  --kiosk \
  --app=http://localhost:8000 \
  --window-position=1920,0 \
  --window-size=2560,720 \
  --disable-infobars \
  --noerrdialogs \
  --disable-session-crashed-bubble \
  --disable-restore-session-state \
  --disable-features=TranslateUI

# Kill server when Chromium exits
kill "$SERVER_PID" 2>/dev/null
