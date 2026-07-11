"""Tool handlers for orgo-desktop-local plugin.

Handlers wrap ~/.hermes/scripts/orgo_desktop.client.OrgoDesktopClient.
Return JSON strings via tools.registry.tool_result / tool_error.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

# Client package lives under HERMES_HOME/scripts
_SCRIPTS = Path.home() / ".hermes" / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from tools.registry import tool_error, tool_result  # noqa: E402

try:
    from orgo_desktop.client import (  # noqa: E402
        DesktopAPIError,
        OrgoDesktopClient,
        is_colocated,
    )
except Exception:  # pragma: no cover - import errors surface via check_fn
    DesktopAPIError = Exception  # type: ignore
    OrgoDesktopClient = None  # type: ignore

    def is_colocated(*_a, **_k):  # type: ignore
        return False


def check_desktop_available() -> bool:
    """Gate: local desktop-api must answer /health."""
    try:
        return bool(is_colocated())
    except Exception:
        return False


def _client() -> OrgoDesktopClient:
    if OrgoDesktopClient is None:
        raise RuntimeError(
            "orgo_desktop client not importable; ensure "
            "~/.hermes/scripts/orgo_desktop is present"
        )
    return OrgoDesktopClient()


def _err(exc: Exception) -> str:
    if isinstance(exc, DesktopAPIError):
        return tool_error(str(exc), status=getattr(exc, "status", None))
    return tool_error(f"{type(exc).__name__}: {exc}")


def _bbox(params: Dict[str, Any]) -> Optional[Tuple[int, int, int, int]]:
    raw = params.get("bbox")
    if not raw:
        return None
    if isinstance(raw, (list, tuple)) and len(raw) == 4:
        return int(raw[0]), int(raw[1]), int(raw[2]), int(raw[3])
    if isinstance(raw, str) and "," in raw:
        parts = [int(x.strip()) for x in raw.split(",")]
        if len(parts) == 4:
            return parts[0], parts[1], parts[2], parts[3]
    return None


# ── schemas ──────────────────────────────────────────────────────────

DOCTOR_SCHEMA = {
    "name": "orgo_desktop_doctor",
    "description": (
        "Same-box Orgo Desktop API readiness check (health, auth, screenshot, bash). "
        "When ready=true, prefer orgo_desktop_* / loopback :8080 over cloud Orgo MCP GUI "
        "for this VM. Returns control_plane, prefer, avoid_when_ready, guidance."
    ),
    "parameters": {"type": "object", "properties": {}, "required": []},
}

SCREENSHOT_SCHEMA = {
    "name": "orgo_desktop_screenshot",
    "description": (
        "Capture the full local Orgo desktop via loopback Desktop API and save PNG. "
        "Returns absolute path + size. Coordinate space is the full desktop (typically 1280x720)."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Optional absolute path for the PNG (default /tmp/orgo-desktop-shot.png)",
            }
        },
        "required": [],
    },
}

CLICK_SCHEMA = {
    "name": "orgo_desktop_click",
    "description": (
        "Click at desktop pixel coordinates via local Orgo Desktop API (not cloud MCP). "
        "Coords are full-desktop pixels from orgo_desktop_screenshot. "
        "Set verify=true to attach visual_changed/noop fingerprints (top panel cropped)."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "x": {"type": "integer", "description": "X pixel"},
            "y": {"type": "integer", "description": "Y pixel"},
            "button": {
                "type": "string",
                "enum": ["left", "right", "middle"],
                "description": "Mouse button (default left)",
            },
            "double": {
                "type": "boolean",
                "description": "Double-click if true",
            },
            "verify": {
                "type": "boolean",
                "description": "If true, compare frame fingerprint before/after",
            },
            "settle_s": {
                "type": "number",
                "description": "Seconds to wait before post-hash when verify (default 0.2)",
            },
            "bbox": {
                "description": "Optional ROI [left,top,right,bottom] for verify hash",
            },
        },
        "required": ["x", "y"],
    },
}

DRAG_SCHEMA = {
    "name": "orgo_desktop_drag",
    "description": (
        "Drag from (start_x,start_y) to (end_x,end_y) via local Desktop API /drag. "
        "Prefer for piece moves / sliders when two-click is flaky. Optional verify fingerprints."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "start_x": {"type": "integer"},
            "start_y": {"type": "integer"},
            "end_x": {"type": "integer"},
            "end_y": {"type": "integer"},
            "verify": {"type": "boolean"},
            "settle_s": {"type": "number"},
            "bbox": {"description": "Optional ROI [left,top,right,bottom] for verify"},
        },
        "required": ["start_x", "start_y", "end_x", "end_y"],
    },
}

CLICK_PATH_SCHEMA = {
    "name": "orgo_desktop_click_path",
    "description": (
        "Two-click select→destination on the local desktop. Default verify=true reports "
        "selection_changed, destination_changed, destination_noop, visual_changed. "
        "Use when moving pieces/icons; if destination_noop=true the second click did not "
        "change pixels (re-plan — do not trust API success alone)."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "x1": {"type": "integer", "description": "From X"},
            "y1": {"type": "integer", "description": "From Y"},
            "x2": {"type": "integer", "description": "To X"},
            "y2": {"type": "integer", "description": "To Y"},
            "settle_s": {"type": "number", "description": "Pause between clicks (default 0.35)"},
            "verify": {"type": "boolean", "description": "Default true"},
            "button": {"type": "string", "enum": ["left", "right", "middle"]},
            "bbox": {"description": "Optional ROI [left,top,right,bottom] for verify"},
        },
        "required": ["x1", "y1", "x2", "y2"],
    },
}

TYPE_SCHEMA = {
    "name": "orgo_desktop_type",
    "description": "Type text into the focused desktop window via local Desktop API.",
    "parameters": {
        "type": "object",
        "properties": {
            "text": {"type": "string", "description": "Text to type"},
            "delay_ms": {
                "type": "integer",
                "description": "Milliseconds between keystrokes (default 12)",
            },
        },
        "required": ["text"],
    },
}

KEY_SCHEMA = {
    "name": "orgo_desktop_key",
    "description": (
        "Press a key or chord via local Desktop API "
        "(e.g. Return, Escape, ctrl+l, ctrl+c, alt+Tab)."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "key": {"type": "string", "description": "Key name or combination"},
        },
        "required": ["key"],
    },
}

BASH_SCHEMA = {
    "name": "orgo_desktop_bash",
    "description": (
        "Run a shell command through the local Orgo Desktop API /bash endpoint "
        "(desktop environment, DISPLAY=:99). Prefer Hermes terminal for pure "
        "agent-side work; use this when the command must run in the desktop session."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "command": {"type": "string", "description": "Shell command"},
            "timeout": {
                "type": "integer",
                "description": "Timeout seconds (default 60)",
            },
        },
        "required": ["command"],
    },
}

SCROLL_SCHEMA = {
    "name": "orgo_desktop_scroll",
    "description": "Scroll at a desktop point via local Desktop API.",
    "parameters": {
        "type": "object",
        "properties": {
            "direction": {"type": "string", "enum": ["up", "down"]},
            "amount": {"type": "integer", "description": "Scroll ticks (default 3)"},
            "x": {"type": "integer", "description": "X pixel (default 640)"},
            "y": {"type": "integer", "description": "Y pixel (default 360)"},
        },
        "required": ["direction"],
    },
}

OPEN_URL_SCHEMA = {
    "name": "orgo_desktop_open_url",
    "description": (
        "Open a URL in headed Chrome on the Orgo desktop (bash path with --no-sandbox). "
        "User can watch via the Orgo dashboard stream."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "URL to open"},
        },
        "required": ["url"],
    },
}

WAIT_SCHEMA = {
    "name": "orgo_desktop_wait",
    "description": "Wait N seconds via Desktop API /wait (max 60).",
    "parameters": {
        "type": "object",
        "properties": {
            "seconds": {"type": "number", "description": "Seconds to wait (max 60)"},
        },
        "required": ["seconds"],
    },
}


# ── handlers ─────────────────────────────────────────────────────────

def handle_doctor(params: Dict[str, Any], **kwargs) -> str:
    del kwargs, params
    try:
        report = _client().doctor()
        return tool_result(report)
    except Exception as e:
        return _err(e)


def handle_screenshot(params: Dict[str, Any], **kwargs) -> str:
    del kwargs
    path = params.get("path") or "/tmp/orgo-desktop-shot.png"
    try:
        out = _client().save_screenshot(path)
        return tool_result(
            {
                "ok": True,
                "path": str(out),
                "bytes": out.stat().st_size,
                "coordinate_space": "full_desktop",
            }
        )
    except Exception as e:
        return _err(e)


def handle_click(params: Dict[str, Any], **kwargs) -> str:
    del kwargs
    try:
        r = _client().click(
            int(params["x"]),
            int(params["y"]),
            button=str(params.get("button") or "left"),
            double=bool(params.get("double") or False),
            verify=bool(params.get("verify") or False),
            settle_s=float(params.get("settle_s") or 0.2),
            bbox=_bbox(params),
        )
        return tool_result(r)
    except Exception as e:
        return _err(e)


def handle_drag(params: Dict[str, Any], **kwargs) -> str:
    del kwargs
    try:
        r = _client().drag(
            int(params["start_x"]),
            int(params["start_y"]),
            int(params["end_x"]),
            int(params["end_y"]),
            verify=bool(params.get("verify") or False),
            settle_s=float(params.get("settle_s") or 0.25),
            bbox=_bbox(params),
        )
        return tool_result(r)
    except Exception as e:
        return _err(e)


def handle_click_path(params: Dict[str, Any], **kwargs) -> str:
    del kwargs
    try:
        verify = params.get("verify")
        if verify is None:
            verify = True
        r = _client().click_path(
            int(params["x1"]),
            int(params["y1"]),
            int(params["x2"]),
            int(params["y2"]),
            settle_s=float(params.get("settle_s") or 0.35),
            verify=bool(verify),
            bbox=_bbox(params),
            button=str(params.get("button") or "left"),
        )
        return tool_result(r)
    except Exception as e:
        return _err(e)


def handle_type(params: Dict[str, Any], **kwargs) -> str:
    del kwargs
    try:
        delay = int(params.get("delay_ms") or 12)
        r = _client().type_text(str(params["text"]), delay_ms=delay)
        return tool_result(r)
    except Exception as e:
        return _err(e)


def handle_key(params: Dict[str, Any], **kwargs) -> str:
    del kwargs
    try:
        r = _client().key(str(params["key"]))
        return tool_result(r)
    except Exception as e:
        return _err(e)


def handle_bash(params: Dict[str, Any], **kwargs) -> str:
    del kwargs
    try:
        timeout = int(params.get("timeout") or 60)
        r = _client().bash(str(params["command"]), timeout=timeout)
        return tool_result(r)
    except Exception as e:
        return _err(e)


def handle_scroll(params: Dict[str, Any], **kwargs) -> str:
    del kwargs
    try:
        r = _client().scroll(
            direction=str(params.get("direction") or "down"),
            amount=int(params.get("amount") or 3),
            x=int(params.get("x") or 640),
            y=int(params.get("y") or 360),
        )
        return tool_result(r)
    except Exception as e:
        return _err(e)


def handle_open_url(params: Dict[str, Any], **kwargs) -> str:
    del kwargs
    try:
        r = _client().open_url(str(params["url"]))
        return tool_result(r)
    except Exception as e:
        return _err(e)


def handle_wait(params: Dict[str, Any], **kwargs) -> str:
    del kwargs
    try:
        r = _client().wait(float(params["seconds"]))
        return tool_result(r)
    except Exception as e:
        return _err(e)
