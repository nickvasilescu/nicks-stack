---
name: desktop-wallpapers
description: "Create and apply desktop wallpapers/backgrounds, including AI image generation, procedural fallbacks, and Linux desktop-environment wallpaper commands."
version: 1.1.0
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [wallpaper, desktop, background, image-generation, linux, xfce, procedural-art]
    category: creative
    created_by: agent
---

# Desktop Wallpapers

Use this skill when the user asks for a cool desktop background, VM wallpaper, lock-screen-style image, or wants a generated image applied as a desktop wallpaper.

## Workflow

1. Determine the target surface and platform.
   - If the user says "your computer", inspect the live environment before assuming a desktop environment.
   - On Linux, check `XDG_CURRENT_DESKTOP`, `DISPLAY`, `WAYLAND_DISPLAY`, and available wallpaper tools.
   - For XFCE, `xfconf-query` is the most direct way to set the background.

2. Prefer real image generation when available.
   - Use the configured image generation tool for the requested style and aspect ratio.
   - For desktop backgrounds, default to `landscape` / 16:9 unless the user specifies otherwise.
   - Avoid text/logos/watermarks unless explicitly requested (model-compare fleets often request company logo + model name — honor that).
   - Leave negative space if the desktop has icons.

3. If image generation is unavailable because credentials/billing/provider setup is missing, do not stop at the error.
   - Capture the setup fix briefly if useful, but continue with a local fallback when possible.
   - A good fallback is a deterministic procedural PNG/SVG wallpaper generated with Python stdlib or existing graphics tools.
   - Verify the generated image dimensions and file validity before applying it.

4. Save the artifact in a sensible user-visible location.
   - Linux VM default: `~/Pictures/<descriptive-name>.png`.
   - Use an absolute path in the final reply.

5. Apply the wallpaper using the desktop environment's native mechanism.
   - XFCE: set `xfce4-desktop` backdrop properties with `xfconf-query`, then reload `xfdesktop` if present.
   - GNOME: use `gsettings set org.gnome.desktop.background picture-uri file:///absolute/path`.
   - KDE Plasma, Windows, and macOS require platform-specific commands; inspect first rather than guessing.

6. Verify.
   - Confirm the image exists and has expected dimensions.
   - Confirm the desktop configuration points to the generated file when the platform exposes a query command.
   - On Orgo/Xvnc: also confirm nonblack **and color-diverse** paint via screenshot (see Orgo section). xfconf alone is not enough.

## XFCE wallpaper commands

For an XFCE VM with VNC/virtual monitors, update all matching backdrop paths rather than only one monitor key:

```bash
IMG=/absolute/path/to/wallpaper.png
for prop in \
  /backdrop/screen0/monitor0/image-path \
  /backdrop/screen0/monitorVirtual-1/workspace0/image-path \
  /backdrop/screen0/monitorscreen/workspace0/image-path; do
  xfconf-query -c xfce4-desktop -p "$prop" -s "$IMG" 2>/dev/null || true
done
for prop in $(xfconf-query -c xfce4-desktop -l | grep -E '/last-image$'); do
  xfconf-query -c xfce4-desktop -p "$prop" -s "$IMG" 2>/dev/null || true
done
for prop in $(xfconf-query -c xfce4-desktop -l | grep -E '/image-style$'); do
  xfconf-query -c xfce4-desktop -p "$prop" -s 5 2>/dev/null || true
done
for prop in $(xfconf-query -c xfce4-desktop -l | grep -E '/image-show$'); do
  xfconf-query -c xfce4-desktop -p "$prop" -s true 2>/dev/null || true
done
# Prefer restart over --reload (reload can hang the shell 60s+)
if pgrep -x xfdesktop >/dev/null; then
  kill -HUP "$(pgrep -x xfdesktop | head -1)" 2>/dev/null || true
else
  # terminal(background=true) or Python Popen(start_new_session=True)
  DISPLAY="${DISPLAY:-:99}" xfdesktop &
fi
xfconf-query -c xfce4-desktop -l -v | grep -F "$IMG" || true
```

## Orgo / Xvnc verification (co-located or remote fleet)

On Orgo desktops (`DISPLAY=:99`, VNC), wallpaper work is not done when xfconf points at a file. Paint can be dead while config looks correct.

1. Confirm `xfdesktop` is running (`pgrep -a xfdesktop`). Panel + `xfwm4` alone can leave a black root — **most common post-apply failure** is `xfdesktop` dying while xfconf still lists the correct PNG.
2. Prefer `orgo-desktop screenshot` when co-located; on **remote** fleet boxes use Orgo bash + `scrot` / PIL.
3. Fail closed on black / solid-only paint:
   - pure black PNG ≈ 2700–3500 bytes
   - solid `xsetroot` color ≈ 14–20KB with high nonblack but **low color diversity** — wallpaper FAIL
   - real wallpaper: often 100KB–1.2MB with hundreds of unique color samples
4. Recovery order (do not stop after soft restart if paint is still flat):
   a. Soft: relaunch xfsettingsd / xfwm4 / xfce4-panel / xfdesktop (Python `Popen(start_new_session=True)`).
   b. Re-pin every `image-path` / `last-image` + `image-style=5`.
   c. If still flat: **full Xvnc restart** per **orgo-desktop-local** `references/black-framebuffer-recovery.md`, then re-pin and verify diversity.
5. After any Xvnc restart, tell the user to **hard-refresh / reconnect noVNC**.

Fleet multi-box apply, exact-filename waits, and recovery transcripts: `references/orgo-xfce-wallpaper-apply.md`.

## Procedural fallback

When no image-generation backend is usable, create a procedural wallpaper instead of declaring the task impossible. A small Python script can write a valid PNG directly with `zlib`/`struct`, avoiding external dependencies like ImageMagick or Pillow.

See `scripts/procedural_neon_wallpaper.py` for a dependency-free 1920x1080 neon Linux command-center wallpaper generator.

## Pitfalls

- Do not save a durable rule that a specific image provider is unavailable; provider credentials and billing are environment state.
- Do not use GUI computer-use for wallpaper changes when CLI desktop settings are available.
- Do not use shell-level background wrappers for launching GUI apps/processes; use tracked background process tools when needed. Launch `xfdesktop` / Xvnc with `terminal(background=true)` or Python `start_new_session=True` — Hermes rejects foreground `nohup`/`&`.
- `xfdesktop --reload` can hang the shell (60s+ timeout observed). Prefer `kill -HUP` on the existing PID, or `pkill -x xfdesktop` then relaunch; then verify with a screenshot.
- Some minimal VMs lack `file`, ImageMagick, Pillow, or desktop portals. Verify PNGs with Python by reading the PNG header when common utilities are missing.
- For XFCE, setting only one `image-path` may not affect the visible VNC/virtual monitor. Enumerate `xfconf-query -c xfce4-desktop -l` and update monitor/workspace keys (`monitor0`, `monitorVNC-0` last-image per workspace, `monitorVirtual-1`, `monitorscreen`).
- AI image backends often emit ~1024×576 even for landscape. Fine when `image-style` is 5 (scaled) on 1280×720 VNC; not a failure. Second gen / upscale only if the user wants sharper fill.
- xfconf success ≠ visible wallpaper. Always verify nonblack **and color-diverse** paint after apply.
- **User: "wallpapers disappeared / went black"** is almost always dead/missing `xfdesktop` (or dead Xvnc paint), not deleted files. Check `pgrep -x xfdesktop` and screenshot diversity before re-generating images.
- Soft client relaunch can leave a **solid root color** that is nonblack but not the wallpaper. Require unique color samples, not just nonblack counts.
- **Fleet multi-box uploads:** wait for the **exact** filename on that computer; delete other `wallpaper-*.png` so apply scripts do not pick a sibling box's art.
- Nick prefers **company-logo + model-name** branding wallpapers for model-compare fleets when he asks for model-matched backgrounds (overrides generic "avoid logos" default).
