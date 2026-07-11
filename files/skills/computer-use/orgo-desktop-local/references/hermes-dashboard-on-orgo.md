# Hermes dashboard on co-located Orgo

## Start (long-lived)

```bash
hermes dashboard --no-open --port 9119
# Ready marker: HERMES_DASHBOARD_READY port=9119
# Bind is loopback: http://127.0.0.1:9119
```

Status / stop:

```bash
hermes dashboard --status
hermes dashboard --stop
```

## Open so the *user* can see it (mandatory path)

Do **not** claim the user can see the dashboard after only:

- `browser_navigate` (agent browser stack, not VNC)
- CUA `computer_use` capture (often black / "no window matched" on Orgo)
- bare `google-chrome` without verifying paint

**Required sequence:**

1. `orgo-desktop doctor` green; if screenshot bytes ~2–3KB / pure black → follow `black-framebuffer-recovery.md` first.
2. `orgo-desktop open-url "http://127.0.0.1:9119"` (headed Chrome with `--no-sandbox`).
3. `orgo-desktop screenshot /tmp/desk.png` and confirm **nonblack** pixels + window title like `Hermes Agent - Dashboard`.
4. Tell the user to refresh/reconnect **Orgo noVNC** if their stream is stale.
5. Optional: dismiss Chrome "Restore pages?" with Escape.

## Pitfalls

- Dashboard process can be up (HTTP 200) while VNC paint is black — user sees nothing until framebuffer recovery + headed open-url.
- Do not `pkill -f chrome` from a shell argv that contains the word `chrome` (can kill the agent shell). Use the safe PID kill pattern in black-framebuffer recovery.
- Prefer one Chrome window; repeated open-url multiplies windows and desyncs focus.
- Auth on dashboard API routes (`/api/health` 401 without session) is normal; HTML `/` 200 is enough for UI load.
