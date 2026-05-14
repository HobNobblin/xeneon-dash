# Xeneon Dash

Xeneon Dash is a modular dashboard system for the Corsair Xeneon Edge. It runs a local web server and renders independently-written widgets
in a configurable grid layout on the 2560×720 display.

## Architecture

* core/server.py — a FastAPI backend that collects system metrics every second and broadcasts them over a WebSocket to all connected clients.
It also auto-discovers and serves widget files from the widgets/ directory, and mounts any per-widget backend routes automatically.
* core/kiosk.py — a GTK3 window using override_redirect (via Gtk.WindowType.POPUP) to bypass GNOME's window manager and place itself at the
exact X11 coordinates of the Xeneon. It embeds a WebKit2GTK webview that loads the dashboard.
* core/frontend/ — the grid shell. index.html is the outer page; grid.js reads config.yaml via the API, builds a CSS Grid, and loads each
configured widget into its own <iframe>. It opens a WebSocket and forwards metric ticks to all iframes via postMessage.
* core/frontend/xeneon.js — the widget SDK. Any widget can include this script and call xeneon.on("tick", metrics => { ... }) to receive live
data, and xeneon.config to read its config block from config.yaml.

# Widgets

Each widget is a self-contained directory under widgets/ with a manifest.json, an index.html, and an optional backend.py. Adding a widget
means dropping a folder and adding an entry to config.yaml — no changes to the core app needed. 

The cpu widget displays per-core usage as animated vertical bars with a colour gradient from blue (idle) to red (loaded).

Layout is configured in config.yaml as a named grid with configurable column/row counts. Each widget entry specifies its grid position and
span.

Launch is a single ./launch.sh that bootstraps the venv on first run, kills any leftover server, starts the backend, maps touch input to
DP-1, and opens the kiosk window on the Xeneon.

# Dashboard Configuration

The application will serve a configuration page at http://localhost:8000/config to allow for widget placement and sizing. Upon saving the config on the web page changes will be saved to the config.yaml file.
