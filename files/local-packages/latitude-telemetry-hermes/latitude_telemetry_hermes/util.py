from __future__ import annotations

import json
import os
import hashlib
import re
import threading
import time
from typing import Any

_SECRET_PATTERNS = [
    re.compile(r"(?i)(api[_-]?key|authorization|bearer|token|secret|password|cvv|pan|ssn)\s*[:=]\s*[^\s,}]+"),
    re.compile(r"\b(sk-[A-Za-z0-9_-]{16,}|lat_[A-Za-z0-9_-]{16,}|ghp_[A-Za-z0-9_]{16,}|xox[baprs]-[A-Za-z0-9-]{16,})\b"),
]


def _now_ms() -> int:
    return int(time.time() * 1000)


def _ms_to_ns(ms: int) -> str:
    return str(int(ms) * 1_000_000)


def _trace_id() -> str:
    return os.urandom(16).hex()  # 32 hex chars


def _span_id() -> str:
    return os.urandom(8).hex()  # 16 hex chars


def _safe_json(value: Any) -> str:
    try:
        return value if isinstance(value, str) else json.dumps(value, default=str)
    except Exception:
        return ""


def _redact_text(value: Any, max_len: int = 2000) -> str:
    text = _safe_json(value)
    for pattern in _SECRET_PATTERNS:
        text = pattern.sub("[REDACTED]", text)
    if len(text) > max_len:
        return text[:max_len] + f"...[truncated {len(text) - max_len} chars]"
    return text


def _stable_hash(value: Any) -> str:
    return hashlib.sha256(_redact_text(value, max_len=200000).encode("utf-8", errors="replace")).hexdigest()[:16]


def _summarize_value(value: Any, *, depth: int = 0) -> Any:
    if value is None:
        return {"type": "null"}
    if isinstance(value, str):
        stripped = value.strip()
        return {"type": "string", "chars": len(value), "lines": value.count("\n") + (1 if value else 0), "empty": not bool(stripped), "sha256_16": _stable_hash(value)}
    if isinstance(value, bool):
        return {"type": "bool"}
    if isinstance(value, (int, float)):
        return {"type": type(value).__name__}
    if isinstance(value, (list, tuple)):
        out = {"type": "array", "length": len(value)}
        if depth < 1:
            out["items"] = [_summarize_value(v, depth=depth + 1) for v in list(value)[:8]]
            if len(value) > 8:
                out["truncated_items"] = len(value) - 8
        return out
    if isinstance(value, dict):
        keys = [str(k) for k in value.keys()]
        out = {"type": "object", "key_count": len(keys), "keys": keys[:30]}
        if len(keys) > 30:
            out["truncated_keys"] = len(keys) - 30
        if depth < 1:
            out["fields"] = {str(k): _summarize_value(v, depth=depth + 1) for k, v in list(value.items())[:12]}
        return out
    text = _redact_text(value)
    return {"type": type(value).__name__, "chars": len(text), "sha256_16": _stable_hash(text)}


def _summarize_messages(messages: Any) -> dict[str, Any]:
    if not isinstance(messages, (list, tuple)):
        return {"type": type(messages).__name__, "message_count": 0}
    roles: dict[str, int] = {}
    total_chars = 0
    tool_call_count = 0
    last_user = ""
    system_chars = 0
    for msg in messages:
        if not isinstance(msg, dict):
            continue
        role = str(msg.get("role") or "unknown")
        roles[role] = roles.get(role, 0) + 1
        text = _redact_text(msg.get("content"), max_len=200000)
        total_chars += len(text)
        if role == "user":
            last_user = text
        if role == "system":
            system_chars += len(text)
        tc = msg.get("tool_calls")
        if isinstance(tc, list):
            tool_call_count += len(tc)
    return {
        "message_count": len(messages),
        "roles": roles,
        "total_content_chars": total_chars,
        "system_content_chars": system_chars,
        "tool_call_count": tool_call_count,
        "last_user_chars": len(last_user),
        "last_user_sha256_16": _stable_hash(last_user) if last_user else None,
    }


def _get(obj: Any, name: str) -> Any:
    """Read a field whether the payload is a dict or an object."""
    if isinstance(obj, dict):
        return obj.get(name)
    return getattr(obj, name, None)


def _trace_key(task_id: str, session_id: str, turn_id: str, api_request_id: str) -> str:
    """Stable per-turn scope key (mirrors Hermes's langfuse plugin)."""
    prefix = (
        f"task:{task_id}" if task_id else f"session:{session_id}" if session_id else f"thread:{threading.get_ident()}"
    )
    if turn_id:
        return f"{prefix}:turn:{turn_id}"
    if api_request_id:
        return f"{prefix}:api:{api_request_id}"
    return task_id or prefix
