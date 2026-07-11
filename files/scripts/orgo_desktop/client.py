"""HTTP client for Orgo's in-VM Desktop API.

Auth: Bearer <vnc_password> (NOT ORGO_API_KEY).
Base: http://127.0.0.1:8080 by default (ORGO_DESKTOP_API_URL override).

Coordinate space: full desktop pixels as returned by /screenshot
(typically 1280x720 on Dewey).
"""

from __future__ import annotations

import base64
import hashlib
import io
import json
import os
import socket
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Tuple

try:
    from PIL import Image  # type: ignore
except Exception:  # pragma: no cover
    Image = None  # type: ignore


DEFAULT_BASE = "http://127.0.0.1:8080"
DEFAULT_TIMEOUT = 30


class DesktopAPIError(RuntimeError):
    def __init__(self, message: str, *, status: Optional[int] = None, body: Any = None):
        super().__init__(message)
        self.status = status
        self.body = body


def _read_env_file_value(path: Path, key: str) -> Optional[str]:
    if not path.is_file():
        return None
    try:
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            if k.strip() != key:
                continue
            v = v.strip().strip("'").strip('"')
            return v or None
    except OSError:
        return None
    return None


def discover_token() -> str:
    """Resolve desktop-api bearer token (VNC password).

    Order:
      1. ORGO_DESKTOP_API_TOKEN
      2. VNC_PASSWORD
      3. ~/.hermes/.env VNC_PASSWORD
      4. /tmp/.vncpasswd is binary — skip
    """
    for key in ("ORGO_DESKTOP_API_TOKEN", "VNC_PASSWORD"):
        val = os.environ.get(key)
        if val:
            return val
    hermes_home = Path(os.environ.get("HERMES_HOME", Path.home() / ".hermes"))
    for key in ("ORGO_DESKTOP_API_TOKEN", "VNC_PASSWORD"):
        val = _read_env_file_value(hermes_home / ".env", key)
        if val:
            return val
    raise DesktopAPIError(
        "No desktop-api token found. Set VNC_PASSWORD or ORGO_DESKTOP_API_TOKEN "
        "(this is the per-VM vnc_password, not ORGO_API_KEY)."
    )


def is_colocated(base_url: str = DEFAULT_BASE, timeout: float = 1.5) -> bool:
    """True if local desktop-api /health answers."""
    try:
        req = urllib.request.Request(base_url.rstrip("/") + "/health")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8", errors="replace"))
        return data.get("service") == "orgo-desktop-api" or data.get("status") == "healthy"
    except Exception:
        return False


@dataclass
class OrgoDesktopClient:
    base_url: str = DEFAULT_BASE
    token: Optional[str] = None
    timeout: float = DEFAULT_TIMEOUT

    def __post_init__(self) -> None:
        self.base_url = self.base_url.rstrip("/")
        if self.token is None:
            self.token = discover_token()

    # ── HTTP ──────────────────────────────────────────────────────────

    def _request(
        self,
        method: str,
        path: str,
        body: Optional[Dict[str, Any]] = None,
        *,
        auth: bool = True,
        timeout: Optional[float] = None,
    ) -> Any:
        url = self.base_url + path
        data = None if body is None else json.dumps(body).encode("utf-8")
        headers = {"Accept": "application/json"}
        if body is not None:
            headers["Content-Type"] = "application/json"
        if auth:
            headers["Authorization"] = f"Bearer {self.token}"
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=timeout or self.timeout) as resp:
                raw = resp.read()
                if not raw:
                    return {"status": resp.status}
                try:
                    return json.loads(raw.decode("utf-8"))
                except json.JSONDecodeError:
                    return {"status": resp.status, "raw": raw[:500].decode("utf-8", errors="replace")}
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="replace")
            try:
                parsed = json.loads(err_body)
            except json.JSONDecodeError:
                parsed = err_body
            raise DesktopAPIError(
                f"{method} {path} -> HTTP {e.code}: {parsed}",
                status=e.code,
                body=parsed,
            ) from e
        except (urllib.error.URLError, TimeoutError, socket.timeout) as e:
            raise DesktopAPIError(f"{method} {path} failed: {e}") from e

    # ── Discovery ─────────────────────────────────────────────────────

    def health(self) -> Dict[str, Any]:
        return self._request("GET", "/health", auth=False)

    def info(self) -> Dict[str, Any]:
        return self._request("GET", "/")

    def status(self) -> Dict[str, Any]:
        return self._request("GET", "/status")

    def schema(self) -> Dict[str, Any]:
        return self._request("GET", "/schema", auth=False)

    def doctor(self) -> Dict[str, Any]:
        """Structured readiness report for same-box computer use."""
        report: Dict[str, Any] = {
            "base_url": self.base_url,
            "colocated": False,
            "health": None,
            "auth_ok": False,
            "screenshot_ok": False,
            "bash_ok": False,
            "display": os.environ.get("DISPLAY"),
            "hostname": socket.gethostname(),
            "errors": [],
        }
        try:
            h = self.health()
            report["health"] = h
            report["colocated"] = h.get("service") == "orgo-desktop-api" or h.get("status") == "healthy"
        except Exception as e:
            report["errors"].append(f"health: {e}")
            return report

        try:
            st = self.status()
            report["status"] = st
            report["auth_ok"] = True
        except Exception as e:
            report["errors"].append(f"auth/status: {e}")
            return report

        try:
            shot = self.screenshot()
            report["screenshot_ok"] = bool(shot.get("success") and shot.get("image"))
            report["screenshot_bytes"] = len(base64.b64decode(shot["image"])) if shot.get("image") else 0
        except Exception as e:
            report["errors"].append(f"screenshot: {e}")

        try:
            b = self.bash("echo ok-desktop-api; hostname")
            report["bash_ok"] = b.get("exit_code") == 0 and "ok-desktop-api" in (b.get("output") or "")
            report["bash_sample"] = (b.get("output") or "")[:200]
        except Exception as e:
            report["errors"].append(f"bash: {e}")

        report["ready"] = bool(
            report["colocated"] and report["auth_ok"] and report["screenshot_ok"] and report["bash_ok"]
        )
        # Machine-readable routing for agents (co-located vs cloud MCP).
        if report["ready"]:
            report["control_plane"] = "local_desktop_api"
            report["prefer"] = "local_desktop_api"
            report["avoid_when_ready"] = [
                "mcp__orgo__* GUI tools for this VM",
                "cloud www.orgo.ai computer GUI hop when controlling this desktop",
            ]
            report["guidance"] = (
                "ready=true: use orgo_desktop_* model tools or orgo-desktop CLI / "
                "OrgoDesktopClient against loopback :8080. Do not use cloud Orgo MCP "
                "GUI for this same desktop. Cloud MCP remains for other VMs / lifecycle."
            )
        else:
            report["control_plane"] = "unavailable"
            report["prefer"] = "fix_local_or_use_cloud_for_remote_vms"
            report["avoid_when_ready"] = []
            report["guidance"] = (
                "Local desktop-api not ready. Fix VNC_PASSWORD / :8080, or use cloud "
                "Orgo MCP only for remote computers / fleet lifecycle."
            )
        return report

    # ── Sense ─────────────────────────────────────────────────────────

    def screenshot(self) -> Dict[str, Any]:
        return self._request("GET", "/screenshot")

    def save_screenshot(self, path: str | Path) -> Path:
        data = self.screenshot()
        if not data.get("image"):
            raise DesktopAPIError(f"screenshot missing image field: {data}")
        out = Path(path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(base64.b64decode(data["image"]))
        return out

    def cursor_position(self) -> Dict[str, Any]:
        # schema marks GET 405 in practice; try POST empty if needed
        try:
            return self._request("POST", "/cursor_position", {})
        except DesktopAPIError:
            return self._request("GET", "/cursor_position")

    # ── Actions ───────────────────────────────────────────────────────
    # click/drag live below with optional verify= (visual noop detection).

    def double_click(self, x: int, y: int) -> Dict[str, Any]:
        return self._request("POST", "/double_click", {"x": int(x), "y": int(y)})

    def mouse_move(self, x: int, y: int) -> Dict[str, Any]:
        return self._request("POST", "/mouse_move", {"x": int(x), "y": int(y)})

    def type_text(self, text: str, *, delay_ms: int = 12) -> Dict[str, Any]:
        return self._request("POST", "/type", {"text": text, "delay_ms": int(delay_ms)})

    def key(self, key: str) -> Dict[str, Any]:
        return self._request("POST", "/key", {"key": key})

    def scroll(
        self,
        direction: str = "down",
        amount: int = 3,
        *,
        x: int = 0,
        y: int = 0,
    ) -> Dict[str, Any]:
        return self._request(
            "POST",
            "/scroll",
            {"direction": direction, "amount": int(amount), "x": int(x), "y": int(y)},
        )

    def wait(self, seconds: float) -> Dict[str, Any]:
        return self._request("POST", "/wait", {"seconds": float(seconds)})

    # ── Execution ─────────────────────────────────────────────────────

    def bash(self, command: str, *, timeout: int = 200) -> Dict[str, Any]:
        return self._request(
            "POST",
            "/bash",
            {"command": command, "timeout": int(timeout)},
            timeout=max(self.timeout, float(timeout) + 5),
        )

    def exec_python(self, code: str) -> Dict[str, Any]:
        return self._request("POST", "/exec", {"code": code})

    # ── Convenience ───────────────────────────────────────────────────

    def open_url(self, url: str, *, browser: str = "google-chrome") -> Dict[str, Any]:
        """Open a URL in headed Chrome on the desktop (bash path)."""
        # Prefer chrome with flags known to work as root on Orgo images.
        cmd = (
            f'export DISPLAY="${{DISPLAY:-:99}}"; '
            f'nohup {browser} --no-sandbox --no-first-run --disable-session-crashed-bubble '
            f'--new-window {json.dumps(url)} >/tmp/orgo-desktop-browser.log 2>&1 & echo started:$!'
        )
        return self.bash(cmd, timeout=15)

    # ── Visual verify / noop detection ────────────────────────────────

    def screenshot_png_bytes(self) -> bytes:
        data = self.screenshot()
        if not data.get("image"):
            raise DesktopAPIError(f"screenshot missing image field: {data}")
        return base64.b64decode(data["image"])

    def frame_fingerprint(
        self,
        png_bytes: Optional[bytes] = None,
        *,
        top_skip: int = 28,
        bottom_skip: int = 0,
        left_skip: int = 0,
        right_skip: int = 0,
        bbox: Optional[Tuple[int, int, int, int]] = None,
    ) -> str:
        """Stable-ish hash of desktop pixels for noop detection.

        Default crops off the top panel (clock/tray) so second-level clock
        ticks do not force every compare to report a change. Pass bbox=
        (left, top, right, bottom) for a board/window ROI.
        """
        if png_bytes is None:
            png_bytes = self.screenshot_png_bytes()
        if Image is not None:
            im = Image.open(io.BytesIO(png_bytes)).convert("RGB")
            w, h = im.size
            if bbox is not None:
                left, top, right, bottom = bbox
                im = im.crop((left, top, right, bottom))
            else:
                left = max(0, left_skip)
                top = max(0, top_skip)
                right = w - max(0, right_skip)
                bottom = h - max(0, bottom_skip)
                if right > left and bottom > top:
                    im = im.crop((left, top, right, bottom))
            return hashlib.sha256(im.tobytes()).hexdigest()
        # Fallback: full PNG digest (clock may cause false visual_changed)
        return hashlib.sha256(png_bytes).hexdigest()

    def _attach_verify(
        self,
        result: Dict[str, Any],
        *,
        before_fp: str,
        after_fp: str,
        settle_s: float,
        top_skip: int,
        bbox: Optional[Tuple[int, int, int, int]],
    ) -> Dict[str, Any]:
        changed = before_fp != after_fp
        out = dict(result) if isinstance(result, dict) else {"api_result": result}
        out["visual_changed"] = changed
        out["noop"] = not changed
        out["fingerprint_before"] = before_fp
        out["fingerprint_after"] = after_fp
        out["verify"] = {
            "settle_s": settle_s,
            "top_skip": top_skip,
            "bbox": list(bbox) if bbox else None,
            "note": (
                "noop=true means cropped frame hash unchanged after action; "
                "API success alone does not prove UI state changed"
            ),
        }
        return out

    def click(
        self,
        x: int,
        y: int,
        *,
        button: str = "left",
        double: bool = False,
        verify: bool = False,
        settle_s: float = 0.2,
        top_skip: int = 28,
        bbox: Optional[Tuple[int, int, int, int]] = None,
    ) -> Dict[str, Any]:
        before = self.frame_fingerprint(top_skip=top_skip, bbox=bbox) if verify else None
        result = self._request(
            "POST",
            "/click",
            {"x": int(x), "y": int(y), "button": button, "double": bool(double)},
        )
        if not verify:
            return result
        time.sleep(max(0.0, float(settle_s)))
        after = self.frame_fingerprint(top_skip=top_skip, bbox=bbox)
        return self._attach_verify(
            result,
            before_fp=before or "",
            after_fp=after,
            settle_s=settle_s,
            top_skip=top_skip,
            bbox=bbox,
        )

    def drag(
        self,
        start_x: int,
        start_y: int,
        end_x: int,
        end_y: int,
        *,
        verify: bool = False,
        settle_s: float = 0.25,
        top_skip: int = 28,
        bbox: Optional[Tuple[int, int, int, int]] = None,
    ) -> Dict[str, Any]:
        before = self.frame_fingerprint(top_skip=top_skip, bbox=bbox) if verify else None
        result = self._request(
            "POST",
            "/drag",
            {
                "start_x": int(start_x),
                "start_y": int(start_y),
                "end_x": int(end_x),
                "end_y": int(end_y),
            },
        )
        if not verify:
            return result
        time.sleep(max(0.0, float(settle_s)))
        after = self.frame_fingerprint(top_skip=top_skip, bbox=bbox)
        return self._attach_verify(
            result,
            before_fp=before or "",
            after_fp=after,
            settle_s=settle_s,
            top_skip=top_skip,
            bbox=bbox,
        )

    def click_path(
        self,
        x1: int,
        y1: int,
        x2: int,
        y2: int,
        *,
        settle_s: float = 0.35,
        verify: bool = True,
        top_skip: int = 28,
        bbox: Optional[Tuple[int, int, int, int]] = None,
        button: str = "left",
    ) -> Dict[str, Any]:
        """Two-click gesture (select then destination) with optional visual checks.

        Reports:
          - selection_changed: first click altered cropped frame
          - destination_changed: second click altered frame vs post-selection
          - visual_changed / noop: overall before→after
        Destination noops (API success, UI unchanged) match real Lichess misses.
        """
        before = self.frame_fingerprint(top_skip=top_skip, bbox=bbox) if verify else None
        r1 = self._request(
            "POST",
            "/click",
            {"x": int(x1), "y": int(y1), "button": button, "double": False},
        )
        time.sleep(max(0.0, float(settle_s)))
        mid = self.frame_fingerprint(top_skip=top_skip, bbox=bbox) if verify else None
        r2 = self._request(
            "POST",
            "/click",
            {"x": int(x2), "y": int(y2), "button": button, "double": False},
        )
        time.sleep(max(0.0, float(settle_s)))
        after = self.frame_fingerprint(top_skip=top_skip, bbox=bbox) if verify else None

        out: Dict[str, Any] = {
            "success": bool(
                (isinstance(r1, dict) and r1.get("success", True))
                and (isinstance(r2, dict) and r2.get("success", True))
            ),
            "action": "click_path",
            "from": [int(x1), int(y1)],
            "to": [int(x2), int(y2)],
            "steps": [r1, r2],
        }
        if verify and before is not None and mid is not None and after is not None:
            selection_changed = before != mid
            destination_changed = mid != after
            overall = before != after
            out["selection_changed"] = selection_changed
            out["destination_changed"] = destination_changed
            out["visual_changed"] = overall
            out["noop"] = not overall
            out["destination_noop"] = not destination_changed
            out["fingerprint_before"] = before
            out["fingerprint_after_select"] = mid
            out["fingerprint_after"] = after
            out["verify"] = {
                "settle_s": settle_s,
                "top_skip": top_skip,
                "bbox": list(bbox) if bbox else None,
                "note": (
                    "destination_noop=true means second click did not change pixels "
                    "(common when illegal/missed board square despite API success)"
                ),
            }
        return out


def default_client() -> OrgoDesktopClient:
    base = os.environ.get("ORGO_DESKTOP_API_URL", DEFAULT_BASE)
    return OrgoDesktopClient(base_url=base)
