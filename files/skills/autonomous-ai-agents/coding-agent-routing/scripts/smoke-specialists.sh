#!/usr/bin/env bash
# Smoke-check coding specialists without dumping secrets.
set -euo pipefail
export PATH="/usr/local/bin:${HOME}/.local/bin:${HOME}/.grok/bin:${PATH:-}"

ok=0
fail=0
report() { printf '%s\n' "$*"; }

check_claude() {
  if ! command -v claude >/dev/null 2>&1; then report "claude: MISSING binary"; fail=$((fail+1)); return; fi
  if ! claude auth status --text 2>/dev/null | head -1 | rg -qi 'login|max|pro|claude'; then
    report "claude: NOT LOGGED IN"; fail=$((fail+1)); return
  fi
  out=$(timeout 90 claude -p "Reply with exactly: claude-ok" --max-turns 1 2>&1 | tail -5 || true)
  if printf '%s' "$out" | rg -q 'claude-ok'; then report "claude: OK"; ok=$((ok+1))
  else report "claude: AUTH-ish but smoke failed: ${out:0:200}"; fail=$((fail+1)); fi
}

check_codex() {
  if ! command -v codex >/dev/null 2>&1; then report "codex: MISSING binary"; fail=$((fail+1)); return; fi
  st=$(codex login status 2>&1 | head -1 || true)
  if ! printf '%s' "$st" | rg -qi 'logged in'; then report "codex: NOT LOGGED IN ($st)"; fail=$((fail+1)); return; fi
  d=$(mktemp -d)
  (cd "$d" && git init -q && git config user.email t@t && git config user.name t && echo x >r && git add r && git commit -q -m i)
  out=$(cd "$d" && timeout 120 codex exec "Reply with exactly: codex-ok" 2>&1 | tail -20 || true)
  rm -rf "$d"
  if printf '%s' "$out" | rg -qi 'usage limit'; then report "codex: LOGGED IN but USAGE LIMITED"; fail=$((fail+1))
  elif printf '%s' "$out" | rg -q 'codex-ok'; then report "codex: OK"; ok=$((ok+1))
  else report "codex: logged in; smoke unclear: ${out:0:200}"; fail=$((fail+1)); fi
}

check_grok() {
  if ! command -v grok >/dev/null 2>&1; then report "grok: MISSING binary"; fail=$((fail+1)); return; fi
  if [[ ! -f "${HOME}/.grok/auth.json" ]]; then report "grok: no ~/.grok/auth.json"; fail=$((fail+1)); return; fi
  out=$(env -u XAI_API_KEY timeout 90 grok --no-auto-update -p "Reply with exactly: grok-ok" 2>&1 | tail -10 || true)
  if printf '%s' "$out" | rg -q 'grok-ok'; then report "grok: OK"; ok=$((ok+1))
  else report "grok: smoke failed: ${out:0:200}"; fail=$((fail+1)); fi
}

check_dashboard() {
  code=$(curl -sS -o /dev/null -w '%{http_code}' --connect-timeout 2 http://127.0.0.1:9119/ 2>/dev/null || echo 000)
  if [[ "$code" == "200" ]]; then report "dashboard: OK http://127.0.0.1:9119"; ok=$((ok+1))
  else report "dashboard: not serving on :9119 (code=$code)"; fail=$((fail+1)); fi
}

check_claude
check_codex
check_grok
check_dashboard
report "summary: ok=$ok fail=$fail"
exit $([[ $fail -eq 0 ]] && echo 0 || echo 1)
