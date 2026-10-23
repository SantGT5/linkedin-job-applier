#!/usr/bin/env bash
# Virtual display + VNC + noVNC, then the worker. Ports stay inside the compose network;
# nginx exposes /novnc/ only to logged-in users.
set -euo pipefail

rm -f /tmp/.X99-lock /tmp/.X11-unix/X99
# A fresh X cookie each start: only this container's processes can use the display, and
# python-xlib (PyAutoGUI) finds the credentials it expects.
export XAUTHORITY="$HOME/.Xauthority"
rm -f "$XAUTHORITY" && touch "$XAUTHORITY"
xauth -q -f "$XAUTHORITY" add :99 . "$(python -c 'import secrets; print(secrets.token_hex(16))')"
Xvfb :99 -screen 0 1920x1080x24 -nolisten tcp -auth "$XAUTHORITY" &
for _ in $(seq 1 50); do xdpyinfo -display :99 >/dev/null 2>&1 && break; sleep 0.1; done

# Plain desktop: no wallpaper helper (it pops an xmessage over Chrome), no toolbar.
mkdir -p "$HOME/.fluxbox"
printf 'background: none\n' > "$HOME/.fluxbox/overlay"
printf 'session.screen0.toolbar.visible: false\nsession.styleOverlay: %s/.fluxbox/overlay\n' "$HOME" > "$HOME/.fluxbox/init"
mkdir -p "$HOME/.fluxbox/bin"
printf '#!/bin/sh\nexit 0\n' > "$HOME/.fluxbox/bin/fbsetbg" && chmod +x "$HOME/.fluxbox/bin/fbsetbg"
PATH="$HOME/.fluxbox/bin:$PATH" fluxbox >/dev/null 2>&1 &
x11vnc -display :99 -auth "$XAUTHORITY" -forever -shared -nopw -localhost -rfbport 5900 -quiet -bg -o /tmp/x11vnc.log
websockify --web /usr/share/novnc 6080 localhost:5900 >/tmp/websockify.log 2>&1 &

mkdir -p "${DATA_DIR}/logs" "${DATA_DIR}/resumes/default" "${CHROME_PROFILE_DIR}"
exec python -m app.worker
