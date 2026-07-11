"""Pass/fail smoke suite for local Orgo Desktop API computer-use."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Dict, List

from .client import OrgoDesktopClient


def run_smoke(client: OrgoDesktopClient, out_dir: str = "/tmp/orgo-desktop-smoke") -> Dict[str, Any]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    checks: List[Dict[str, Any]] = []

    def add(name: str, ok: bool, detail: Any = None) -> None:
        checks.append({"name": name, "ok": bool(ok), "detail": detail})

    # 1 health
    try:
        h = client.health()
        add("health", h.get("status") == "healthy", h)
    except Exception as e:
        add("health", False, str(e))
        return {"passed": False, "checks": checks}

    # 2 auth via status
    try:
        st = client.status()
        add("auth_status", "state" in st or "cpu_percent" in st, st)
    except Exception as e:
        add("auth_status", False, str(e))
        return {"passed": False, "checks": checks}

    # 3 screenshot
    try:
        path = client.save_screenshot(out / "screenshot.png")
        add(
            "screenshot",
            path.is_file() and path.stat().st_size > 1000,
            {"path": str(path), "bytes": path.stat().st_size},
        )
    except Exception as e:
        add("screenshot", False, str(e))

    # 4 bash
    try:
        b = client.bash("echo SMOKE_OK; hostname; echo DISPLAY=$DISPLAY")
        ok = b.get("exit_code") == 0 and "SMOKE_OK" in (b.get("output") or "")
        add("bash", ok, b)
    except Exception as e:
        add("bash", False, str(e))

    # 5 key (Escape is safe)
    try:
        r = client.key("Escape")
        add("key_escape", r.get("success") is True or r.get("action") is not None, r)
    except Exception as e:
        add("key_escape", False, str(e))

    # 6 click center
    try:
        r = client.click(640, 400)
        add("click_center", r.get("success") is True or r.get("action") is not None, r)
    except Exception as e:
        add("click_center", False, str(e))

    # 7 wait
    try:
        r = client.wait(0.2)
        add("wait", True, r)
    except Exception as e:
        add("wait", False, str(e))

    # 8 post-action screenshot
    try:
        path2 = client.save_screenshot(out / "screenshot_after.png")
        add(
            "screenshot_after",
            path2.is_file() and path2.stat().st_size > 1000,
            {"path": str(path2)},
        )
    except Exception as e:
        add("screenshot_after", False, str(e))

    # 9 doctor prefer fields
    try:
        doc = client.doctor()
        ok = bool(doc.get("ready")) and doc.get("prefer") == "local_desktop_api"
        add(
            "doctor_prefer_local",
            ok,
            {
                "ready": doc.get("ready"),
                "prefer": doc.get("prefer"),
                "control_plane": doc.get("control_plane"),
                "avoid_when_ready": doc.get("avoid_when_ready"),
            },
        )
    except Exception as e:
        add("doctor_prefer_local", False, str(e))

    # 10 fingerprint stability (no action): two hashes should match with top_skip
    try:
        a = client.frame_fingerprint(top_skip=28)
        time.sleep(0.15)
        b = client.frame_fingerprint(top_skip=28)
        add(
            "fingerprint_stable",
            a == b,
            {"fp_a": a[:16], "fp_b": b[:16], "match": a == b},
        )
    except Exception as e:
        add("fingerprint_stable", False, str(e))

    # 11 verify-capable click returns noop/visual_changed keys
    try:
        r = client.click(10, 40, verify=True, settle_s=0.15, top_skip=28)
        ok = "noop" in r and "visual_changed" in r and "fingerprint_before" in r
        add("click_verify_fields", ok, {k: r.get(k) for k in ("success", "noop", "visual_changed")})
    except Exception as e:
        add("click_verify_fields", False, str(e))

    # 12 drag API (small move near top-left chrome/desktop chrome-safe-ish)
    try:
        r = client.drag(50, 50, 80, 55, verify=True, settle_s=0.2)
        ok = r.get("success") is True or r.get("action") is not None or "noop" in r
        add(
            "drag_api",
            ok,
            {k: r.get(k) for k in ("success", "action", "noop", "visual_changed", "error")},
        )
    except Exception as e:
        add("drag_api", False, str(e))

    # 13 click_path fields
    try:
        r = client.click_path(20, 50, 40, 55, settle_s=0.2, verify=True)
        ok = r.get("action") == "click_path" and "destination_noop" in r
        add(
            "click_path_fields",
            ok,
            {
                k: r.get(k)
                for k in (
                    "success",
                    "selection_changed",
                    "destination_changed",
                    "destination_noop",
                    "noop",
                )
            },
        )
    except Exception as e:
        add("click_path_fields", False, str(e))

    passed = all(c["ok"] for c in checks)
    return {
        "passed": passed,
        "base_url": client.base_url,
        "out_dir": str(out),
        "ts": time.time(),
        "checks": checks,
    }
