#!/bin/bash
# ==========================================================================
# Nick's Stack — first-boot onboarding (runs on the desktop, once)
# ==========================================================================
# Walks a new user through the steps that need a human:
#   1. Nous model auth   (device-code — required for the agent to think)
#   2. Telegram bot      (scan a QR — the signature onboarding)
#   3. 1Password vault   (optional — one service-account token unlocks the
#                         whole key map in config.yaml's secrets block)
#   4. next-steps for AgentMail / AgentCard / Composio / AgentPhone /
#      Latitude / Orgo / X / honcho
#
# Launched by an XFCE autostart entry inside a terminal. Idempotent: each
# step is skipped once satisfied, so re-running only does what's left.
set +e
export HOME=/root
export HERMES_HOME=/root/.hermes
export DISPLAY="${DISPLAY:-:99}"
export PATH=/usr/local/bin:/root/.local/bin:/root/.hermes/bin:/usr/bin:/bin:$PATH

VENV_PY=/usr/local/lib/hermes-agent/venv/bin/python
ENV_FILE="$HERMES_HOME/.env"
OP_ENV="$HERMES_HOME/.op.env"
STAMP=/var/lib/orgo/nicks-stack-onboarded
mkdir -p /var/lib/orgo "$HERMES_HOME"

hr() { printf '\n\033[1;36m%s\033[0m\n' "────────────────────────────────────────────────────────"; }
say() { printf '\033[1;32m%s\033[0m\n' "$*"; }

clear 2>/dev/null
say "  Welcome to Nick's Stack — Hermes agent setup"
hr

# --- 1. Nous model auth ----------------------------------------------------
if [ ! -s "$HERMES_HOME/auth.json" ]; then
  say "Step 1/4 — Connect your Nous account (model: gpt-5.5)"
  echo "A device-code sign-in will open. Follow the URL + code it prints."
  echo "(Prefer ChatGPT? Later run: hermes auth add openai-codex, then set"
  echo " model.default: gpt-5.6-sol / provider: openai-codex in config.yaml.)"
  echo
  hermes auth add nous --type oauth
  echo
  if [ -s "$HERMES_HOME/auth.json" ]; then
    # 1-token sanity call: a zero-credit Nous account 404s on every model
    # call while everything looks green — fail loudly here, not silently.
    echo "Verifying the model can think (1-token test call)…"
    if hermes -z "Reply with exactly: ok" >/tmp/nicks-stack-modelcheck 2>&1 \
       && grep -qi "ok" /tmp/nicks-stack-modelcheck; then
      say "Model check passed ✓"
    else
      printf '\033[1;31m%s\033[0m\n' "Model test call FAILED — most often a Nous account with zero credits."
      echo "Add credits at portal.nousresearch.com, or connect ChatGPT instead:"
      echo "  hermes auth add openai-codex"
    fi
  fi
else
  say "Step 1/4 — Model account already connected ✓"
fi

# --- 2. Telegram bot via QR ------------------------------------------------
if ! grep -q '^TELEGRAM_BOT_TOKEN=..' "$ENV_FILE" 2>/dev/null; then
  hr
  say "Step 2/4 — Create your Telegram bot (scan the QR)"
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
  say "Step 2/4 — Telegram bot already connected ✓"
fi

# --- 3. 1Password (optional, but it IS the stack's secret plane) -----------
hr
if [ -s "$OP_ENV" ]; then
  say "Step 3/4 — 1Password already connected ✓"
else
  say "Step 3/4 — Connect 1Password (optional, recommended)"
  cat <<'OPINTRO'
  One service-account token unlocks every key this stack knows about:
  config.yaml maps 17 env vars to op://Hermes/Hermes Agent Secrets/<FIELD>.
  Setup (once, on 1password.com): create vault "Hermes" -> a Secure Note
  named "Hermes Agent Secrets" -> add fields named exactly like the env
  vars (see ~/.hermes/.env key contract) -> create a service account that
  can read vault "Hermes".
OPINTRO
  printf '  Paste your service-account token (ops_…) or press Enter to skip: '
  read -r OPTOK
  if [ -n "$OPTOK" ]; then
    umask 077
    printf 'OP_SERVICE_ACCOUNT_TOKEN=%s\n' "$OPTOK" > "$OP_ENV"
    unset OPTOK
    python3 /usr/local/bin/nicks-stack-op-enable || true
    echo "Checking…"
    hermes secrets onepassword status || true
    supervisorctl restart hermes-gateway 2>/dev/null || true
    say "1Password wired — keys resolve at every hermes start."
  else
    echo "Skipped. Re-run this setup any time, or: echo 'OP_SERVICE_ACCOUNT_TOKEN=ops_…' > ~/.hermes/.op.env"
  fi
fi

# --- 4. The rest of the stack (agent-assisted) ------------------------------
hr
say "Step 4/4 — The rest of your stack"
cat <<'NEXT'
  Everything below can also be done by just TELLING YOUR AGENT in chat —
  it has skills for each of these and installs its own keys.

  • AgentMail (the agent's email): put AGENTMAIL_API_KEY (am_…) in 1Password
      or ~/.hermes/.env, then ask the agent to create its inbox and save it
      as AGENTMAIL_INBOX. Console: console.agentmail.to
  • AgentCard (the agent's payment card): needs AgentMail first (magic codes
      land in the inbox). Ask the agent to run its `agentcard-hermes-setup`
      skill — it completes the OAuth itself (hermes mcp login agent-cards).
  • Composio (1000+ apps): COMPOSIO_CONSUMER_KEY (ck_…) from app.composio.dev.
  • AgentPhone (SMS/iMessage): set AGENTPHONE_API_KEY + AGENTPHONE_AGENT_ID
      (+ AGENTPHONE_NUMBER_ID); the webhook bridge starts on the next resume
      — no cron. Health: curl -s localhost:8787/health
  • Latitude (tracing + MCP): LATITUDE_API_KEY + LATITUDE_PROJECT.
  • Orgo (self-operation): ORGO_API_KEY + this VM's ORGO_DEFAULT_COMPUTER_ID
      (find it in the orgo.ai dashboard URL of this computer).
  • Linear: ask the agent to run  hermes mcp login linear
  • X / Twitter: X_APP_ONLY_BEARER_TOKEN enables the app-only MCP; for the
      full user-context xapi server see the x-mcp-integration skill.
  • honcho memory: HONCHO_API_KEY, then set memory.provider: honcho in
      ~/.hermes/config.yaml and restart the gateway.

  Keys land automatically: parked MCP servers revive within 5 minutes of a
  key appearing (or instantly via the /mcp command in chat).
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
