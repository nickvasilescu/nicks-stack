#!/bin/bash
# Nick's Stack — autostart launcher for the first-boot onboarding.
# Opens the guided setup in a terminal on the desktop, unless already done.
export DISPLAY="${DISPLAY:-:99}"
STAMP=/var/lib/orgo/nicks-stack-onboarded
[ -f "$STAMP" ] && exit 0
ONBOARD=/usr/local/bin/nicks-stack-onboard.sh
if command -v xfce4-terminal >/dev/null 2>&1; then
  exec xfce4-terminal --title="Nick's Stack Setup" --geometry=100x32 --command="$ONBOARD"
elif command -v x-terminal-emulator >/dev/null 2>&1; then
  exec x-terminal-emulator -e "$ONBOARD"
elif command -v xterm >/dev/null 2>&1; then
  exec xterm -T "Nick's Stack Setup" -geometry 100x32 -e "$ONBOARD"
fi
# No terminal emulator: run headless. The Telegram QR still opens in Chrome;
# Nous-auth prompts land in the log for the `hermes` terminal user to follow.
mkdir -p /var/log/orgo
exec "$ONBOARD" >/var/log/orgo/nicks-stack-onboard.log 2>&1
