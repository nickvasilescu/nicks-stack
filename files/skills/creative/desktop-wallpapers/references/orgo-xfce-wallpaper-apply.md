# Orgo XFCE wallpaper apply (session notes)

## When this applies

Hermes co-located on Orgo (`orgo-desktop`, `DISPLAY=:99`, 1280×720 Xvnc) **or** remote Orgo fleet boxes via REST/MCP bash. User wants AI wallpaper generated and applied (Dewey theme, model-compare fleet branding, etc.).

## Checklist (single box)

1. **Generate** via Hermes `image_generate` (`aspect_ratio=landscape`). When Nick asks for model-matched branding, use **company logo style + model name**.
2. **Validate PNG** (header + dimensions). AI backends may return 1536×1024 or ~1024×576; `image-style` 5 is OK on 1280×720 VNC.
3. **Deliver:** Orgo `POST /files/upload` with `projectId` + `desktopId` and a **unique** filename (e.g. `wallpaper-glm-5.2.png`). Poll until `/root/Desktop/<exact-fname>` exists — do not `ls wallpaper-*.png | head` (fleet race).
4. **Install path:** `cp` to `/root/Pictures/<exact-fname>`; delete other `wallpaper-*.png` on this box only.
5. **Enumerate XFCE props** and set every matching path:
   - `/backdrop/screen0/monitor0/image-path`
   - `/backdrop/screen0/monitorVirtual-1/workspace0/image-path`
   - `/backdrop/screen0/monitorscreen/workspace0/image-path`
   - all `/last-image` under `monitorVNC-0/workspace*`
   - all `/image-style` → `5`
   - all `/image-show` → `true`
6. **Ensure xfdesktop is running.** Python `Popen(..., start_new_session=True)`. Avoid `xfdesktop --reload` (hangs).
7. **Screenshot verify:** require nonblack **and color diversity** (unique samples >> 20). Real wallpaper often 100KB–1.2MB.
8. If black or solid-only: recovery below, then re-run steps 5–7. **Do not re-generate images first** when files still exist under `/root/Pictures/`.

## Fleet multi-box (model-compare)

1. One landscape image per model (vendor mark + model label).
2. Upload with exact per-box filenames; wait for exact path on that computer.
3. Pin only that path; wipe foreign `wallpaper-*.png`.
4. Verify paint **per box**. Nick will open noVNC and notice black immediately.
5. If "I saw them then they went black": diagnose `pgrep -x xfdesktop` + screenshot diversity; recover paint (usually dead xfdesktop / Xvnc), not art.

## Black / disappeared wallpaper recovery

### Diagnosis

| Signal | Meaning |
|--------|---------|
| xfconf still lists correct PNG | Config OK |
| PNG still on disk | Skip re-upload |
| `pgrep -x xfdesktop` empty; panel/xfwm4 alive | Classic black desktop |
| shot ~14–20KB after soft restart | Often solid root only (xsetroot), not wallpaper |
| shot ~2.7–3.5KB | Pure black / dead paint |

### Soft recovery (try first)

1. Safe-kill Chrome by exact `/opt/google/chrome/chrome` PIDs only.
2. `pkill -x` xfdesktop xfwm4 xfce4-panel xfsettingsd.
3. Relaunch via Python: xfsettingsd → xfwm4 → xfce4-panel → xfdesktop.
4. Re-pin all image-path/last-image props.
5. Verify diversity; if FAIL continue.

### Full recovery (when soft leaves solid/black)

1. Stop XFCE clients.
2. Restart `Xvnc :99` with startup-equivalent flags (1280x720, rfbport 5999, PasswordFile `/tmp/.vncpasswd`, AlwaysShared, +render, CompareFB 2, ZlibLevel 1). Wait `xdpyinfo -display :99`.
3. Session dbus if needed; relaunch clients.
4. Re-pin wallpaper; hard-restart xfdesktop once more.
5. WALLPAPER_OK = large file + high unique color samples (not merely nonblack after solid xsetroot).
6. Tell user to **hard-refresh / reconnect noVNC** after Xvnc restart.

Also see **orgo-desktop-local** `references/black-framebuffer-recovery.md`.

## Proven interactions

- **2026-07-09 Dewey single-box:** xfconf OK, paint pure black (~2774B). Full Xvnc recovery restored wallpaper.
- **2026-07-09 Minions model-compare fleet (7 boxes):** first apply nonblack OK; minutes later user saw black fleet-wide. Cause: `xfdesktop` dead on all, files+xfconf still correct. Soft relaunch painted solid root only (~16KB, high nonblack, low diversity). Full Xvnc + client restart restored all seven WALLPAPER_OK (700KB–1.2MB, high unique samples).

## Success criteria

- xfconf points at intended `/root/Pictures/wallpaper-*.png`
- `pgrep -x xfdesktop` alive
- Screenshot diversity proves wallpaper (not solid color)
- User told to refresh noVNC after Xvnc restart

## Cross-skills

- Parent: `desktop-wallpapers` SKILL.md
- Paint recovery: `orgo-desktop-local` / `references/black-framebuffer-recovery.md`
- Fleet Hermes boxes: `managed-hermes-on-orgo` / `references/multi-model-compare-fleet.md`
