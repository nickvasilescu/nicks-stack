# Headless multi-CLI auth (specialists)

Hermes provider OAuth in `~/.hermes/auth.json` does **not** authenticate specialist CLIs. Each product has its own store. Use these recipes on remote/headless hosts (Orgo, VPS, no local browser).

## Auth stores

| CLI | Install (typical) | Login | Auth artifact | Smoke |
|-----|-------------------|-------|---------------|-------|
| Grok Build | `curl -fsSL https://x.ai/cli/install.sh \| bash` | `grok login --device-auth` | `~/.grok/auth.json` | `env -u XAI_API_KEY grok --no-auto-update -p "Say ok."` |
| Codex | `npm i -g @openai/codex` | `codex login --device-auth` | `~/.codex/auth.json` | git repo + `codex exec "Say ok"` (needs `pty=true` in Hermes) |
| Claude Code | `npm i -g @anthropic-ai/claude-code` | OAuth paste flow (below) | Claude creds / `CLAUDE_CODE_OAUTH_TOKEN` | `claude -p "Say ok" --max-turns 1` |

Optional Hermes skill for Grok orchestration: `yes | hermes skills install official/autonomous-ai-agents/grok` (noninteractive confirm).

Optional long-lived Claude token (generate once where browser OAuth works): `claude setup-token` → set `CLAUDE_CODE_OAUTH_TOKEN` in Hermes `.env`.

## Codex device auth

```bash
# Prefer background=true + notify_on_complete so the agent can surface URL/code without killing the waiter early
codex login --device-auth
# URL: https://auth.openai.com/codex/device + one-time code (~15 min)
codex login status   # expect: Logged in using ChatGPT
```

**Usage limit ≠ auth failure.** Inference may return "You've hit your usage limit … try again at <time>" after login succeeds. Mark Codex unavailable; fall back to Claude Code or Grok Build. Do not retry-loop.

## Grok device auth

```bash
grok login --device-auth
# URL https://accounts.x.ai/oauth2/device?user_code=XXXX + code
# Prefer SuperGrok OAuth over XAI_API_KEY for subscription path
env -u XAI_API_KEY grok --no-auto-update -p "Say ok."
```

## Claude OAuth paste (headless) — critical

Claude has **no** device-code flag comparable to Codex/Grok. Flow: CLI prints authorize URL with `code_challenge` + `state`, waits for user to paste `code#state`.

### Pitfall: background stdin is `/dev/null`

`terminal(background=true)` without a real PTY/FIFO makes `process(action='submit')` fail with "stdin not available". Writing the OAuth code to a dead/background process **invalidates PKCE** — codes are bound to that process's challenge. Killing the waiter forces a **new** browser URL. Mid-session SIGTERM notifications for killed waiters are noise; only the live state matters.

### Working recipe: `script` + FIFO

```bash
export PATH="/usr/local/bin:$HOME/.local/bin:$PATH"
rm -f /tmp/claude-auth.in /tmp/claude-auth.out /tmp/claude-auth.done
mkfifo /tmp/claude-auth.in

# Run as terminal(background=true, notify_on_complete=true). Hermes rejects bare `&` in foreground.
exec 3<>/tmp/claude-auth.in
script -q -f -c "claude auth login --claudeai" /tmp/claude-auth.out <&3
echo $? > /tmp/claude-auth.done
```

1. Read authorize URL from `/tmp/claude-auth.out` (`claude.com/cai/oauth/authorize?...&state=LIVE_STATE`).
2. Give the user **only that URL**. Tell them to ignore older auth links and SIGTERM notices from prior attempts.
3. User returns full paste (often `TOKEN#state`).
4. **Validate before inject:** the substring after `#` (if present) **must** equal the live `state=` from the waiting URL. If it does not match, do **not** inject. Restart clean login or tell the user they used a dead/old tab.
5. Inject into the live FIFO only:

```bash
printf '%s\n' 'PASTE_CODE_HERE' > /tmp/claude-auth.in
# wait until /tmp/claude-auth.done appears (exit 0) or timeout
claude auth status --text
# expect: Login method: Claude Max/Pro account, loggedIn true
claude -p "Reply with exactly: claude-ok" --max-turns 1
```

### Do not

- Reuse a paste code from a killed/expired login process
- Start concurrent `claude auth login` processes (orphans + wrong challenge)
- Inject a code whose `#state` does not match the live waiter
- Assume Hermes `xai-oauth` / `openai-codex` pool entries satisfy CLI login
- Combine `watch_patterns` with `notify_on_complete` (Hermes drops watch patterns as duplicate)

### Recovery when user pastes dead-session code

1. `pkill -f "claude auth login"` (and any leftover `script -q -f -c claude`)
2. Recreate FIFO + start one clean waiter
3. Surface the **new** URL only; require new browser approval
4. Inject only when state matches

## Pre-flight before routing to a specialist

```bash
command -v claude; command -v codex; command -v grok
claude auth status --text 2>&1 | head -5
codex login status 2>&1 | head -5
test -f ~/.grok/auth.json && echo grok-auth-ok
# Or full board:
bash ~/.hermes/skills/autonomous-ai-agents/coding-agent-routing/scripts/smoke-specialists.sh
```

If smoke fails with auth error → re-login. If smoke fails with usage limit → mark unavailable, fall back.

## Layer reminder

| Layer | Question | Example |
|-------|----------|---------|
| Hermes brain | Who powers Hermes? | `model.provider: xai-oauth` |
| Specialist CLI | Who runs the long coding solo? | `claude -p` / `codex exec` / `grok -p` |

These are independent. Configuring Hermes brain never replaces CLI auth.
