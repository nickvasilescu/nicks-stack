# Headed web / game loop (local Desktop API)

Use when Hermes is co-located (`orgo-desktop doctor` → `ready: true`) and the user
wants a **watched** browser session via VNC, not headless `browser_*`.

## Preconditions

```bash
orgo-desktop doctor   # ready: true
orgo-desktop smoke    # optional full pass
```

Auth is VNC password / `ORGO_DESKTOP_API_TOKEN`, not `ORGO_API_KEY`.

## Path choice

| Need | Path |
|---|---|
| Native model tools `orgo_desktop_*` | Plugin+toolset enabled **and new session** |
| Same stack mid-session | `orgo-desktop` CLI or `OrgoDesktopClient` |
| DOM-only / no watch | Hermes `browser_*` (prefer when headed not required) |
| Other VMs / lifecycle | cloud Orgo MCP (`orgo-cloud-computers`) |

If `tool_search` / `tool_describe` cannot see `orgo_desktop_*`, do not pretend to call
them. Use client/CLI and say so.

## Control loop

1. Screenshot full desktop (1280×720 on Dewey).
2. Plan **one** action from pixels (or URL open).
3. Execute via Desktop API (`click` / `key` / `type` / `open_url` / `bash`).
4. `wait` (0.5–3s depending on SPA).
5. Re-screenshot; re-plan from **actual** state (title bar, move list, modals).
6. For multi-ply games: never continue a fixed move list after an opponent reply without
   re-reading the position.

## Pixel CTA recovery

When a labeled button is missed twice:

1. Save latest full-desktop PNG.
2. Crop the modal / rail region.
3. Find:
   - Lichess selected lime: high G, low R/B (strength / side tiles).
   - Button label text: near-white / light-gray luminance bands.
4. Click the **center of the text/button band**, not a remembered y from a prior layout.
5. Confirm success by state change (title, new modal fields, board appear), not by API
   `success: true` alone.

Observed Dewey 1280×720 Lichess AI setup (one session; re-measure always):

| Target | Approx center |
|---|---|
| Right rail "Play against computer" | ~1110, 480 |
| Side / White tile | ~835, 555 |
| Modal "Play against computer" start | ~640, **649** (below Side row; y≈574 hits Random) |

## Chess board mapping (Lichess-style)

1. Detect light/dark board squares by color on full-desktop screenshot.
2. Tight bbox of dense board pixels → `left, top, right, bottom`.
3. `sq = (right - left + 1) / 8`.
4. White at bottom (default when playing White):

```text
x = left + (file + 0.5) * sq    # file 0=a .. 7=h
y = bottom - (rank + 0.5) * sq  # rank 0=1 .. 7=8
```

5. Move = click from-square, short wait, click to-square.
6. After each move: wait for engine (~2–3s at low strength), screenshot, read move list /
   check highlights, then choose the next move.

Example map from one Dewey game (do not hardcode forever): board ≈ 388,177–835,624,
sq ≈ 56 → e2 (640,540), e4 (640,428).

## Lichess vs computer smoke (local API only)

Success criteria for a short smoke (~8 half-moves):

1. Doctor ready.
2. Open `https://lichess.org/` via `open_url` (not stale `/setup/ai` if 404).
3. Open AI setup (Strength row present; not Challenge-a-friend modal).
4. Start game; window title like `Your turn - Play Stockfish level N`.
5. Play several plies with adaptive loop; move list shows alternating White/Black.
6. Evidence: screenshots under `/tmp/lichess-ply-*.png` (or equivalent) + final title.

Pitfalls specific to Lichess:

- `/setup/ai` may 404; homepage + "Play against computer" is reliable.
- Challenge-a-friend modal looks like Game setup but has no Strength.
- Stockfish replies can put you in check; fixed opening scripts after e4/Nf3/Bc4/c3 can
  fail (e.g. …Qxe4+) if the next clicks ignore check.
- Multiple Chrome windows from repeated open-url: activate by title
  (`xdotool search --name 'Stockfish'`) via desktop-api `/bash`.

## Chrome window hygiene

- Prefer a single headed Chrome for the smoke.
- `open_url` uses `google-chrome --no-sandbox … --new-window`.
- Avoid broad `pkill -f chrome` from the agent shell when it may SIGTERM the wrapper;
  if cleanup is needed, target main PIDs, re-doctor, then one open-url.
- Window geometry may be `0,27 1280x693` under a top panel; **click coords still match
  full-desktop screenshots** from Desktop API (not window-local).

## Validation checklist

| Step | Pass |
|---|---|
| Doctor | `ready: true` |
| Open site | headed Chrome shows target origin |
| Correct modal | expected fields (e.g. Strength 1–8 for AI) |
| Game start | title / board / opponent label |
| Moves | move list grows; screenshots after each ply |
| Honest tooling report | model tools vs CLI/client named correctly |
