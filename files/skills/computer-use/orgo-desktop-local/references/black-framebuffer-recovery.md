# Black framebuffer recovery (Orgo local desktop)

## Symptom

- User says they do not see the app / dashboard even though Chrome title or HTTP is OK
- `orgo-desktop doctor` may still report `ready: true` (API up) while paint is dead
- `screenshot_bytes` ≈ **2700–3500** (pure black PNG) or PIL nonblack ≈ 0 / only agent-cursor pixels (~100)
- Windows still exist in `xdotool search` (Chrome, Obsidian, Discord) but nothing paints on VNC/noVNC
- `scrot` / `import -window root` / CUA `capture app=screen` are pure black even when window titles claim content

## Fast black check (do this before claiming "opened")

```bash
orgo-desktop screenshot /tmp/desk-check.png
# doctor also prints screenshot_bytes
python3 - <<'PY'
from PIL import Image
from pathlib import Path
p = Path("/tmp/desk-check.png")
im = Image.open(p)
non = sum(1 for c in im.getdata() if sum(c[:3]) > 0)
print("bytes", p.stat().st_size, "nonblack", non, "size", im.size)
# fail closed: pure black frames are ~2.7KB on 1280x720 PNG
assert non > 10000, "black framebuffer — run recovery before headed open-url claims"
PY
```

**Rule:** `ready: true` + tiny `screenshot_bytes` (e.g. 2774) = **not ready for headed work**. Recover paint first. Prefer `orgo-desktop screenshot` / `OrgoDesktopClient.save_screenshot` over raw `scrot` for truth.

## Common causes

1. Aggressive `xdotool windowsize/windowmove` on Chrome + GPU/WebGL failures
2. `pkill -f chrome` matching the **agent shell** and partially killing the session
3. Stuck paint path under TigerVNC `Xvnc :99` after bad GPU path / many Chrome relaunches
4. Claiming success from Chrome window title alone while VNC stream is black (user cannot see it)

## Safe Chrome kill

```bash
export DISPLAY=:99
ps -eo pid,cmd | awk '/\/opt\/google\/chrome\/chrome/ && !/awk/ {print $1}' | while read p; do kill "$p" 2>/dev/null; done
```

Do **not** use `pkill -f chrome` from a command that contains the string `chrome` in its own argv.

## Recovery (session-proven on Dewey Orgo)

Hermes `terminal` **rejects** foreground `nohup`/`&`. Use `background=true` for Xvnc, or Python `start_new_session=True` for session clients.

1. Safe-kill Chrome (exact `/opt/google/chrome/chrome` PIDs only).
2. Stop XFCE clients carefully: `xfwm4`, `xfdesktop`, `xfce4-panel`, `xfsettingsd`, `autocutsel` (`pgrep -x` / `pkill -x`).
3. Stop and restart `Xvnc :99` (geometry 1280x720, rfbport 5999, PasswordFile `/tmp/.vncpasswd`). Regenerate passwd via `/opt/mkvncpasswd.py` from `VNC_PASSWORD` **without printing the secret**.
4. Wait for `xdpyinfo -display :99`.
5. Relaunch session clients via Python (avoids shell `&` / nohup bans):

```python
import os, subprocess, time
os.environ["DISPLAY"] = ":99"
for c in (["xfsettingsd"], ["xfwm4"], ["xfce4-panel"], ["xfdesktop"]):
    subprocess.Popen(c, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
for args in (["autocutsel", "-fork"], ["autocutsel", "-selection", "PRIMARY", "-fork"]):
    subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
time.sleep(2)
subprocess.run(["xsetroot", "-solid", "#334455"], check=False)
```

6. Verify **nonblack** screenshot (PIL nonblack >> 10k; file often 100KB+).
7. Open headed apps with **`orgo-desktop open-url <url>`** (preferred), not ad-hoc Chrome flag soup.
8. Tell the user to **reconnect / hard-refresh noVNC** if their stream still shows the old black frame.

Optional: restart `desktop-api` only if `/health` fails; recovery above often leaves API healthy.

## Headed Chrome after recovery

```bash
orgo-desktop open-url "http://127.0.0.1:9119"   # or any URL
# Fallback flags if open-url path is unavailable:
# google-chrome --no-sandbox --no-first-run --disable-session-crashed-bubble \
#   --disable-gpu --use-gl=swiftshader --new-window <url>
```

After open:

- Confirm window title (e.g. `Hermes Agent - Dashboard - Google Chrome`)
- Confirm **nonblack** `orgo-desktop screenshot`
- Dismiss Chrome **Restore pages?** with Escape / dialog X if present
- Raise window: `xdotool search --name "…" windowactivate windowraise`

## Hermes dashboard + "I don't see it"

| Check | Meaning |
|-------|---------|
| `curl` :9119 → 200 | Server OK |
| Chrome title has Dashboard | Process navigated |
| Screenshot pure black | **Paint dead** — recover; do not tell user it is open |
| Screenshot has Hermes teal UI | User should see it after VNC refresh |

Loopback only: `http://127.0.0.1:9119`. SSH tunnel if viewing from laptop: `-L 9119:127.0.0.1:9119`.

## Login portals

Stop at password/2FA. User completes auth on VNC/noVNC; agent resumes only after non-login URL.

## Related

- Parent skill: `orgo-desktop-local` SKILL.md pitfalls
- Hermes control plane notes: `coding-agent-routing` → `references/hermes-surfaces-vs-specialist-desktop.md`
