"""latitude — Hermes plugin for Latitude/OpenTelemetry observability.

Traces Hermes agent turns, LLM requests, tool calls, and provider errors to
Latitude using standard OTLP/HTTP JSON. The implementation intentionally avoids
optional SDK dependencies so it works in packaged Hermes installs that do not
ship pip.

Activation is handled by the Hermes plugin system. Enable with:

    hermes plugins enable observability/latitude

Required env vars (set in ~/.hermes/.env):
  HERMES_LATITUDE_API_KEY  - Latitude project API key
  HERMES_LATITUDE_PROJECT  - Latitude project slug

Optional env vars:
  HERMES_LATITUDE_ENDPOINT - OTLP traces endpoint
                             (default: https://ingest.latitude.so/v1/traces)
  HERMES_LATITUDE_SERVICE  - service.name resource attribute
                             (default: hermes-agent)
  HERMES_LATITUDE_ENV      - deployment.environment resource attribute
  HERMES_LATITUDE_DEBUG    - truthy value enables debug logging
"""
from __future__ import annotations

import json
import logging
import os
import random
import threading
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

DEFAULT_ENDPOINT = "https://ingest.latitude.so/v1/traces"
DEFAULT_SERVICE_NAME = "hermes-agent"
_SCOPE_NAME = "hermes-agent.latitude"
_SCOPE_VERSION = "1.0.0"


@dataclass(frozen=True)
class LatitudeConfig:
    api_key: str
    project: str
    endpoint: str = DEFAULT_ENDPOINT
    service_name: str = DEFAULT_SERVICE_NAME
    environment: str = ""


@dataclass
class TraceState:
    trace_id: str
    root_span_id: str
    task_id: str = ""
    turn_id: str = ""
    session_id: str = ""
    platform: str = ""
    model: str = ""
    provider: str = ""
    api_mode: str = ""
    root_start: float = field(default_factory=time.time)
    spans: list[dict[str, Any]] = field(default_factory=list)
    errored: bool = False
    error_message: str = ""
    last_updated_at: float = field(default_factory=time.time)


_STATE_LOCK = threading.Lock()
_TRACE_STATE: Dict[str, TraceState] = {}
_CONFIG_CACHE: Optional[LatitudeConfig] | object = None
_INIT_FAILED = object()


def _env(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


def _env_bool(name: str) -> bool:
    return _env(name).lower() in {"1", "true", "yes", "on"}


def _debug(message: str) -> None:
    if _env_bool("HERMES_LATITUDE_DEBUG"):
        logger.info("Latitude tracing: %s", message)


def _get_config() -> Optional[LatitudeConfig]:
    """Return Latitude runtime config, or None when not configured.

    Successful config is cached per process. Missing env is intentionally not
    cached so a test or early-starting process can set credentials later before
    the first real trace. Operators should still restart Hermes after changing
    Latitude env vars in normal runtime use.
    """
    global _CONFIG_CACHE
    if isinstance(_CONFIG_CACHE, LatitudeConfig):
        return _CONFIG_CACHE

    api_key = _env("HERMES_LATITUDE_API_KEY") or _env("LATITUDE_API_KEY")
    project = _env("HERMES_LATITUDE_PROJECT") or _env("LATITUDE_PROJECT")
    if not api_key or not project:
        return None

    _CONFIG_CACHE = LatitudeConfig(
        api_key=api_key,
        project=project,
        endpoint=_env("HERMES_LATITUDE_ENDPOINT") or _env("LATITUDE_ENDPOINT") or DEFAULT_ENDPOINT,
        service_name=_env("HERMES_LATITUDE_SERVICE") or _env("OTEL_SERVICE_NAME") or DEFAULT_SERVICE_NAME,
        environment=_env("HERMES_LATITUDE_ENV") or _env("OTEL_ENVIRONMENT"),
    )
    return _CONFIG_CACHE


def reset_for_tests() -> None:
    global _CONFIG_CACHE
    with _STATE_LOCK:
        _TRACE_STATE.clear()
    _CONFIG_CACHE = None


def _trace_key(task_id: str = "", turn_id: str = "", session_id: str = "") -> str:
    if task_id:
        return task_id
    if turn_id:
        return f"turn:{turn_id}"
    if session_id:
        return f"session:{session_id}"
    return f"thread:{threading.get_ident()}"


def _rand_hex(n_bytes: int) -> str:
    return random.randbytes(n_bytes).hex() if hasattr(random, "randbytes") else os.urandom(n_bytes).hex()


def _ts_nanos(ts: Optional[float]) -> str:
    if ts is None:
        ts = time.time()
    return str(int(float(ts) * 1_000_000_000))


def _duration_end(started_at: Optional[float], duration_seconds: Optional[float]) -> float:
    if started_at is None:
        return time.time()
    if duration_seconds is None:
        return time.time()
    return float(started_at) + float(duration_seconds)


def _attr_value(value: Any) -> Optional[dict[str, Any]]:
    if value is None:
        return None
    if isinstance(value, bool):
        return {"boolValue": value}
    if isinstance(value, int) and not isinstance(value, bool):
        return {"intValue": str(value)}
    if isinstance(value, float):
        return {"doubleValue": value}
    if isinstance(value, (dict, list, tuple)):
        try:
            value = json.dumps(value, ensure_ascii=False, default=str)
        except Exception:
            value = str(value)
    return {"stringValue": str(value)}


def _attrs(values: Dict[str, Any]) -> list[dict[str, Any]]:
    attrs = []
    for key, value in values.items():
        encoded = _attr_value(value)
        if encoded is not None:
            attrs.append({"key": key, "value": encoded})
    return attrs


def _status(ok: bool, message: str = "") -> dict[str, Any]:
    status: dict[str, Any] = {"code": 1 if ok else 2}
    if message:
        status["message"] = str(message)[:1024]
    return status


def _span(
    *,
    trace_id: str,
    span_id: str,
    name: str,
    parent_span_id: str = "",
    start: Optional[float] = None,
    end: Optional[float] = None,
    attributes: Optional[Dict[str, Any]] = None,
    ok: bool = True,
    status_message: str = "",
    kind: int = 1,
) -> dict[str, Any]:
    if end is None:
        end = time.time()
    if start is None:
        start = end
    out = {
        "traceId": trace_id,
        "spanId": span_id,
        "name": name,
        "kind": kind,
        "startTimeUnixNano": _ts_nanos(start),
        "endTimeUnixNano": _ts_nanos(end),
        "attributes": _attrs(attributes or {}),
        "status": _status(ok, status_message),
    }
    if parent_span_id:
        out["parentSpanId"] = parent_span_id
    return out


def _state_for(
    *,
    task_id: str = "",
    turn_id: str = "",
    session_id: str = "",
    platform: str = "",
    model: str = "",
    provider: str = "",
    api_mode: str = "",
    started_at: Optional[float] = None,
) -> TraceState:
    key = _trace_key(task_id, turn_id, session_id)
    state = _TRACE_STATE.get(key)
    if state is None:
        state = TraceState(
            trace_id=_rand_hex(16),
            root_span_id=_rand_hex(8),
            task_id=task_id or "",
            turn_id=turn_id or "",
            session_id=session_id or "",
            platform=platform or "",
            model=model or "",
            provider=provider or "",
            api_mode=api_mode or "",
            root_start=float(started_at) if started_at is not None else time.time(),
        )
        _TRACE_STATE[key] = state
    else:
        state.task_id = state.task_id or task_id or ""
        state.turn_id = state.turn_id or turn_id or ""
        state.session_id = state.session_id or session_id or ""
        state.platform = state.platform or platform or ""
        state.model = model or state.model
        state.provider = provider or state.provider
        state.api_mode = api_mode or state.api_mode
    state.last_updated_at = time.time()
    return state


def _usage_attr(usage: Any, key: str) -> Optional[int]:
    if not isinstance(usage, dict):
        return None
    value = usage.get(key)
    if value is None and key == "completion_tokens":
        value = usage.get("output_tokens")
    if value is None and key == "prompt_tokens":
        value = usage.get("input_tokens")
    try:
        return int(value) if value is not None else None
    except Exception:
        return None


def _resource_attributes(cfg: LatitudeConfig, state: TraceState) -> Dict[str, Any]:
    attrs = {
        "service.name": cfg.service_name,
        "telemetry.sdk.name": "hermes-latitude-plugin",
        "telemetry.sdk.language": "python",
        "hermes.session_id": state.session_id,
        "hermes.platform": state.platform,
    }
    if cfg.environment:
        attrs["deployment.environment"] = cfg.environment
    return attrs


def _build_payload(cfg: LatitudeConfig, state: TraceState, root_end: Optional[float] = None) -> dict[str, Any]:
    root_end = root_end or time.time()
    root = _span(
        trace_id=state.trace_id,
        span_id=state.root_span_id,
        name="hermes.agent.turn",
        start=state.root_start,
        end=root_end,
        ok=not state.errored,
        status_message=state.error_message,
        attributes={
            "hermes.task_id": state.task_id,
            "hermes.turn_id": state.turn_id,
            "hermes.session_id": state.session_id,
            "hermes.platform": state.platform,
            "gen_ai.request.model": state.model,
            "gen_ai.system": state.provider,
            "hermes.api_mode": state.api_mode,
        },
    )
    return {
        "resourceSpans": [{
            "resource": {"attributes": _attrs(_resource_attributes(cfg, state))},
            "scopeSpans": [{
                "scope": {"name": _SCOPE_NAME, "version": _SCOPE_VERSION},
                "spans": [root, *state.spans],
            }],
        }]
    }


def _send_payload(cfg: LatitudeConfig, payload: dict[str, Any]) -> None:
    data = json.dumps(payload, ensure_ascii=False, default=str).encode("utf-8")
    req = urllib.request.Request(
        cfg.endpoint,
        data=data,
        headers={
            "Authorization": f"Bearer {cfg.api_key}",
            "X-Latitude-Project": cfg.project,
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            # Latitude docs say 202; current endpoint may return 200. Treat any
            # 2xx as accepted and log unexpected successful status only in debug.
            if not 200 <= int(response.status) < 300:
                logger.warning("Latitude ingest returned HTTP %s", response.status)
            else:
                _debug(f"exported trace to Latitude HTTP {response.status}")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", "replace")[:500]
        logger.warning("Latitude ingest failed HTTP %s: %s", exc.code, body)
    except Exception as exc:
        logger.warning("Latitude ingest failed: %s", exc)


def _export_and_clear(key: str, state: TraceState, *, root_end: Optional[float] = None) -> None:
    cfg = _get_config()
    if cfg is None:
        _TRACE_STATE.pop(key, None)
        return
    payload = _build_payload(cfg, state, root_end=root_end)
    _TRACE_STATE.pop(key, None)
    _send_payload(cfg, payload)


def on_pre_api_request(
    *,
    task_id: str = "",
    turn_id: str = "",
    api_request_id: str = "",
    session_id: str = "",
    platform: str = "",
    model: str = "",
    provider: str = "",
    api_mode: str = "",
    started_at: Optional[float] = None,
    message_count: Optional[int] = None,
    tool_count: Optional[int] = None,
    approx_input_tokens: Optional[int] = None,
    request_char_count: Optional[int] = None,
    **_: Any,
) -> None:
    if _get_config() is None:
        return
    with _STATE_LOCK:
        state = _state_for(
            task_id=task_id,
            turn_id=turn_id,
            session_id=session_id,
            platform=platform,
            model=model,
            provider=provider,
            api_mode=api_mode,
            started_at=started_at,
        )
        pending_attrs = {
            "hermes.api_request_id": api_request_id,
            "hermes.api_call_count": None,
            "gen_ai.system": provider or state.provider,
            "gen_ai.request.model": model or state.model,
            "hermes.api_mode": api_mode or state.api_mode,
            "hermes.message_count": message_count,
            "hermes.tool_count": tool_count,
            "gen_ai.usage.input_tokens_estimate": approx_input_tokens,
            "hermes.request_char_count": request_char_count,
        }
        state.spans.append({
            "_pending_llm": True,
            "span_id": _rand_hex(8),
            "api_request_id": api_request_id,
            "start": float(started_at) if started_at is not None else time.time(),
            "attributes": pending_attrs,
        })


def _complete_pending_llm(state: TraceState, api_request_id: str, attrs: Dict[str, Any], *, end: float, ok: bool, status_message: str = "") -> None:
    pending = None
    for span in reversed(state.spans):
        if span.get("_pending_llm") and span.get("api_request_id") == api_request_id:
            pending = span
            break
    if pending is None:
        pending = {
            "_pending_llm": True,
            "span_id": _rand_hex(8),
            "api_request_id": api_request_id,
            "start": end,
            "attributes": {},
        }
        state.spans.append(pending)
    merged_attrs = dict(pending.get("attributes") or {})
    merged_attrs.update(attrs)
    idx = state.spans.index(pending)
    state.spans[idx] = _span(
        trace_id=state.trace_id,
        span_id=pending["span_id"],
        parent_span_id=state.root_span_id,
        name="hermes.llm.call",
        start=pending.get("start", end),
        end=end,
        attributes=merged_attrs,
        ok=ok,
        status_message=status_message,
        kind=3,
    )


def on_post_api_request(
    *,
    task_id: str = "",
    turn_id: str = "",
    api_request_id: str = "",
    session_id: str = "",
    platform: str = "",
    model: str = "",
    provider: str = "",
    api_mode: str = "",
    api_call_count: Optional[int] = None,
    api_duration: Optional[float] = None,
    started_at: Optional[float] = None,
    ended_at: Optional[float] = None,
    finish_reason: Optional[str] = None,
    response_model: Optional[str] = None,
    usage: Optional[dict[str, Any]] = None,
    assistant_content_chars: Optional[int] = None,
    assistant_tool_call_count: Optional[int] = None,
    **_: Any,
) -> None:
    if _get_config() is None:
        return
    end = float(ended_at) if ended_at is not None else _duration_end(started_at, api_duration)
    key = _trace_key(task_id, turn_id, session_id)
    with _STATE_LOCK:
        state = _state_for(task_id=task_id, turn_id=turn_id, session_id=session_id, platform=platform, model=model, provider=provider, api_mode=api_mode, started_at=started_at)
        attrs = {
            "hermes.api_request_id": api_request_id,
            "hermes.api_call_count": api_call_count,
            "hermes.api_duration_ms": int(float(api_duration) * 1000) if api_duration is not None else None,
            "gen_ai.system": provider or state.provider,
            "gen_ai.request.model": model or state.model,
            "gen_ai.response.model": response_model,
            "hermes.api_mode": api_mode or state.api_mode,
            "hermes.finish_reason": finish_reason,
            "hermes.assistant_content_chars": assistant_content_chars,
            "hermes.assistant_tool_call_count": assistant_tool_call_count,
            "gen_ai.usage.input_tokens": _usage_attr(usage, "prompt_tokens"),
            "gen_ai.usage.output_tokens": _usage_attr(usage, "completion_tokens"),
            "gen_ai.usage.total_tokens": _usage_attr(usage, "total_tokens"),
        }
        _complete_pending_llm(state, api_request_id, attrs, end=end, ok=True)
        # A model response that requests tools is mid-turn. Keep the trace open
        # so tool spans and the follow-up LLM call appear in one agent-turn trace.
        if assistant_tool_call_count and int(assistant_tool_call_count) > 0:
            return
        _export_and_clear(key, state, root_end=end)


def on_api_request_error(
    *,
    task_id: str = "",
    turn_id: str = "",
    api_request_id: str = "",
    session_id: str = "",
    platform: str = "",
    model: str = "",
    provider: str = "",
    api_mode: str = "",
    api_call_count: Optional[int] = None,
    api_duration: Optional[float] = None,
    started_at: Optional[float] = None,
    ended_at: Optional[float] = None,
    error: Optional[dict[str, Any]] = None,
    retryable: Optional[bool] = None,
    reason: Optional[str] = None,
    **_: Any,
) -> None:
    if _get_config() is None:
        return
    end = float(ended_at) if ended_at is not None else _duration_end(started_at, api_duration)
    error = error if isinstance(error, dict) else {}
    error_type = str(error.get("type") or "APIError")
    error_message = str(error.get("message") or error_type)
    key = _trace_key(task_id, turn_id, session_id)
    with _STATE_LOCK:
        state = _state_for(task_id=task_id, turn_id=turn_id, session_id=session_id, platform=platform, model=model, provider=provider, api_mode=api_mode, started_at=started_at)
        state.errored = True
        state.error_message = error_message
        attrs = {
            "hermes.api_request_id": api_request_id,
            "hermes.api_call_count": api_call_count,
            "hermes.api_duration_ms": int(float(api_duration) * 1000) if api_duration is not None else None,
            "gen_ai.system": provider or state.provider,
            "gen_ai.request.model": model or state.model,
            "hermes.api_mode": api_mode or state.api_mode,
            "error.type": error_type,
            "error.message": error_message,
            "hermes.error.retryable": retryable,
            "hermes.error.reason": reason,
        }
        _complete_pending_llm(state, api_request_id, attrs, end=end, ok=False, status_message=error_message)
        _export_and_clear(key, state, root_end=end)


def on_post_tool_call(
    *,
    tool_name: str = "",
    args: Any = None,
    result: Any = None,
    task_id: str = "",
    session_id: str = "",
    tool_call_id: str = "",
    turn_id: str = "",
    api_request_id: str = "",
    duration_ms: Optional[int] = None,
    status: Optional[str] = None,
    error_type: Optional[str] = None,
    error_message: Optional[str] = None,
    **_: Any,
) -> None:
    if _get_config() is None:
        return
    end = time.time()
    duration_s = (float(duration_ms) / 1000.0) if duration_ms is not None else 0.0
    start = end - max(duration_s, 0.0)
    ok = (status or "ok") == "ok"
    key = _trace_key(task_id, turn_id, session_id)
    with _STATE_LOCK:
        state = _state_for(task_id=task_id, turn_id=turn_id, session_id=session_id)
        state.spans.append(_span(
            trace_id=state.trace_id,
            span_id=_rand_hex(8),
            parent_span_id=state.root_span_id,
            name="hermes.tool.call",
            start=start,
            end=end,
            ok=ok,
            status_message=error_message or "",
            attributes={
                "hermes.tool.name": tool_name,
                "hermes.tool_call_id": tool_call_id,
                "hermes.api_request_id": api_request_id,
                "hermes.tool.status": status or ("ok" if ok else "error"),
                "hermes.tool.duration_ms": duration_ms,
                "error.type": error_type,
                "error.message": error_message,
            },
        ))
        state.last_updated_at = time.time()


def register(ctx) -> None:
    ctx.register_hook("pre_api_request", on_pre_api_request)
    ctx.register_hook("post_api_request", on_post_api_request)
    ctx.register_hook("api_request_error", on_api_request_error)
    ctx.register_hook("post_tool_call", on_post_tool_call)
