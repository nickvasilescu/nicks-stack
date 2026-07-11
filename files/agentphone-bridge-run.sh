#!/bin/bash
# ==========================================================================
# Nick's Stack — AgentPhone webhook-bridge wrapper (supervised entrypoint)
# ==========================================================================
# Same dormant-gate idiom as the gateway wrapper: the supervised service
# sleeps (does NOT crash-loop) until the two hard-required AgentPhone keys
# exist in ~/.hermes/.env, then execs the bridge under a lifetime flock
# (duplicate-supervisord defense — see build-recipe §9). On Dewey this
# bridge REPLACED the SMS polling cron: AgentPhone pushes events to the
# bridge on :8787, which self-provisions a cloudflared quick tunnel when
# AGENTPHONE_PUBLIC_URL is unset and registers the webhook itself.
#
# No env sourcing here on purpose — the bridge loads /root/.hermes/.env and
# /root/.hermes_agentphone_bridge/env itself (bridge file wins), exactly as
# on Dewey.
set +e
export HOME=/root
export PATH=/usr/local/bin:/root/.local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$PATH

E=/root/.hermes/.env

# Dormant until configured: both keys must be present and non-empty.
until grep -q '^AGENTPHONE_API_KEY=..' "$E" 2>/dev/null && \
      grep -q '^AGENTPHONE_AGENT_ID=..' "$E" 2>/dev/null; do sleep 15; done

mkdir -p /var/lib/orgo
exec flock /var/lib/orgo/agentphone-bridge.lock \
  /usr/bin/python3 /root/.hermes_agentphone_bridge/agentphone_bridge.py
