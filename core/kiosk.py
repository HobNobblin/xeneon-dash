import os

# WebKit2GTK's DMA-BUF renderer uses GBM which is incompatible with NVIDIA
# proprietary drivers. Disable it so WebKit falls back to a working path.
os.environ["WEBKIT_DISABLE_DMABUF_RENDERER"] = "1"
os.environ["WEBKIT_DISABLE_COMPOSITING_MODE"] = "1"

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('WebKit2', '4.1')
from gi.repository import Gtk, WebKit2

# POPUP type sets override_redirect=True — bypasses GNOME's WM so the
# window lands at the exact X11 coordinates we specify
win = Gtk.Window(type=Gtk.WindowType.POPUP)
win.move(435, 1440)
win.resize(2560, 720)

webview = WebKit2.WebView()
settings = webview.get_settings()
settings.set_property("hardware-acceleration-policy",
                       WebKit2.HardwareAccelerationPolicy.NEVER)
webview.load_uri("http://localhost:8000")

win.add(webview)
win.connect('destroy', Gtk.main_quit)
win.show_all()
Gtk.main()
