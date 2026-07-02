#!/usr/bin/env python3
# ==========================================================================
# Nick's Stack — Telegram managed-bot QR pairing (the signature onboarding)
# ==========================================================================
# Reproduces the exact flow the source VM used: mint a Nous managed-bot pairing,
# render its deep link as a QR PNG, show it on the desktop in Chrome, poll until
# the user scans + taps "Create Bot", then write the three TELEGRAM_* keys into
# ~/.hermes/.env. No BotFather, no manual token paste — scan and go.
#
# MUST run under the Hermes venv python so hermes_cli is importable:
#   /usr/local/lib/hermes-agent/venv/bin/python telegram-pair.py
#
# After this returns 0, restart the gateway so it enables the Telegram platform
# (a running gateway does NOT hot-pick-up a newly written bot token).
import os
import sys
import time
import subprocess

QR_PATH = "/root/telegram_qr.png"
DISPLAY = os.environ.get("DISPLAY", ":99")


def log(msg):
    print(f"[telegram-pair] {msg}", flush=True)


def render_qr_png(payload: str, path: str) -> bool:
    """Render the pairing deep link as a PNG (python-qrcode defaults —
    reproduces the source VM's 490x490 1-bit look). Returns True on success."""
    try:
        import qrcode
    except ImportError:
        log("qrcode not in venv; installing via uv…")
        # The Hermes venv is uv-managed and ships no pip — install with uv.
        for cmd in (["uv", "pip", "install", "--python", sys.executable, "qrcode[pil]"],
                    ["/root/.hermes/bin/uv", "pip", "install", "--python", sys.executable, "qrcode[pil]"],
                    [sys.executable, "-m", "pip", "install", "qrcode[pil]"]):
            if subprocess.run(cmd, check=False).returncode == 0:
                break
        try:
            import qrcode
        except ImportError:
            log("qrcode still unavailable — falling back to terminal ASCII QR")
            return False
    img = qrcode.make(payload)          # box_size=10, border=4, ECC-L defaults
    img.save(path)
    return True


def show_qr_on_desktop(path: str):
    """Open the QR PNG in Chrome as a plain file:// tab on the VNC desktop —
    the same mechanism the operator used on the source VM."""
    env = dict(os.environ, DISPLAY=DISPLAY)
    for browser in ("google-chrome-stable", "google-chrome", "chromium"):
        try:
            subprocess.Popen(
                [browser, "--no-sandbox", "--disable-gpu", "--no-first-run",
                 "--no-default-browser-check", f"file://{path}"],
                env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
            return True
        except FileNotFoundError:
            continue
    log("no Chrome/Chromium found — QR saved to " + path)
    return False


def main():
    from hermes_cli.telegram_managed_bot import (
        create_pairing, poll_for_setup_result, render_qr_terminal,
    )
    from hermes_cli.config import save_env_value

    deadline = time.time() + 15 * 60          # try up to 15 min of fresh QRs
    while time.time() < deadline:
        pairing = create_pairing(bot_name="Nick's Stack")
        log("Pairing created. Deep link:")
        print("    " + pairing.deep_link, flush=True)
        if render_qr_png(pairing.qr_payload, QR_PATH):
            show_qr_on_desktop(QR_PATH)
            log("QR shown on the desktop (also at " + QR_PATH + ").")
        else:
            # Fallback: ASCII QR in this terminal.
            try:
                print(render_qr_terminal(pairing.qr_payload), flush=True)
            except Exception:
                pass
        log("Scan it with your phone → Telegram opens → tap 'Create Bot'. "
            "Waiting up to 180s…")
        try:
            result = poll_for_setup_result(None, pairing, timeout=180, interval=2)
        except Exception as exc:
            log(f"Poll ended ({exc}); minting a fresh QR…")
            result = None
        if result and result.token:
            save_env_value("TELEGRAM_BOT_TOKEN", result.token)
            uid = str(result.owner_user_id)
            save_env_value("TELEGRAM_ALLOWED_USERS", uid)
            save_env_value("TELEGRAM_HOME_CHANNEL", uid)
            log(f"Paired! bot=@{result.bot_username}, owner={uid}. Keys written.")
            try:
                os.remove(QR_PATH)
            except OSError:
                pass
            return 0
        log("No pairing yet — regenerating QR…")
    log("Timed out waiting for a Telegram pairing.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
