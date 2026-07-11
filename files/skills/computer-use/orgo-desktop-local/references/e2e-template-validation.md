# E2E validation: hermes-orgo-desktop-local template

## Current product ref

```text
default/hermes-orgo-desktop-local@0.3.4
```

## Success criteria (required)

On the **target** VM (or Orgo MCP bash):

```bash
bash /opt/orgo-hermes-desktop-local/install/validate.sh
# exit 0, summary pass=N fail=0
```

Also required for **API honesty**:

```bash
cat /usr/local/bin/orgo-tmux-startup.sh
# must be agentmail-only: new-session -d -s hermes -c /root  (no send-keys bash -l)
ls -la /tmp/tmux-0/default
# prefer srwxrwx--- (0770)
tmux capture-pane -t hermes -p -S -20
# should show root@…# or a short banner without nested bash -l spam
```

Also required before claiming **web Terminal UI** works:

1. Edge WS with **current** VNC password returns a prompt (default and/or `session=hermes`).
2. User hard-refreshed after any restart.
3. If UI still black: desktop Terminal on VNC stream is an accepted working path.

Checks in validate.sh: Desktop API health, hermes PATH, plugin, client, CLI, skills,
config plugin+toolset, doctor ready+prefer local, non-trivial screenshot, local-first
skill text.

## Proven E2E / recovery

| Date | Ref / action | Computer | Notes |
|------|--------------|----------|-------|
| 2026-07-09 | `@0.1.4` | `7b31b2ec-…` | validate 12/12, MCP GUI; terminals hung/blank |
| 2026-07-09 | `@0.2.0` | `e79035d3-…` | capture banner without key; UI still flaky for user |
| 2026-07-09 | `@0.3.4` contract | `966f99a0-…` / `21197ea2` | **User verified UI works** after restart + agentmail session + hard refresh |

## Operator procedure (outside the VM)

```text
1. GET .../build → ready for @0.3.4
2. POST /computers template_ref=default/hermes-orgo-desktop-local@0.3.4
3. Confirm templateTerminals = [{name: hermes, title: Hermes}] (or empty if intentional)
4. orgo_bash: cat orgo-tmux-startup.sh; socket mode; capture-pane; validate.sh
5. orgo_screenshot non-black
6. If web Terminal black: restart computer → hard refresh → reopen panel
   (see references/template-terminal-blank-ui.md)
```

## Individual install

```bash
bash install/install-on-existing-hermes.sh   # uses --no-allow-tool-override
bash install/validate.sh
# full Hermes process restart for orgo_desktop_* model tools
```

## Do not claim done when

- Only schema validate / metal ready
- Only Dewey local package test
- WS green but user has not hard-refreshed after restart
- Interactive plugin prompt blocked bootstrap (log shows "Grant it?")
- `orgo-tmux-startup.sh` contains `send-keys … bash -l`
