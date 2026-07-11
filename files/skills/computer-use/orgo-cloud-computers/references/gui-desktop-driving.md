# Headed GUI driving on Orgo desktops

Session-proven patterns for driving the live Orgo desktop when the user wants to watch (dashboard/VNC), especially when Hermes runs *on* the same computer.

## When this applies

- User asks for headed control ("so I can watch"), native apps, or sites that need the real desktop browser.
- Host is Orgo Linux desktop (`orgo-desktop`, `DISPLAY=:99`, Chrome present).
- Prefer **local Desktop API** when Hermes is co-located; Orgo MCP GUI when controlling a remote computer.

## First 30 seconds

1. `orgo_ensure_running` (default computer or explicit id) if lifecycle/status unknown.
2. `orgo_get_computer` with `compact=false` → copy **dashboard URL** to the user:
   - Prefer `connection_url` (e.g. `https://www.orgo.ai/desktops/<instance>`)
   - Fallback: `url` / instance `webUrl`
3. **Same-box:** `orgo-desktop doctor` or `orgo_desktop_doctor` must be ready. Do not wait for CUA.
4. **Remote-only:** use Orgo MCP screenshot/click when not co-located.

Default Dewey computer id lives in `ORGO_DEFAULT_COMPUTER_ID`. Do not retarget to customer VMs unless the user names them.

## Tool map

| Goal | Same-box (Hermes on VM) | Remote Orgo computer |
|------|-------------------------|----------------------|
| Shell / open URL | `orgo_desktop_bash` / `orgo-desktop bash` / local `terminal` | `orgo_bash` |
| See desktop | `orgo_desktop_screenshot` / `orgo-desktop screenshot` | `orgo_screenshot` |
| Click | `orgo_desktop_click` x/y **1280x720** | `orgo_click` |
| Type / keys | `orgo_desktop_type` / `orgo_desktop_key` | `orgo_type` / `orgo_key` |
| Pause | `orgo_desktop_wait` (`seconds`) | `orgo_wait` (`duration`) |
| Long-lived Chrome | `orgo_desktop_open_url` or `terminal(background=true)` + `--no-sandbox` | MCP bash / remote terminal |

CUA element clicks are optional enrichment only; web modals often lack usable AX frames.

Local `scrot` + PIL pixel scans remain useful for finding button text rows when needed.

## Chrome as root (Orgo image)

```bash
export DISPLAY=:99
google-chrome --no-sandbox --no-first-run --no-default-browser-check \
  --disable-session-crashed-bubble --start-maximized "https://..."
```

Failure without flag: `Running as root without --no-sandbox is not supported.`

Launch as a real background process (`orgo_desktop_open_url`, `terminal` background=true). Avoid foreground shell `&`.

If Chrome disappeared (user focused Obsidian, etc.): search class `Google-chrome`, `windowactivate` / relaunch URL.

## Coordinate and layout rules

- Default desktop resolution observed: **1280x720**. Click model space matches.
- Window position matters if not maximized. Maximized layouts reflow SPAs.
- Example pitfall: Lichess home CTAs sit on the **left** in a narrower window and on the **right** when maximized. Fixed (x,y) from an earlier shot will hit the wrong control.
- Wrong CTA risk: adjacent buttons ("Challenge a friend" vs "Play against computer"); prefer direct URL routes when known, else re-screenshot and re-locate the label.

## Adaptive multi-step loop (required)

For wizards, multi-page flows, or **games vs an opponent/engine**:

1. Screenshot
2. Identify current state (turn, modal open, piece placement, form fields)
3. One action (or one intentional compound action like click-piece then click-square)
4. Wait for UI/engine response
5. Screenshot again and re-plan

**Anti-pattern:** precompute a long move list and fire it with fixed sleeps. Opponent replies change legality and board geometry; blind scripts desync.

Board games: recalibrate square centers from the current screenshot if the window resized. Chess canvases are not AX buttons.

## Open-by-URL before button hunting

```text
ctrl+l → type full URL → Enter
# or: orgo_desktop_open_url / orgo-desktop open-url
```

Faster and less ambiguous than homepage modals. If hash routes (`#ai`) are stale on a SPA, use the visible labeled button after a clean homepage load.

## Evidence for the user

- Always share the dashboard URL for headed sessions.
- On CLI: describe state; absolute paths to screenshots are fine (no `MEDIA:` tags on CLI).
- On messaging: durable PNG path + platform media convention.

## Related

- Parent skill: `orgo-cloud-computers` SKILL.md
- Same-box stack: `orgo-desktop-local` (plugin + CLI + Desktop API)
- Cross-link: `computer-use` (CUA path; optional on Orgo)
- Setup history: `references/dewey-orgo-session.md`
