---
name: orgo-cloud-computers
description: Use Orgo cloud computers via CLI and MCP.
version: 0.3.2
author: Hermes
platforms: [linux, macos]
metadata:
  hermes:
    tags: [Orgo, CloudComputers, MCP, CLI, RemoteExecution, GUI]
    related_skills: [computer-use, orgo-desktop-local]
---

# Orgo Cloud Computers

This skill configures and uses Orgo cloud computers through the Orgo CLI and the Orgo MCP server. It does not store API keys or replace task-specific judgment about whether to use a shell, GUI, file transfer, or an agent session. Prefer scriptable CLI/MCP actions before GUI driving; verify the target computer is running before acting.

For **customer Hermes deployments / pilots**, also load `managed-hermes-on-orgo`.

When Hermes is **on** the Orgo VM, load **`orgo-desktop-local`** and prefer loopback Desktop API for GUI/bash/screenshot.

**Sharing with others:** public fleet connector is GitHub MCP `nickvasilescu/orgo-mcp`. Same-box click/screenshot/bash is the Hermes plugin + CLI + skill (not MCP alone). See `orgo-desktop-local` → `references/packaging-and-sharing.md`. macOS operator UI is a separate product (`hermes-desktop-os1`).

## When to Use

- The user mentions Orgo, orgo.ai, Dewey, Minions, cloud computers, or a computer ID.
- The user asks to install, configure, test, or use the Orgo CLI.
- The user provides an Orgo MCP command such as `npx -y github:nickvasilescu/orgo-mcp`.
- The user asks whether Orgo is reachable via CLI or MCP.
- A task needs a remote Linux VM with shell, screenshot, GUI, upload/download, or one-shot agent execution.
- The user asks about **Orgo templates** / Forge images / launching from a template.

## Same-box routing (Hermes on the VM)

If Hermes is **inside** the Orgo desktop (hostname `orgo-desktop`, local
`http://127.0.0.1:8080/health` reports `orgo-desktop-api`), **do not** use
cloud Orgo MCP for screenshot/click/type/bash by default.

**Load and follow skill `orgo-desktop-local`.** Prefer:

1. Model tools `orgo_desktop_*` (plugin toolset `orgo_desktop`) after a new session, or
2. CLI `orgo-desktop` (`~/.local/bin/orgo-desktop`)

```bash
orgo-desktop doctor    # must be ready
orgo-desktop smoke
orgo-desktop screenshot /tmp/desk.png
orgo-desktop bash '…'
orgo-desktop click X Y
```

Auth is **`VNC_PASSWORD` / per-VM vnc_password**, not `ORGO_API_KEY`.

Keep Orgo MCP / cloud API for: multi-computer fleet, ensure_running,
create/clone/resize, dashboard URL, and actions against a **different**
computer id.

Still use this skill (cloud MCP) when driving a remote Orgo computer Hermes
is not inside, when local doctor is red, or for lifecycle/dashboard only.

**CUA / Hermes `computer_use` is secondary on same-box Orgo** — optional a11y
enrichment only, never readiness, never the first screenshot path when paint may
be black. Prefer order: local Desktop API → `browser_*` for DOM → cloud MCP for
other VMs → CUA last. Sentiment: Orgo local first, CUA second, cloud MCP third
(other hosts only). See `orgo-desktop-local` v1.4+ and `computer-use` v2.1+.

## Prerequisites

- Orgo API key available as `ORGO_API_KEY` in the environment or Hermes `.env`.
- Optional default target computer as `ORGO_DEFAULT_COMPUTER_ID`.
- Node/npx available for the local stdio MCP server. The Orgo installer can install Node under `~/.orgo/node`.
- Hermes MCP client available when configuring Orgo as an MCP server.
- If a target name is ambiguous, use the computer ID rather than the display name.

## How to Run

Use the `terminal` tool for CLI setup and verification. Use Orgo MCP tools directly after `hermes mcp test orgo` succeeds and the session has reloaded MCP servers.

**Routing:**

- Co-located Hermes-on-Orgo: local Desktop API (`orgo-desktop-local`) for screenshot/click/type/bash
- Remote computer: Orgo MCP screenshot/click/type or MCP bash/exec
- Templates list/publish: REST via `terminal` (see Templates)

## Quick Reference

```text
curl -fsSL https://orgo.ai/install.sh | bash
export PATH="$HOME/.local/bin:$HOME/.orgo/node/bin:$PATH"
export ORGO_API_KEY=***
export ORGO_DEFAULT_COMPUTER_ID=<computer-id>
orgo computers list
orgo ssh "<computer-name>"
orgo run "<task>" --computer "<computer-name>" --json
orgo agent --computer "<computer-name>"
hermes mcp add orgo --command npx --env 'ORGO_API_KEY=${ORGO_API_KEY}' ORGO_DEFAULT_COMPUTER_ID='${ORGO_DEFAULT_COMPUTER_ID}' --args -y github:nickvasilescu/orgo-mcp
hermes mcp test orgo
```

Hosted MCP alternative:

```text
https://orgo-mcp.onrender.com/mcp
```

### Templates (REST + MCP image field)

```text
GET  https://www.orgo.ai/api/templates/global
GET  https://www.orgo.ai/api/templates
GET  https://www.orgo.ai/api/templates/{namespace}/{name}/{version}
GET  https://www.orgo.ai/api/template-schema
POST https://www.orgo.ai/api/templates/validate
POST https://www.orgo.ai/api/templates?auto_build=true

MCP orgo_create_computer.image = "system/hermes-agent@1.0.0" | "default/name@semver"
REST POST /computers template_ref = same form
```

CLI has **no** `orgo templates` and **no** `computers create --template`.

## Procedure

1. Install or locate the CLI via `terminal`.
2. Persist PATH for `~/.local/bin` if needed.
3. Save credentials in Hermes `.env` without printing them.
4. Confirm the target computer is running (`orgo computers list` or MCP list/get) before acting.
5. Configure Orgo MCP (stdio `npx -y github:nickvasilescu/orgo-mcp` preferred).
6. Verify CLI + `hermes mcp test orgo`.
7. Choose control mode:
   - **Same-box:** `orgo-desktop-local` / `orgo_desktop_*` / `orgo-desktop` CLI
   - CLI ssh / run / agent (remote)
   - MCP bash/exec for scriptable remote work
   - MCP screenshot/click/type for remote GUI (see GUI desktop driving)
   - MCP or REST file upload/export for transfer
8. When launching from a template/image:
   - List refs via REST global/account endpoints
   - Create via MCP `image` or REST `template_ref`
   - **Immediately verify software expected from the template is present** (e.g. `which hermes`)
9. Headed watch sessions: `orgo_ensure_running` + `orgo_get_computer` first; paste `connection_url` (else `url`) before driving UI.

## GUI desktop driving (headed Orgo)

For live VNC/desktop streams (browser games, native apps, "watch me click"), not headless `browser_*`.

**Hermes-on-Orgo (same machine):** hostname like `orgo-desktop`, `DISPLAY` set, Chrome present. Prefer **local Desktop API** (`orgo-desktop-local` / `orgo_desktop_*` / `orgo-desktop` CLI) over Orgo MCP screenshot/click. MCP and local hit the same desktop; local is the correct hop.

**Default Dewey:** use `ORGO_DEFAULT_COMPUTER_ID`; do not retarget to customer boxes unless asked.

**Coordinates:** click/drag use **1280x720** model space. Re-measure after maximize/resize; SPAs reflow CTAs (left vs right columns).

**Chrome as root:**

```bash
export DISPLAY=:99
google-chrome --no-sandbox --no-first-run --no-default-browser-check \
  --disable-session-crashed-bubble --start-maximized "https://example.com"
```

Without `--no-sandbox`, Chrome exits (root sandbox error). Launch via `terminal(background=true)`; do not use foreground shell `&`.

**Control loop (required for multi-step UI / games):** screenshot → find target → one action → wait → re-screenshot → **re-plan from actual state**. Never blind-fire a long fixed click/move list that depends on opponent or page responses.

**Open by URL** (`ctrl+l`, type, Enter) before hunting homepage buttons; adjacent CTAs often open the wrong modal.

**`orgo_wait` parameter name is `duration`**, not `seconds`.

Recipes: `references/gui-desktop-driving.md`.

## Templates detail

See `references/templates-access.md` for the full access matrix and sample refs.

Common system refs: `system/hermes-agent@1.0.0`, `system/claude-code@1.0.0`, `system/openclaw@1.0.0`.
Account refs appear under `default/<name>@<semver>` on `GET /templates`.

## Files upload (secrets/state)

Multipart `POST /files/upload` lands files on the VM Desktop as `/root/Desktop/<filename>`.

Observed (2026-07): request fails with `Missing projectId` if only `workspaceId` is sent. Use:

```text
projectId = <workspace UUID>
desktopId = <computer UUID>
file = <binary>
```

Do not print secret file contents when merging into `~/.hermes/.env`.

## Pitfalls

- Do not act on a named computer before confirming it is running; workspaces may contain many similarly named computers.
- Avoid saving raw API keys in `config.yaml`; keep secrets in `.env` and reference them with `${ORGO_API_KEY}`.
- The Orgo installer may install `orgo` under `~/.local/bin` and Node under `~/.orgo/node`; add both to PATH for the current shell before testing.
- `hermes mcp add` is interactive after discovery. In non-interactive contexts, pipe a blank line only when enabling all discovered tools is acceptable.
- MCP / plugin tool changes usually require `/reload-mcp`, `/reset`, or a **fresh Hermes session** before tools appear.
- Prefer MCP bash/exec for remote scriptable work; local Desktop API for same-box GUI; MCP GUI only when remote visual interaction is required.
- **Templates are not a CLI feature.** Use REST to list/manage; MCP only to launch via `image`.
- **Template/image create ≠ software verified.** MCP launches with `image: system/hermes-agent@...` have been observed to boot a bare desktop without `hermes` on PATH; always verify.
- **Files upload field name:** `projectId` required in practice even when computer create uses `workspace_id`.
- Do not change `ORGO_DEFAULT_COMPUTER_ID` to a customer pilot box unless the user wants all default Orgo actions to hit that machine.
- **Same-box GUI stack:** prefer local Desktop API (`orgo-desktop-local`). Do not block headed work on CUA install; do not prefer cloud MCP clicks when `orgo-desktop doctor` is ready.
- **cua-driver optional:** may be installed for native a11y; web modals often lack usable frames. Never treat CUA as required readiness on Orgo images.
- **Chrome root sandbox:** pass `--no-sandbox` when launching Chrome as root on Orgo desktops.
- **Stale coordinates:** maximize and responsive sites move targets; re-scan after layout changes.
- **Adaptive GUI only:** multi-ply games/wizards must re-screenshot after each opponent/page update. Fixed move lists after the first reply desync and blunder.
- **`orgo_wait` uses `duration`**, not `seconds`.
- **Disk resize ≠ usable space.** Orgo may enlarge `vda` while the ext4 root stays at the old size. Always compare `lsblk` vs `df -h /`; grow with `/sbin/resize2fs` (not bare `resize2fs` if PATH omits `/sbin`). Full steps: `references/fleet-remote-exec.md` § Disk resize.
- **API cpu/ram fields can lag live hardware.** Prefer `nproc` / `free -h` / `df` on the box when reporting post-resize size.

## Verification

```bash
export PATH="$HOME/.local/bin:$HOME/.orgo/node/bin:$PATH"
orgo --version
orgo computers list
hermes mcp test orgo
# same-box also:
orgo-desktop doctor
# optional template probe
curl -sS https://www.orgo.ai/api/templates/global -H "Authorization: Bearer $ORGO_API_KEY" | head -c 400
```

A successful remote setup shows the target computer as `running`, `hermes mcp test orgo` connects, and the Orgo server reports its tool list. Same-box also needs `orgo-desktop doctor` ready.

## References

- `references/dewey-orgo-session.md` — Dewey/Minions setup pattern
- `references/templates-access.md` — templates CLI/MCP/REST matrix and pitfalls
- `references/gui-desktop-driving.md` — headed GUI: dashboard watch URL, Chrome flags, 1280x720 clicks, adaptive multi-step loop
- `references/fleet-remote-exec.md` — REST exec patterns, gateway recycle without banned strings, /sbin PATH
- `references/disk-resize-fs-grow.md` — block device grew but df still old size; /sbin/resize2fs online grow
- Skill **`orgo-desktop-local`** — loopback Desktop API, plugin tools, doctor/smoke (when Hermes is on the VM)
