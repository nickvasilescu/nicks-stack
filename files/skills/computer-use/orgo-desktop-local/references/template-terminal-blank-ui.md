# Orgo browser terminal blank / black / not connecting

## Symptom

User opens Orgo web UI Terminal / Hermes tab: pure black, blank, or infinite spinner.
Desktop VNC may still paint. Computer API screenshot/bash and edge terminal WS may
still return prompts. **Do not treat WS-green as UI-green.**

## User-verified recovery (2026-07-09) — do this first

Confirmed working on live Minions computer after long template-tab blackouts:

1. **Restart the computer** (Orgo API `POST /computers/{id}/restart`).
   - Rotates **VNC password**. Old browser WebSocket tokens die immediately.
2. Ensure hermes tmux matches **agentmail contract** (see below). If session was
   heal-owned / nested-shell, recreate cleanly:
   ```bash
   tmux kill-server 2>/dev/null || true
   # exact agentmail shape:
   tmux new-session -d -s hermes -c /root
   chmod 0770 /tmp/tmux-0/default
   ```
3. User **hard-refreshes** the Orgo desktop page (Cmd/Ctrl+Shift+R).
   - Soft reload keeps a dead WS → still black even when the VM shell is healthy.
4. Reopen Terminal / Hermes panel.

If the side panel is still black after that: use the **desktop stream Terminal**
(`xfce4-terminal`) or the **default** shell tab (no `session=`). Both are valid
product paths.

## Two different "terminals" (do not conflate)

| Surface | What it is | When it fails |
|---------|------------|---------------|
| **Side panel Terminal / Hermes tab** | Browser WS → PTY or `session=<name>` tmux | Can black with healthy VM |
| **Desktop stream Terminal app** | Real `xfce4-terminal` on VNC | Independent; always open as fallback |

Screenshot the desktop (`GET /computers/{id}/screenshot`) before arguing the box is dead.

## How attach works

```text
wss://www.orgo.ai/desktops/{instance_id}/ws/terminal?token={vnc_password}&cols=…&rows=…
optional: &session=hermes   # template tab → tmux session by name
```

| Fact | Detail |
|------|--------|
| Token | **VNC password** from `GET /computers/{id}/vnc-password` |
| Rotates | **Every restart** — hard refresh required after restart |
| `token=template-build` | Edge WS **closes** immediately; never use for attach |
| Default (no session) | Often `root@orgo-desktop:/#` even when template sessions exist |
| `session=hermes` | tmux attach; may emit alternate-screen CSI (`?1049h`) |

Docs: https://docs.orgo.ai/api-reference/computers/terminal

**If WS returns a prompt but the browser panel is black: frontend attach / stale token, not missing Hermes.**

## Agentmail contract (gold — do not drift)

Orgo generates `/usr/local/bin/orgo-tmux-startup.sh` from `template.terminal[]`.
Working agentmail body is **only**:

```bash
#!/bin/bash
# orgo-generated — do not edit
set +e
if ! tmux has-session -t 'hermes' 2>/dev/null; then
  tmux new-session -d -s 'hermes' -c '/root'
fi
```

Template terminal entry:

```json
{ "name": "hermes", "title": "Hermes", "description": "…", "cwd": "/root" }
```

**No `run` field.** Adding `"run": "bash -l"` makes Orgo emit:

```bash
tmux new-session -d -s 'hermes' -c '/root'
tmux send-keys -t 'hermes' 'bash -l' C-m   # nested shell → black tab
```

Observed healthy markers (agentmail):

| Marker | Working | Broken (common) |
|--------|---------|-----------------|
| Socket | `srwxrwx---` (**0770**), root:root | `srw-rw----` (**0660**) after supervisord heal |
| Pane parent | `tmux new-session …` with **ppid=1** (orgo-init) | under `SUPERVISOR_PROCESS_NAME=orgo-terminal-heal` |
| Pane cmd | plain `-bash` | nested `bash -l` / garbage from doctor spam |
| Clients | UI attach → `attached=1` | `attached=0` forever if user never refreshes |

## Boot race (why post-hoc fix works)

Orgo first-create init order (observed):

1. Long `app_install` (~60s+)
2. Hooks (`first_boot` / `every_boot`) — **before** terminals
3. `tmux_startup` runs `orgo-tmux-startup.sh`
4. Often a **second** `orgo-init` ~30–60s later that runs `tmux_startup` again

### Hook / heal anti-patterns

- **Do not create/touch `hermes` in hooks** (hooks run before `tmux_startup`).
- **Do not kill-server / kill-session under supervisord** and recreate as a "heal".
  That replaces orgo-init's tmux server (wrong socket mode / ownership). The
  post-hoc fix that worked was **agentmail-identical recreate**, not "more heal".
- Soft heal (optional): wait for session, `chmod 0770` socket, paint **one** short
  line if pane empty. Never dump doctor JSON into the pane.
- Bare `hermes plugins enable` without `--no-allow-tool-override` hangs on "Grant it?".

## Root causes checklist

1. Hung interactive enable as tab `run` / bootstrap process
2. One-shot `run` (validate) exits → dead tab
3. `terminal.run: bash -l` → nested shell in generated startup script
4. Heal kill + supervisord-owned tmux server (socket 0660)
5. Empty login bash paint until key/resize (older 0.1.6)
6. **Stale VNC token after restart** (UI spinner / black) — **#1 real user fix**
7. Soft page reload instead of hard refresh after restart
8. User looking at side panel while only desktop stream has a shell

## Diagnosis (run for the computer_id)

```bash
# On VM
cat /usr/local/bin/orgo-tmux-startup.sh
ls -la /tmp/tmux-0/default
tmux ls -F 'name=#{session_name} attached=#{session_attached}'
tmux list-panes -t hermes -F 'pid=#{pane_pid} cmd=#{pane_current_command}'
# parent of pane pid should be "tmux new-session …" ppid 1 when healthy
tmux capture-pane -t hermes -p -S -20
# Outside
curl -sS -H "Authorization: Bearer $ORGO_API_KEY" \
  "https://www.orgo.ai/api/computers/$CID/vnc-password"
# WS with current password + optional session=hermes
# Computer screenshot: is desktop Terminal open?
```

## Product strategies

| Strategy | When |
|----------|------|
| Agentmail single tab + **no `run`** + no aggressive heal | Preferred named Hermes tab (`@0.3.4+`) |
| Desktop `xfce4-terminal` autostart | Always as fallback on VNC stream |
| Empty `terminal: []` | Only if named tab path is abandoned |
| Never multi-tab bootstrap/validate | Always |

```bash
hermes plugins enable orgo-desktop-local --no-allow-tool-override
```

## Operator instructions for users

1. After **any** restart: hard-close tab or hard-refresh; reopen desktop URL.
2. Wait for ready / second init (~20–30s after first boot) before judging the tab.
3. If Hermes tab black: hard refresh → default shell tab → desktop Terminal window.
4. Next spins: **`default/hermes-orgo-desktop-local@0.3.4`** (or newer with same contract).

## Product refs

| Ref | Notes |
|-----|--------|
| **`@0.3.4`** | Prefer: agentmail terminal (no `run`), soft heal only, desktop terminal fallback |
| `@0.3.3` | Empty template terminals + desktop terminal |
| `@0.3.0`–`@0.3.2` | Agentmail-shaped; older heal may kill session — avoid for new spins |
| `@0.2.x` | WS ok; incomplete launch UX |
| `@0.1.x` | Do not recommend |

## Related

- `references/playground-401-diagnostics.md`
- `references/e2e-template-validation.md`
- `orgo-cloud-computers` → `references/template-metal-authoring.md`
- https://github.com/nickvasilescu/agentmail-agent
- https://github.com/nickvasilescu/nicks-stack
