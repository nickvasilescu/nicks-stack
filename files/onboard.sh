#!/bin/bash
# ==========================================================================
# Nick's Stack — first-boot onboarding (runs on the desktop, once)
# ==========================================================================
# Walks a new user through the only steps that need a human:
#   1. Nous model auth  (device-code — required for the agent to think)
#   2. Telegram bot     (scan a QR — the signature onboarding)
#   3. next-steps for Composio / AgentPhone / AgentMail / AgentCard / Latitude
#
# Launched by an XFCE autostart entry inside a terminal. Idempotent: each step
# is skipped once satisfied, so re-running only does what's left. Marks a stamp
# when Nous auth + Telegram are both done so it stops nagging.
set +e
export HOME=/root
export HERMES_HOME=/root/.hermes
export DISPLAY="${DISPLAY:-:99}"
export PATH=/usr/local/bin:/root/.local/bin:/root/.hermes/bin:/usr/bin:/bin:$PATH

VENV_PY=/usr/local/lib/hermes-agent/venv/bin/python
ENV_FILE="$HERMES_HOME/.env"
STAMP=/var/lib/orgo/nicks-stack-onboarded
mkdir -p /var/lib/orgo "$HERMES_HOME"

hr() { printf '\n\033[1;36m%s\033[0m\n' "────────────────────────────────────────────────────────"; }
say() { printf '\033[1;32m%s\033[0m\n' "$*"; }

clear 2>/dev/null
say "  Welcome to Nick's Stack — Hermes agent setup"
hr

# --- 1. Nous model auth ----------------------------------------------------
if [ ! -s "$HERMES_HOME/auth.json" ]; then
  say "Step 1/3 — Connect your Nous account (model: gpt-5.5)"
  echo "A device-code sign-in will open. Follow the URL + code it prints."
  echo
  hermes auth
  echo
else
  say "Step 1/3 — Nous account already connected ✓"
fi

# --- 2. Telegram bot via QR ------------------------------------------------
if ! grep -q '^TELEGRAM_BOT_TOKEN=..' "$ENV_FILE" 2>/dev/null; then
  hr
  say "Step 2/3 — Create your Telegram bot (scan the QR)"
  echo "A QR code opens in Chrome. Scan it with your phone, then tap"
  echo "'Create Bot' in Telegram. Your bot + allowlist are set automatically."
  echo
  "$VENV_PY" /usr/local/bin/nicks-stack-telegram-pair.py
  if grep -q '^TELEGRAM_BOT_TOKEN=..' "$ENV_FILE" 2>/dev/null; then
    say "Telegram connected — restarting the gateway to enable it…"
    supervisorctl restart hermes-gateway 2>/dev/null || \
      { [ -f "$HERMES_HOME/gateway.pid" ] && kill -USR1 "$(cat "$HERMES_HOME/gateway.pid")" 2>/dev/null; }
  fi
else
  say "Step 2/3 — Telegram bot already connected ✓"
fi

# --- 3. Optional integrations (next steps) ---------------------------------
hr
say "Step 3/3 — Optional integrations"
cat <<'NEXT'
  • Composio (1000+ apps): drop your consumer key (ck_…) as
      COMPOSIO_CONSUMER_KEY in ~/.hermes/.env  — or just tell the agent your
      key in chat and it will wire it. Then restart the gateway.
  • AgentPhone (SMS/iMessage auto-responder): set AGENTPHONE_API_KEY,
      AGENTPHONE_AGENT_ID, AGENTPHONE_NUMBER_ID (in the vault or ~/.hermes/.env);
      the SMS cron self-seeds on the next resume.
  • AgentMail: connect the agent_mail toolkit in Composio, or paste an am_ key.
  • AgentCard: run  `agent-cards signup`  (magic-link email → JWT).
  • Latitude tracing: set HERMES_LATITUDE_API_KEY + HERMES_LATITUDE_PROJECT.

  You can always just chat with the agent (Telegram or the `hermes` terminal)
  and hand it a key — it knows how to install its own credentials.
NEXT
hr

# Stamp only when the two required steps are done, so we stop auto-launching.
if [ -s "$HERMES_HOME/auth.json" ] && grep -q '^TELEGRAM_BOT_TOKEN=..' "$ENV_FILE" 2>/dev/null; then
  date -Iseconds > "$STAMP"
  say "Setup complete. This window won't reappear. Talk to your agent on Telegram!"
else
  say "Setup paused — re-open 'Nick's Stack Setup' from the desktop to finish."
fi
echo
read -r -p "Press Enter to close…" _
