#!/usr/bin/env bash
# Store X app-only bearer from clipboard into xurl app profile.
# Never echoes the token. Safe to run from agent sessions.
set -euo pipefail
export PATH="${HOME}/.local/bin:${PATH}"
APP="${1:-hermes-x}"

tok=$(xclip -o -selection clipboard 2>/dev/null || true)
if [[ -z "${tok// }" ]]; then
  tok=$(xclip -o -selection primary 2>/dev/null || true)
fi
if [[ -z "${tok// }" ]]; then
  echo "ERROR: clipboard empty" >&2
  exit 2
fi
if [[ ${#tok} -lt 40 ]]; then
  echo "ERROR: clipboard content too short to be a bearer token (len=${#tok})" >&2
  exit 3
fi
tok=$(printf '%s' "$tok" | tr -d '\r\n' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
printf '%s' "$tok" | xurl auth app-only --app "$APP" -
printf '' | xclip -selection clipboard 2>/dev/null || true
printf '' | xclip -selection primary 2>/dev/null || true

status=$(xurl auth status 2>&1)
echo "$status" | sed -E 's/(AAAA[A-Za-z0-9%_-]{10,})/[REDACTED]/g; s/(Bearer[[:space:]]+)[A-Za-z0-9%_-]{20,}/\1[REDACTED]/g'

set +e
out=$(xurl --app "$APP" --auth app '/2/tweets/search/recent?query=from:XDevelopers&max_results=10' 2>&1)
ec=$?
set -e
echo "smoke_exit=$ec"
printf '%s' "$out" | sed -E 's/[A-Za-z0-9_%-]{40,}/[REDACTED]/g' | head -c 500
echo
if [[ $ec -eq 0 ]]; then
  echo "OK: bearer stored for $APP; app-only smoke succeeded (token not shown)"
else
  echo "WARN: store command completed; smoke failed (token not shown). Check plan/credits/auth."
fi
