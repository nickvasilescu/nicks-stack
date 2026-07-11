# Hermes surfaces vs specialist desktop apps

## What to install for agent stacks (Dewey / Orgo)

| Want | Install | Skip |
|------|---------|------|
| Hermes orchestrates coding | Specialist **CLIs** + `coding-agent-routing` | Claude/Codex desktop for Hermes |
| Visual Hermes ops / config | `hermes dashboard` | Claude Desktop |
| Native Hermes Electron on box | `hermes desktop` / `gui` | Only if you use the GUI daily |
| Human Claude Chat/Cowork GUI | Claude Desktop (Linux beta) | Not required for Hermes |

Specialist **desktop** apps do not plug into Hermes skills. Hermes spawns **CLIs**.

## Claude Desktop on Linux

- Official beta: Ubuntu 22.04+ / Debian 12+, x64/arm64 via Anthropic apt.
- Chat / Cowork / Code tabs; Computer Use and dictation not in Linux beta.
- Separate from Claude Code CLI; same subscription can power both.
- On Orgo: needs usable display; Cowork wants ~8 GB RAM and a local VM (~4 GB while running). Tight on small agent VMs.
- **Do not** install Claude Desktop to "complete" multi-agent coding. Agent value is `claude` CLI.

## Codex Desktop

- Official: **macOS and Windows only**. Linux: notify form / unofficial wrappers.
- Linux path for Hermes: Codex **CLI** only.

## Hermes dashboard (preferred control plane on agent VMs)

```bash
# Long-lived daemon (terminal background=true, no notify_on_complete)
export PATH="/usr/local/bin:$HOME/.local/bin:$PATH"
hermes dashboard --no-open --port 9119
# Ready when log shows: HERMES_DASHBOARD_READY port=9119
# Open: http://127.0.0.1:9119
hermes dashboard --status
hermes dashboard --stop
```

- Default bind **127.0.0.1** (not public). Use Orgo browser localhost or SSH `-L 9119:127.0.0.1:9119`.
- Probe: `curl -sS -o /dev/null -w '%{http_code}' http://127.0.0.1:9119/` → expect 200. Unauthenticated API routes may 401 — expected.
- First start may build web assets; subsequent starts are fast if dist exists.

### Opening so the *user* can see it on Orgo (mandatory)

Do **not** claim visibility after only `browser_navigate` or CUA/scrot black frames.

1. `orgo-desktop doctor` green **and** nonblack screenshot (bytes ≫ 3KB). If black → `orgo-desktop-local` `references/black-framebuffer-recovery.md`.
2. `orgo-desktop open-url "http://127.0.0.1:9119"` (preferred over hand-rolled Chrome).
3. `orgo-desktop screenshot` → nonblack + window title `Hermes Agent - Dashboard`.
4. Tell user to refresh/reconnect noVNC if their stream is stale.
5. Dismiss Chrome "Restore pages?" with Escape if it appears.

Full recipe: skill `orgo-desktop-local` → `references/hermes-dashboard-on-orgo.md`.

Fallback hand-rolled Chrome (only if Desktop API down):

```bash
export DISPLAY=:99
google-chrome --no-sandbox --disable-dev-shm-usage --no-first-run \
  --user-data-dir=/tmp/chrome-dash-profile --disable-gpu \
  --window-size=1280,720 --window-position=0,0 \
  "http://127.0.0.1:9119"
```

**Pitfalls:**

- Bare `terminal` forbids shell `&`; use `background=true` for long-lived Chrome.
- Prefer **`orgo-desktop open-url`** when doctor is green.
- HTTP 200 + agent browser snapshot ≠ user-visible VNC.
- `Opening in existing browser session` → fresh `--user-data-dir` or careful PID kill (not `pkill -f chrome`).
- `inotify_init() failed: Too many open files` is noise if title/HTTP/orgo paint are good.

## Hermes desktop (Electron)

```bash
hermes desktop              # may npm install + package first run
hermes desktop --build-only
hermes desktop --skip-build
```

Heavier than dashboard. Prefer dashboard on remote agent hosts unless user lives in Orgo GUI.

## Decision one-liner

Hermes brain + messaging + dashboard for ops; Claude/Codex/Grok **CLIs** for coding specialists; specialist desktop apps only for human preference, never as Hermes integration. Prefer Orgo local Desktop API over CUA for headed work on this host.
