---
name: orgo-desktop-local
description: Same-box Orgo Desktop API computer use via loopback :8080 (prefer over cloud MCP / CUA when Hermes is on the VM). Model tools, CLI, plugin enable path.
version: 1.5.0
author: Hermes
platforms: [linux]
metadata:
  hermes:
    tags: [Orgo, DesktopAPI, ComputerUse, Local, CoLocated, Plugin]
    category: desktop
    related_skills: [orgo-cloud-computers, computer-use]
---

# Orgo Desktop Local (same-box computer use)

When Hermes runs **inside** an Orgo VM (hostname often `orgo-desktop`, `DISPLAY=:99`),
GUI/control actions should hit the **in-VM Desktop API**, not the cloud Orgo MCP hop
and not CUA-first.

**Standing policy (Dewey / this class of host):** prefer **Orgo local computer use**
over CUA driver / Hermes `computer_use`. Local Desktop API is the spine for
screenshot, click, type, key, drag, open-url, bash, and black-framebuffer recovery.
CUA is optional AX/SOM enrichment only. Cloud Orgo MCP GUI is for other VMs and
lifecycle, not this same box when doctor is green.

Load this skill for headed same-box desktop control. For fleet lifecycle / other VMs,
also load `orgo-cloud-computers`. The generic `computer-use` skill documents CUA;
on Orgo it defers here first.

## Endpoint

| | |
|---|---|
| Base | `http://127.0.0.1:8080` (override `ORGO_DESKTOP_API_URL`) |
| Auth | `Authorization: Bearer <vnc_password>` |
| Token env | `VNC_PASSWORD` or `ORGO_DESKTOP_API_TOKEN` (**not** `ORGO_API_KEY`) |
| Service | `/opt/desktop-api/desktop-api` (`orgo-desktop-api`) |
| Schema | `GET /schema` (no auth) |
| Health | `GET /health` (no auth) |

Actions: `/screenshot` `/click` `/double_click` `/drag` `/type` `/key` `/scroll`
`/mouse_move` `/wait` `/bash` `/exec` `/status` plus WS `/events` `/terminal` `/audio`.

Coordinate space: full desktop pixels (Dewey default **1280×720**).

See `references/desktop-api.md` for request shapes and events.

## Prefer order (mandatory)

1. **Co-located + doctor green + nonblack paint** → local Desktop API (this skill / plugin tools / `orgo-desktop` CLI)
2. **User wants to watch** ("headed", "on your screen", "so I can see", noVNC) → **headed Orgo first** (`orgo-desktop open-url`), not headless `browser_*`. Nick preference 2026-07-09: when researching dashboards, OAuth UIs, toolkit docs, or any UI they asked to watch, keep the paint on VNC. Use headless browser only for silent text extraction when they did not ask to watch.
3. **Websites (silent recon)** → Hermes `browser_*` first (DOM) when the user is not watching
4. **Scriptable** → Hermes `terminal` or Desktop API `/bash` before pixel clicks
5. **Other computers / lifecycle** → cloud Orgo MCP / `https://www.orgo.ai/api` (`orgo-cloud-computers`)
6. **CUA / `computer_use`** → optional a11y enrichment only when element frames exist; never block readiness on CUA; never use as first screenshot path when paint may be black
7. **Never** default to cloud `orgo_click` / MCP GUI when local doctor is green

### Why Orgo > CUA here (evidence, not branding)

| Failure | CUA / naive scrot | Local Desktop API |
|---------|-------------------|-------------------|
| Black framebuffer | Pure black captures; app list noise | Doctor + screenshot bytes; recovery doc restores paint |
| Headed Chrome | Window title real but CUA "no window matched" | `orgo-desktop open-url` + user-visible noVNC |
| Readiness | Optional install; not required | `orgo-desktop doctor` → `ready` / `prefer: local_desktop_api` |
| Hop | Extra driver session | Loopback `:8080` same paint path as VNC |

Sentiment to preserve across patches: **Orgo local first, CUA second, cloud MCP third (other hosts only).**

## Hermes model tools (plugin)

Plugin: `~/.hermes/plugins/orgo-desktop-local/`  
Client lib: `~/.hermes/scripts/orgo_desktop/`  
CLI: `~/.local/bin/orgo-desktop`

### Install / enable (once per host)

```bash
hermes plugins enable orgo-desktop-local
hermes tools enable orgo_desktop --platform cli
# optional: --platform telegram|discord|whatsapp|slack|signal
```

**New session required** after enable (tool list is built at session start).

See `references/hermes-plugin.md` for register_tool pattern and official docs.

### Tool surface

Toolset key: `orgo_desktop`

| Tool | Purpose |
|---|---|
| `orgo_desktop_doctor` | health + auth + screenshot + bash; also `prefer` / `control_plane` / `avoid_when_ready` |
| `orgo_desktop_screenshot` | full desktop PNG path |
| `orgo_desktop_click` | x,y full-desktop coords; optional `verify` → `noop` / `visual_changed` |
| `orgo_desktop_drag` | drag start→end (Desktop API `/drag`); optional `verify` |
| `orgo_desktop_click_path` | two-click select→dest; default verify (`destination_noop` if 2nd click no pixel change) |
| `orgo_desktop_type` | type text |
| `orgo_desktop_key` | key / chord (Escape, Return, ctrl+l) |
| `orgo_desktop_bash` | shell via desktop-api `/bash` |
| `orgo_desktop_scroll` | scroll at point |
| `orgo_desktop_open_url` | headed Chrome (`--no-sandbox`) |
| `orgo_desktop_wait` | wait seconds (API max 60) |

**Visual verify:** cropped frame SHA-256 (default skips top ~28px panel/clock). API `success` alone is not proof the UI changed.

### Session workflow

1. Call `orgo_desktop_doctor` (or `orgo-desktop doctor`). Proceed only if `ready: true`
   **and** the screenshot is not a black framebuffer. Treat `screenshot_bytes` ≈ 2.7–3.5 KB
   (or PIL nonblack ≈ 0) as paint-dead even when API health is green — run
   `references/black-framebuffer-recovery.md` before claiming a headed app is open.
   When ready, `prefer` should be `local_desktop_api` — do **not** use cloud `mcp__orgo__*` GUI for this box.
2. Prefer `orgo_desktop_open_url` / bash openers over hunting homepage buttons
   (including Hermes dashboard at `http://127.0.0.1:9119`).
3. Screenshot → one action → wait → re-screenshot → re-plan from actual state.
   Prefer `orgo-desktop screenshot` over raw `scrot`/CUA root capture for truth on Xvnc.
4. For piece/icon moves: prefer `orgo_desktop_click_path` or `orgo_desktop_drag` with verify.
   If `destination_noop` or `noop` is true, re-plan (do not assume the move landed).
5. If tools missing from the model list: confirm plugin+toolset enabled, then **fully quit and
   restart** the Hermes process (not only `/new` inside a pre-enable process). Mid-session
   fallback: CLI `orgo-desktop …` or Python `OrgoDesktopClient`. Do **not** invent cloud MCP
   GUI calls when doctor is green. Report which path executed honestly.

### Mid-session client fallback (when `orgo_desktop_*` absent)

```python
import sys
sys.path.insert(0, str(Path.home() / ".hermes" / "scripts"))
from orgo_desktop import OrgoDesktopClient
c = OrgoDesktopClient()
assert c.doctor()["ready"]
c.open_url("https://example.com/")
c.save_screenshot("/tmp/desk.png")
c.click(x, y)
c.wait(1.5)
```

Handlers live in `~/.hermes/plugins/orgo-desktop-local/tools.py` and wrap this client;
they need Hermes `tools.registry` only when registered as model tools.

## Headed web / game loop (local API)

When the user wants a **watched** browser session (VNC stream) on this box — or says
**"headed"**, **"on your screen"**, **"so I can see"** — do this path first:

1. Doctor green first; announce that Chrome is opening on noVNC.
2. Prefer one Chrome window: avoid stacking many `open-url` launches (tabs/windows desync
   focus). If messy, close Chrome carefully then re-open **one** URL (see pitfalls).
3. Navigate by URL when possible; for SPAs without a deep link, open homepage then click
   the correct CTA (adjacent buttons are easy to mis-hit).
4. **Locate targets from the latest screenshot**, not from memory coords. Modal CTAs often
   sit below selected option rows (e.g. Lichess "Play against computer" was ~y=649 while
   Side/White was ~y=555 on 1280×720).
5. **Dense SPA list rows / cards** (e.g. X Developer Console production app): single
   `click` often no-ops or hits adjacent Create/+ New controls. Prefer **double-click**
   via Python `OrgoDesktopClient.double_click(x, y)` (Desktop API `/double_click`). The
   `orgo-desktop` CLI has **no** `double_click` subcommand yet — do not invent one.
6. Before re-clicking a missed card, re-measure: white-text centroid (PIL) on the current
   frame; y-off by ~20–40px is enough to miss the hit target on 1280×720.
7. After URL navigation, wait through **Loading… / skeleton** frames before measuring
   or clicking (console.x.com apps list commonly needs 2–6s).
8. Multi-ply / opponent games: after every user move and every opponent reply, re-screenshot
   and re-plan. Fixed move lists desync under checks, captures, and unexpected replies.
9. Board games: map board bounds from screenshot colors once, then click square centers;
   re-map if layout changes. See `references/headed-web-game-loop.md`.
10. **Accordion / collapsible docs panels** (e.g. Composio toolkit OAuth2): pixel clicks often
    miss; re-measure chevron from the latest screenshot, or use DOM `browser_*` as secondary
    extract while keeping the headed tab open for the user to watch.
11. **Hermes dashboard Plugins / memory provider form:** MEMORY PROVIDER dropdown sits above
    the API KEY field. Clicks meant for the key often open the dropdown; accidental SAVE can
    switch provider (honcho → hindsight). Prefer durable writes (`.env`, provider json,
    `hermes config set memory.provider …`) then refresh; leave API KEY blank when green
    **set** badge already shows. Details: `references/hermes-dashboard-on-orgo.md`.

## CLI (shell fallback)

```bash
orgo-desktop doctor
orgo-desktop smoke
orgo-desktop screenshot /tmp/desk.png
orgo-desktop bash 'hostname'
orgo-desktop click 640 400
orgo-desktop click 640 400 --verify
orgo-desktop drag 100 200 300 250 --verify
orgo-desktop click-path 100 200 300 250
orgo-desktop type 'hello'
orgo-desktop key Escape
orgo-desktop open-url https://example.com/
orgo-desktop colocated
```

Python (add `~/.hermes/scripts` to `sys.path`):

```python
from orgo_desktop import OrgoDesktopClient
client = OrgoDesktopClient()
assert client.doctor()["ready"]
client.save_screenshot("/tmp/desk.png")
client.click(100, 200)
```

## Success / validation criteria

| Check | Pass |
|---|---|
| `orgo-desktop doctor` | `"ready": true` and `"prefer": "local_desktop_api"` |
| `orgo-desktop smoke` | Prefer per-check green for actions; see smoke interpretation below |
| Plugin handlers | `orgo_desktop_doctor` returns ready against `:8080` |
| Config | `plugins.enabled` has `orgo-desktop-local`; platform toolsets include `orgo_desktop` |
| New tools | `orgo_desktop_drag` / `orgo_desktop_click_path` registered after **full process** restart |

Do not claim computer-use is improved from config alone; require doctor green and honest tool-list verification (`tool_search` / `tool_describe`).

### Smoke interpretation

`orgo-desktop smoke` may report overall `passed: false` while **all control actions** (health, auth, screenshot, bash, key, click, wait, drag, click_path, verify fields, prefer-local) are green. A lone **`fingerprint_stable`** failure usually means two consecutive frames differed (clock / panel / wallpaper) and is **not** a Desktop API outage.

When reporting status to the user:

1. Separate **action checks** from **fingerprint_stable**.
2. Separate **CLI / Python client** (disk, current after code deploy) from **model tools in this process** (baked at Hermes process start).
3. Plugin **code upgrades** (new schemas: drag, click_path, click `verify`) need the same **full quit + new Hermes process** as first enable. `/new`, MCP reload, and mid-session enable are not enough.
4. After restart, confirm with `tool_search`/`tool_describe` for `orgo_desktop_drag` and `orgo_desktop_click_path`, not only config flags.

## Pitfalls

- **Wrong secret:** Desktop API wants **VNC password** (`VNC_PASSWORD`). `ORGO_API_KEY` is cloud-only.
- **Cloud MCP on self:** longer hop, fleet ambiguity; use only for remote computers / lifecycle.
- **CUA is not the spine:** may doctor-green; web modals often have null AX frames / stale tokens. Prefer Desktop API pixels + browser DOM for web.
- **Root Chrome:** needs `--no-sandbox` (`open-url` already does).
- **Agent cannot patch `config.yaml` via write/patch tools** — use `hermes plugins enable` / `hermes tools enable` / `hermes config set`.
- **Mid-session tools / upgrades:** enable **and** plugin code changes do not hot-load into a long-lived Hermes PID; fully quit the process (not only `/new`). Until then use CLI/`OrgoDesktopClient` and report that path honestly.
- **Smoke overall false ≠ stack down:** check whether only `fingerprint_stable` failed; still treat doctor ready + action checks as usable.
- **Auth dialogs on headed desktop:** never type passwords, 2FA, payment, or permission dialogs. Public handle ok; then wait for the user.
- **API success ≠ UI change:** use `verify` / `click_path` fingerprints; `destination_noop` means the second click did nothing visible.
- **Chess / board UIs:** knight is 2+1 only; in check only resolving moves are legal; re-read move list after every opponent ply; do not trust last-move green as selection.
- **Coordinates:** full desktop 1280×720 unless screenshot proves otherwise; re-measure after maximize. Clicks that "succeed" in the API can still hit the wrong control if y is off by ~30–80px (common on stacked modal buttons).
- **Pixel-find before re-clicking:** when a CTA fails twice, crop the screenshot / scan for button text luminance or selected-green tiles instead of guessing nearby y values.
- **SPA card open needs double-click:** console.x.com (and similar) app/project cards may ignore single click; use `OrgoDesktopClient.double_click`. Focus the correct Chrome window title when login and console both exist.
- **CLI vs Python surface:** drag / click-path / verify are on CLI; double-click is client/API only until CLI grows a subcommand.
- **Adjacent CTAs:** Lichess right rail stacks Create lobby / Challenge a friend / Play against computer — Challenge opens a similar "Game setup" modal without strength; confirm orange highlight or Strength row before "Play".
- **Stale deep links:** Lichess `https://lichess.org/setup/ai` has returned 404; use homepage → Play against computer (or a current documented path).
- **Many Chrome windows:** repeated `open-url`/`--new-window` multiplies windows; focus the wrong title (e.g. aborted human game) mid-smoke. Prefer one window; activate by window name via desktop-api `/bash` + `xdotool` when needed.
- **pkill Chrome from agent shell:** broad `pkill -f chrome` can interrupt the controlling command (SIGTERM). Prefer targeted PIDs or one clean relaunch path; verify with `orgo-desktop doctor` after.
- **Adaptive multi-ply only:** never fire a long fixed chess/game click list after the first opponent reply without re-reading the board/move list.
- **Events underused:** `ws://127.0.0.1:8080/events?token=<vnc_password>` for window_open / file_change / idle waits.
- **Wallpaper / backdrop after recovery:** if xfconf backdrop was set while paint was dead or `xfdesktop` was missing, re-set all `image-path` / `last-image` keys and relaunch `xfdesktop` after recovery. Do not claim wallpaper applied from xfconf alone. Class workflow: skill `desktop-wallpapers` + `references/orgo-xfce-wallpaper-apply.md`.
- **scrot/ImageGrab false-green:** raw root captures can look nonblack (~800KB) while `orgo-desktop screenshot` is pure black (~2.7KB). Gate all "you can see it" claims on Desktop API `screenshot_bytes` only. Details: `references/black-framebuffer-recovery.md`.

## Verification

```bash
orgo-desktop doctor
orgo-desktop smoke
curl -sS http://127.0.0.1:8080/health
hermes plugins list | head -40
# after new session: model tools orgo_desktop_* available
```

## References

- `references/desktop-api.md` — local API verbs, auth, coords, events
- `references/hermes-plugin.md` — plugin layout, enable path, official docs
- `references/headed-web-game-loop.md` — headed SPA/game smoke: doctor, open-url, pixel CTAs, board mapping, Lichess notes
- `references/black-framebuffer-recovery.md` — black VNC/paint recovery path
- `references/packaging-and-sharing.md` — MCP vs plugin vs skills vs OS1; how to share with others
- `references/hermes-dashboard-on-orgo.md` — start `hermes dashboard` and make it **user-visible** on VNC (doctor → open-url → nonblack screenshot)
- `references/hermes-dashboard-memory-provider.md` — Plugins memory provider form: dropdown vs API KEY, accidental provider switch, durable Honcho key path
- Related class skill: `desktop-wallpapers` (AI wallpaper generate/apply; Orgo re-apply after paint recovery)
