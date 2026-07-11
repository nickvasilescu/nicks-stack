#!/bin/bash
# ==========================================================================
# Nick's Stack — Hermes gateway wrapper
# ==========================================================================
# This is the FIXED version of the Hubert VM's broken supervised unit. On the
# source VM the gateway ran as user=orgo while inheriting HOME=/root (mode
# 0700), so its config-wait gate could never pass and the supervised gateway
# never actually started (it was hand-run in a tmux session that died on
# reboot). Here we run as root with HOME=/root and bridge BOTH env files, so
# the gateway is genuinely supervised, reboot-safe, and sees every key.
set +e
export HOME=/root
export HERMES_HOME=/root/.hermes
export PATH=/usr/local/bin:/root/.local/bin:/root/.hermes/bin:/usr/bin:/bin:/usr/sbin:/sbin:$PATH

# Wait for the baked config AND a completed Nous sign-in before starting. This
# keeps the supervised gateway dormant (not crash-looping) until the user runs
# the first-boot onboarding / `hermes auth`, then it comes up cleanly — an
# improvement over the source VM, where the gateway spun with no model creds.
until [ -f "$HERMES_HOME/config.yaml" ] && [ -s "$HERMES_HOME/auth.json" ]; do sleep 5; done

# Source the Orgo vault-injection target (/root/.env — may be absent) and
# Hermes' own env so the model-provider auth + integration keys are visible to
# `hermes gateway run` (it does NOT auto-export either file). ~/.hermes/.env is
# the canonical file Hermes reads; on_resume keeps it in sync with the vault.
set -a
[ -f /root/.env ] && . /root/.env
[ -f "$HERMES_HOME/.env" ] && . "$HERMES_HOME/.env"
set +a

# Lifetime flock: an Orgo boot race can start TWO supervisords, each spawning
# this service — twin gateways then SIGTERM each other via --replace every ~2s,
# forever (field-tested; build-recipe §9). Blocking flock parks the loser.
# --accept-hooks matches Dewey's launch line (plugins/hooks never prompt).
mkdir -p /var/lib/orgo
exec flock /var/lib/orgo/hermes-gateway.lock hermes gateway run --replace --accept-hooks
