#!/usr/bin/env python3
"""AgentPhone inbound SMS/iMessage webhook bridge for Hermes.

Inbound AgentPhone webhook -> local HTTP server -> Hermes one-shot -> POST /v1/messages.
Secrets are loaded from /root/.hermes/.env and /root/.hermes_agentphone_bridge/env,
with the bridge env taking precedence. Secret values are never logged.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import mimetypes
import os
import queue
import random
import re
import secrets
import shutil
import signal
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

BRIDGE_DIR = Path("/root/.hermes_agentphone_bridge")
HERMES_ENV = Path("/root/.hermes/.env")
BRIDGE_ENV = BRIDGE_DIR / "env"
STATE_PATH = BRIDGE_DIR / "state.json"
SEEN_PATH = BRIDGE_DIR / "seen_events.json"
WATERMARK_PATH = BRIDGE_DIR / "conversation_watermarks.json"
EVENTS_LOG = BRIDGE_DIR / "events.log"
CLOUDFLARED_LOG = BRIDGE_DIR / "cloudflared.log"
HOST = "127.0.0.1"
PORT = 8787
HOOK_PATH = "/hooks/agentphone"
MEDIA_PATH_PREFIX = "/media/"
MEDIA_CACHE_DIR = BRIDGE_DIR / "outbound_media"
LOCAL_URL = f"http://{HOST}:{PORT}"
API_BASE = "https://api.agentphone.ai"

# Hermes Telegram-style delivery markers and common image refs.
MEDIA_LINE_RE = re.compile(r"(?im)^\s*MEDIA:\s*(\S+)\s*$")
MEDIA_INLINE_RE = re.compile(r"(?i)\bMEDIA:\s*(\S+)")
MARKDOWN_IMG_RE = re.compile(r"!\[[^\]]*\]\((https?://[^)\s]+|/[^)\s]+)\)")
BARE_IMAGE_URL_RE = re.compile(
    r"(?i)(?<!\()\b(https?://\S+?\.(?:png|jpe?g|gif|webp|mp4|mov|pdf))(?:\?\S*)?"
)
MEDIA_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".mp4", ".mov", ".pdf"}

TOKEN_RE = re.compile(r"(?i)bearer\s+[A-Za-z0-9._~+/-]+")
SK_LIVE_RE = re.compile(r"sk_live_[A-Za-z0-9_\-]+")
WHSEC_RE = re.compile(r"whsec_[A-Za-z0-9._\-]+")
SECRET_ASSIGN_RE = re.compile(
    r"(?i)(secret|api[_-]?key|token|authorization)(['\"]?\s*[:=]\s*['\"]?)([^'\"\s,}]+)"
)
ANSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
TUNNEL_RE = re.compile(r"https://[-a-zA-Z0-9.]+\.trycloudflare\.com")

CONFIG: dict[str, str] = {}
WEBHOOK_SECRET = ""
PUBLIC_URL = ""
SEEN_LOCK = threading.Lock()
ORDER_LOCK = threading.Lock()
LOG_LOCK = threading.Lock()
JOB_LOCK = threading.Lock()
MEDIA_LOCK = threading.Lock()
MEDIA_REGISTRY: dict[str, dict[str, Any]] = {}
STOP = threading.Event()
CLOUDFLARED_PROC: subprocess.Popen[str] | None = None
RUNNING_JOBS: dict[str, dict[str, Any]] = {}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def redact_string(s: str) -> str:
    s = TOKEN_RE.sub("Bearer [REDACTED]", s)
    s = SK_LIVE_RE.sub("sk_live_[REDACTED]", s)
    s = WHSEC_RE.sub("whsec_[REDACTED]", s)
    s = SECRET_ASSIGN_RE.sub(lambda m: f"{m.group(1)}{m.group(2)}[REDACTED]", s)
    return s


def sanitize(obj: Any) -> Any:
    if isinstance(obj, dict):
        out: dict[str, Any] = {}
        for k, v in obj.items():
            if re.search(r"(?i)(secret|api[_-]?key|token|authorization)", str(k)):
                out[k] = "[REDACTED]"
            else:
                out[k] = sanitize(v)
        return out
    if isinstance(obj, list):
        return [sanitize(x) for x in obj]
    if isinstance(obj, str):
        return redact_string(obj)
    return obj


def log_event(event: str, **fields: Any) -> None:
    BRIDGE_DIR.mkdir(parents=True, exist_ok=True)
    record = {"ts": utc_now(), "event": event, **fields}
    safe = sanitize(record)
    line = json.dumps(safe, ensure_ascii=False, sort_keys=True)
    with LOG_LOCK:
        with EVENTS_LOG.open("a", encoding="utf-8") as f:
            f.write(line + "\n")


def parse_env_line(line: str) -> tuple[str, str] | None:
    line = line.strip()
    if not line or line.startswith("#") or "=" not in line:
        return None
    key, val = line.split("=", 1)
    key = key.strip()
    val = val.strip()
    if not key:
        return None
    if (len(val) >= 2) and ((val[0] == val[-1] == '"') or (val[0] == val[-1] == "'")):
        val = val[1:-1]
    return key, val


def load_env_file(path: Path, cfg: dict[str, str]) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        parsed = parse_env_line(line)
        if parsed:
            cfg[parsed[0]] = parsed[1]


def load_config() -> dict[str, str]:
    cfg: dict[str, str] = dict(os.environ)
    load_env_file(HERMES_ENV, cfg)
    load_env_file(BRIDGE_ENV, cfg)  # bridge-specific file wins
    cfg.setdefault("AGENTPHONE_BASE_URL", API_BASE)
    cfg.setdefault("AGENTPHONE_HERMES_TOOLSETS", "web,vision")
    cfg.setdefault("AGENTPHONE_FULL_HERMES_TOOLSETS", "all")
    cfg.setdefault("AGENTPHONE_HERMES_MAX_TURNS", "90")
    cfg.setdefault("AGENTPHONE_WEBHOOK_CONTEXT_LIMIT", "10")
    cfg.setdefault("AGENTPHONE_WEBHOOK_TIMEOUT", "30")
    cfg.setdefault("AGENTPHONE_HERMES_TIMEOUT_SECONDS", "900")
    return cfg


def require_config(cfg: dict[str, str], key: str) -> str:
    val = cfg.get(key, "").strip()
    if not val:
        raise RuntimeError(f"required config missing: {key}")
    return val


def normalize_phone(value: str | None) -> str:
    if not value:
        return ""
    value = value.strip()
    if value.startswith("grp_"):
        return value
    digits = re.sub(r"\D", "", value)
    if not digits:
        return value.strip()
    if len(digits) == 10:
        digits = "1" + digits
    return "+" + digits


def csv_phones(value: str | None) -> set[str]:
    if not value:
        return set()
    return {normalize_phone(x) for x in value.split(",") if normalize_phone(x)}


def atomic_write_json(path: Path, data: Any, mode: int = 0o600) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
    os.chmod(tmp, mode)
    tmp.replace(path)
    os.chmod(path, mode)


def read_json(path: Path, default: Any) -> Any:
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        log_event("json_read_failed", path=str(path), error=str(exc))
    return default


def load_state() -> dict[str, Any]:
    return read_json(STATE_PATH, {})


def save_state(state: dict[str, Any]) -> None:
    atomic_write_json(STATE_PATH, sanitize(state), 0o600)


def api_request(method: str, path: str, payload: dict[str, Any] | None = None, timeout: int = 30) -> Any:
    api_key = require_config(CONFIG, "AGENTPHONE_API_KEY")
    base = CONFIG.get("AGENTPHONE_BASE_URL", API_BASE).rstrip("/")
    if base.endswith("/v1") and path.startswith("/v1/"):
        url = base[:-3] + path
    elif not base.endswith("/v1") and not path.startswith("/v1/"):
        url = base + "/v1" + path
    else:
        url = base + path
    data = None
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json",
        "User-Agent": "curl/8.5.0",
    }
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method.upper())
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            if not body:
                return None
            try:
                return json.loads(body)
            except json.JSONDecodeError:
                return body
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")[:2000]
        raise RuntimeError(f"AgentPhone API {method} {path} failed: HTTP {exc.code}: {redact_string(body)}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"AgentPhone API {method} {path} failed: {exc.reason}") from exc


def verify_signature(raw_body: bytes, headers: Any, secret: str) -> tuple[bool, str]:
    signature = headers.get("X-Webhook-Signature", "")
    timestamp = headers.get("X-Webhook-Timestamp", "")
    if not secret:
        return False, "missing webhook secret"
    if not signature or not timestamp:
        return False, "missing signature headers"
    try:
        ts = int(timestamp)
    except ValueError:
        return False, "invalid timestamp"
    if abs(time.time() - ts) > 300:
        return False, "timestamp outside 5 minute window"
    signed = f"{timestamp}.".encode("utf-8") + raw_body
    expected = "sha256=" + hmac.new(secret.encode("utf-8"), signed, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, signature):
        return False, "signature mismatch"
    return True, "ok"


def extract_media_urls(data: dict[str, Any]) -> list[str]:
    """Return inbound media URLs from AgentPhone webhook payload variants.

    AgentPhone docs describe `data.mediaUrl` for inbound media. Some API surfaces
    and SDKs use snake_case or plural arrays, so accept all known spellings.
    """
    urls: list[str] = []
    for key in ("mediaUrl", "media_url", "mediaUrls", "media_urls"):
        value = data.get(key)
        if not value:
            continue
        if isinstance(value, str):
            candidates = [value]
        elif isinstance(value, list):
            candidates = [str(x) for x in value if x]
        else:
            candidates = [str(value)]
        for url in candidates:
            url = url.strip()
            if url and url not in urls:
                urls.append(url)
    return urls


def media_log_summary(media_urls: list[str]) -> dict[str, Any]:
    """Log media presence without storing signed/private URLs."""
    return {
        "media_count": len(media_urls),
        "media_sha256": [hashlib.sha256(u.encode("utf-8", errors="replace")).hexdigest()[:16] for u in media_urls],
    }


def safe_fields_for_log(fields: dict[str, Any]) -> dict[str, Any]:
    safe = dict(fields)
    media_urls = safe.pop("media_urls", []) or []
    safe.update(media_log_summary(media_urls if isinstance(media_urls, list) else []))
    return safe


def extract_event_fields(payload: dict[str, Any]) -> dict[str, Any]:
    data = payload.get("data") if isinstance(payload.get("data"), dict) else {}
    group = data.get("group") if isinstance(data.get("group"), dict) else {}
    event = str(payload.get("event") or "")
    channel = str(payload.get("channel") or "")
    conversation_id = str(data.get("conversationId") or data.get("conversation_id") or data.get("callId") or "")
    sender = normalize_phone(str(data.get("senderIdentifier") or data.get("from") or data.get("fromNumber") or ""))
    # Message time must win over envelope/delivery time. AgentPhone can retry or
    # deliver queued webhooks out of order; using the envelope timestamp makes an
    # older message delivered late look newer and wrongly interrupt active work.
    timestamp = str(data.get("receivedAt") or data.get("createdAt") or payload.get("timestamp") or "")
    text = str(data.get("message") or data.get("transcript") or data.get("reactionType") or data.get("messageBody") or "")
    media_urls = extract_media_urls(data)
    reply_to = str(group.get("groupId") or data.get("from") or sender)
    message_id = str(
        data.get("messageId")
        or data.get("message_id")
        or data.get("id")
        or payload.get("messageId")
        or payload.get("message_id")
        or ""
    )
    return {
        "event": event,
        "channel": channel,
        "conversation_id": conversation_id,
        "sender": sender,
        "timestamp": timestamp,
        "text": text,
        "media_urls": media_urls,
        "reply_to": reply_to,
        "direction": str(data.get("direction") or ""),
        "message_id": message_id,
    }


def event_dedupe_key(fields: dict[str, Any]) -> str:
    raw = "\x1f".join([
        fields.get("event", ""),
        fields.get("conversation_id", ""),
        fields.get("sender", ""),
        fields.get("timestamp", ""),
        fields.get("text", ""),
        "|".join(fields.get("media_urls") or []),
    ])
    return hashlib.sha256(raw.encode("utf-8", errors="replace")).hexdigest()


def mark_seen_once(key: str, fields: dict[str, Any]) -> bool:
    with SEEN_LOCK:
        seen = read_json(SEEN_PATH, {})
        if key in seen:
            return False
        seen[key] = {
            "first_seen_at": utc_now(),
            "event": fields.get("event"),
            "conversation_id": fields.get("conversation_id"),
            "sender": fields.get("sender"),
            "timestamp": fields.get("timestamp"),
            "text_sha256": hashlib.sha256(fields.get("text", "").encode()).hexdigest(),
            **media_log_summary(fields.get("media_urls") or []),
        }
        # Prevent unbounded growth while preserving recent retry protection.
        if len(seen) > 5000:
            items = sorted(seen.items(), key=lambda kv: kv[1].get("first_seen_at", ""))[-4000:]
            seen = dict(items)
        atomic_write_json(SEEN_PATH, seen, 0o600)
        return True


def parse_event_timestamp(value: str | None) -> float | None:
    """Parse an AgentPhone message timestamp into UTC epoch seconds."""
    raw = str(value or "").strip()
    if not raw:
        return None
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(raw)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.timestamp()


def mark_conversation_event_if_fresh(
    fields: dict[str, Any],
    path: Path = WATERMARK_PATH,
) -> tuple[bool, str | None]:
    """Atomically reject messages older than the last accepted message in a thread.

    AgentPhone may deliver queued webhook events out of order. Without this gate, an
    older late event interrupts a newer active Hermes job. Events with missing or
    malformed timestamps remain accepted so provider format changes do not blackhole
    inbound messages.
    """
    key = str(fields.get("conversation_id") or fields.get("reply_to") or fields.get("sender") or "")
    incoming_raw = str(fields.get("timestamp") or "")
    incoming_ts = parse_event_timestamp(incoming_raw)
    if not key or incoming_ts is None:
        return True, None

    with ORDER_LOCK:
        watermarks = read_json(path, {})
        if not isinstance(watermarks, dict):
            watermarks = {}
        previous = watermarks.get(key) if isinstance(watermarks.get(key), dict) else {}
        previous_raw = str(previous.get("timestamp") or "")
        previous_ts = parse_event_timestamp(previous_raw)
        if previous_ts is not None and incoming_ts < previous_ts:
            return False, previous_raw
        if previous_ts is None or incoming_ts > previous_ts:
            watermarks[key] = {
                "timestamp": incoming_raw,
                "message_id": str(fields.get("message_id") or ""),
                "updated_at": utc_now(),
            }
            atomic_write_json(path, watermarks, 0o600)
        return True, previous_raw or None


def strip_em_dashes(text: str) -> str:
    """Hard-enforce no em/en dash punctuation in outbound iMessage/SMS text.

    Models keep slipping on the soft prompt rule; this is the real gate.
    Em/horizontal/2-em/3-em dashes become ASCII " - ". Spaced en dashes become
    " - "; bare en dashes (ranges like 1–5) become "-".
    """
    if not text:
        return text
    # EM DASH, HORIZONTAL BAR, TWO-EM DASH, THREE-EM DASH
    text = re.sub(r"\s*[\u2014\u2015\u2e3a\u2e3b]\s*", " - ", text)
    # Spaced EN DASH used as a clause break
    text = re.sub(r"\s+\u2013\s+", " - ", text)
    # Remaining EN DASH (ranges, compounds)
    text = text.replace("\u2013", "-")
    # Collapse spaces introduced by replacement; keep newlines intact
    text = re.sub(r"[ \t]{2,}", " ", text)
    return text


def clean_hermes_output(output: str) -> str:
    output = ANSI_RE.sub("", output or "").strip()
    # Quiet mode may still include trailing session bookkeeping in some builds.
    lines = [ln.rstrip() for ln in output.splitlines()]
    drop_patterns = [
        r"^Session\s+(ID|saved|ended|cost|tokens)\b",
        r"^session_id\s*[:=]",
        r"^\[?Session\b.*\]?$",
    ]
    while lines and any(re.search(p, lines[-1], re.I) for p in drop_patterns):
        lines.pop()
    text = "\n".join(lines).strip()
    text = redact_string(text)
    text = strip_em_dashes(text)
    if not text:
        text = "I received your text, but I could not generate a reply."
    # SMS/iMessage-friendly upper bound; AgentPhone/API limits may be lower per channel.
    if len(text) > 3500:
        text = text[:3450].rstrip() + "\n\n[truncated]"
    return text



def extract_outbound_media(text: str) -> tuple[str, list[str]]:
    """Pull MEDIA:/path and image refs out of Hermes final text.

    Hermes Telegram delivery uses lines like MEDIA:/abs/path.png. AgentPhone needs
    public HTTPS media_urls instead, so the bridge strips markers and attaches media.
    """
    refs: list[str] = []
    body = text or ""

    def _add(ref: str) -> None:
        ref = (ref or "").strip().strip("\"'")
        if not ref:
            return
        if ref not in refs:
            refs.append(ref)

    def _media_line(m: re.Match[str]) -> str:
        _add(m.group(1))
        return ""

    def _media_inline(m: re.Match[str]) -> str:
        _add(m.group(1))
        return ""

    def _md_img(m: re.Match[str]) -> str:
        _add(m.group(1))
        return ""

    body = MEDIA_LINE_RE.sub(_media_line, body)
    body = MEDIA_INLINE_RE.sub(_media_inline, body)
    body = MARKDOWN_IMG_RE.sub(_md_img, body)

    # Only treat bare image URLs as attachments when they look like generated media
    # lines, not when buried in prose links. Prefer whole-line bare URLs.
    kept_lines: list[str] = []
    for ln in body.splitlines():
        stripped = ln.strip()
        m = re.fullmatch(r"(?i)(https?://\S+\.(?:png|jpe?g|gif|webp|mp4|mov|pdf)(?:\?\S*)?)", stripped)
        if m:
            _add(m.group(1))
            continue
        kept_lines.append(ln)
    body = "\n".join(kept_lines)
    body = re.sub(r"\n{3,}", "\n\n", body).strip()
    return body, refs


def purge_expired_media(now: float | None = None) -> None:
    now = time.time() if now is None else now
    with MEDIA_LOCK:
        expired = [tok for tok, meta in MEDIA_REGISTRY.items() if float(meta.get("expires", 0)) <= now]
        for tok in expired:
            meta = MEDIA_REGISTRY.pop(tok, {}) or {}
            p = Path(str(meta.get("path") or ""))
            try:
                if p.is_file() and (MEDIA_CACHE_DIR.resolve() in p.resolve().parents or p.parent.resolve() == MEDIA_CACHE_DIR.resolve()):
                    p.unlink(missing_ok=True)
            except Exception:
                pass
            try:
                (MEDIA_CACHE_DIR / f"{tok}.json").unlink(missing_ok=True)
            except Exception:
                pass


def publish_local_media(path: Path) -> str | None:
    """Copy a local file into the bridge media cache and return a public URL."""
    try:
        path = path.expanduser().resolve()
    except Exception:
        return None
    if not path.is_file():
        log_event("media_missing", path=str(path))
        return None
    if path.suffix.lower() not in MEDIA_EXTS:
        log_event("media_skipped_ext", path=str(path), ext=path.suffix)
        return None
    # Size cap default 12MB
    max_bytes = int_config("AGENTPHONE_MEDIA_MAX_BYTES", 12 * 1024 * 1024)
    try:
        size = path.stat().st_size
    except OSError as exc:
        log_event("media_stat_failed", path=str(path), error=str(exc)[:200])
        return None
    if size <= 0 or size > max_bytes:
        log_event("media_skipped_size", path=str(path), size=size, max_bytes=max_bytes)
        return None

    MEDIA_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    token = secrets.token_urlsafe(18)
    safe_name = re.sub(r"[^A-Za-z0-9._-]+", "_", path.name)[:80] or "file.bin"
    dest = MEDIA_CACHE_DIR / f"{token}_{safe_name}"
    try:
        shutil.copy2(path, dest)
    except Exception as exc:
        log_event("media_copy_failed", path=str(path), error=str(exc)[:300])
        return None

    ctype = mimetypes.guess_type(safe_name)[0] or "application/octet-stream"
    ttl = max(60, int_config("AGENTPHONE_MEDIA_TTL_SECONDS", 3600))
    meta = {
        "path": str(dest),
        "name": safe_name,
        "ctype": ctype,
        "expires": time.time() + ttl,
        "size": size,
    }
    meta_path = MEDIA_CACHE_DIR / f"{token}.json"
    try:
        meta_path.write_text(json.dumps(meta), encoding="utf-8")
        meta_path.chmod(0o600)
    except Exception as exc:
        log_event("media_meta_write_failed", error=str(exc)[:200])
        try:
            dest.unlink(missing_ok=True)
        except Exception:
            pass
        return None
    with MEDIA_LOCK:
        MEDIA_REGISTRY[token] = meta
    base = (PUBLIC_URL or LOCAL_URL).rstrip("/")
    url = f"{base}/media/{token}/{urllib.parse.quote(safe_name)}"
    log_event(
        "media_published",
        token=token[:8],
        name=safe_name,
        size=size,
        public_host=urllib.parse.urlparse(base).netloc,
    )
    return url


def resolve_media_refs(refs: list[str]) -> list[str]:
    """Convert local paths and remote URLs into AgentPhone-ready public URLs."""
    purge_expired_media()
    out: list[str] = []
    for ref in refs:
        ref = (ref or "").strip()
        if not ref:
            continue
        if ref.startswith("http://") or ref.startswith("https://"):
            if ref not in out:
                out.append(ref)
            continue
        # file:// support
        if ref.startswith("file://"):
            ref = ref[7:]
        p = Path(ref)
        if not p.is_absolute():
            # common agent cache roots
            candidates = [Path("/tmp") / ref, Path("/tmp/agentphone-media") / ref, MEDIA_CACHE_DIR / ref]
            p = next((c for c in candidates if c.is_file()), Path(ref))
        url = publish_local_media(p)
        if url and url not in out:
            out.append(url)
    return out


def prepare_outbound_body(body: str) -> tuple[str, list[str]]:
    """Clean Hermes output into text + public media URLs for AgentPhone."""
    text = body or ""
    text, refs = extract_outbound_media(text)
    media_urls = resolve_media_refs(refs)
    text = strip_em_dashes(text)
    if not text and not media_urls:
        text = "I received your text, but I could not generate a reply."
    # Keep AgentPhone-friendly length on the text portion only.
    if len(text) > 3500:
        text = text[:3450].rstrip() + "\n\n[truncated]"
    return text, media_urls


def int_config(name: str, default: int) -> int:
    try:
        return int(str(CONFIG.get(name, str(default))).strip())
    except ValueError:
        return default


def float_config(name: str, default: float) -> float:
    try:
        return float(str(CONFIG.get(name, str(default))).strip())
    except ValueError:
        return default


def split_reply_chunks(body: str) -> list[str]:
    """Split a final text into a few iMessage-style bubbles.

    Conservative by design: avoid splitting code/tables, cap bubble count, and
    split mostly at paragraph boundaries so detailed answers do not become
    unreadable SMS confetti.
    """
    text = (body or "").strip()
    if not text:
        return []
    if not bool_config("AGENTPHONE_REPLY_SPLIT_ENABLED", True):
        return [text]
    if "```" in text:
        return [text]
    if is_draft_like_reply(text):
        return [text]
    lines = text.splitlines()
    tableish_lines = sum(1 for ln in lines if ln.strip().startswith("|") and ln.strip().endswith("|"))
    if tableish_lines >= 2:
        return [text]

    min_chars = int_config("AGENTPHONE_REPLY_SPLIT_MIN_CHARS", 120)
    max_chunks = max(1, min(5, int_config("AGENTPHONE_REPLY_SPLIT_MAX_CHUNKS", 3)))
    target_chars = max(80, int_config("AGENTPHONE_REPLY_SPLIT_TARGET_CHARS", 160))
    hard_chars = max(target_chars, int_config("AGENTPHONE_REPLY_SPLIT_HARD_CHARS", 1200))
    if len(text) < min_chars or max_chunks <= 1:
        return [text]

    parts = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    if len(parts) <= 1:
        parts = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]
    if len(parts) <= 1 and len(text) >= min_chars:
        parts = [s.strip() for s in re.split(r"(?i),\s+(?=(?:but|and|so|because|unless|though)\b)", text) if s.strip()]
    if len(parts) <= 1:
        return [text]

    chunks: list[str] = []
    current = ""
    used_count = 0
    for part in parts:
        sep = "\n\n" if "\n" in current or "\n" in part else " "
        candidate = part if not current else current + sep + part
        if len(candidate) <= target_chars or not current:
            current = candidate
            used_count += 1
            continue
        chunks.append(current.strip())
        current = part
        used_count += 1
        if len(chunks) >= max_chunks - 1:
            break

    if len(chunks) >= max_chunks - 1 and used_count < len(parts):
        tail = parts[used_count:]
        current = "\n\n".join([current.strip(), *tail]).strip()
    if current.strip():
        chunks.append(current.strip())

    if len(chunks) > max_chunks:
        chunks = chunks[: max_chunks - 1] + ["\n\n".join(chunks[max_chunks - 1:]).strip()]
    if any(len(c) > hard_chars for c in chunks[:-1]):
        return [text]
    return [c for c in chunks if c]


def is_draft_like_reply(text: str) -> bool:
    """Keep drafted replies/emails copyable as one bubble.

    Chunking is good for conversational status. It is bad for artifacts the user
    will copy/paste, especially drafted emails or texts.
    """
    stripped = text.strip()
    lower = stripped.lower()
    if re.match(r"^(i['’]?d\s+(send|reply|write)|draft|reply|send)\s*:", lower):
        return True
    if re.search(r"(?im)^\s*(subject|to|cc|bcc)\s*:", stripped):
        return True
    has_greeting = re.search(r"(?im)^\s*(hey|hi|hello|dear)\s+[^\n,]{1,60},\s*$", stripped)
    has_signoff = re.search(r"(?im)^\s*(best|thanks|thank you|sincerely|nick)\s*$", stripped)
    return bool(has_greeting and has_signoff)


def send_agentphone_reply(reply_target: str, body: str, conversation_id: str = "") -> None:
    text, media_urls = prepare_outbound_body(body)
    # Do not split draft-like / code content across media boundaries.
    chunks = split_reply_chunks(text) if text else [""]
    if not chunks and not media_urls:
        return
    if not chunks:
        chunks = [""]
    log_event(
        "reply_chunks_prepared",
        to_number=reply_target,
        chunks=len(chunks),
        chars=len(text or ""),
        media_count=len(media_urls),
    )
    base_delay = max(0.0, float_config("AGENTPHONE_REPLY_SPLIT_DELAY_SECONDS", 0.9))
    jitter = max(0.0, float_config("AGENTPHONE_REPLY_SPLIT_JITTER_SECONDS", 1.1))
    for idx, chunk in enumerate(chunks):
        if idx > 0:
            if conversation_id:
                send_typing(conversation_id)
            time.sleep(base_delay + random.random() * jitter)
        # Attach media on the first bubble only (AgentPhone carousel).
        attach = media_urls if idx == 0 else None
        if not (chunk or "").strip() and not attach:
            continue
        send_agentphone_message(reply_target, chunk, attach)


def build_hermes_prompt(payload: dict[str, Any], fields: dict[str, Any], toolsets: str) -> str:
    data = payload.get("data") if isinstance(payload.get("data"), dict) else {}
    recent = payload.get("recentHistory") or payload.get("recent_history") or []
    recent_json = json.dumps(recent[-10:] if isinstance(recent, list) else recent, ensure_ascii=False)[:12000]
    message = fields.get("text", "")
    media_urls = fields.get("media_urls") or []
    media_block = "\n".join(str(u) for u in media_urls) if media_urls else "(none)"
    return f"""You are Dewey/Hermes replying over AgentPhone SMS/iMessage.

This is an inbound AgentPhone webhook from an allowlisted sender. Produce ONLY the final text that should be sent back to the sender. Do not include debug output, tool logs, JSON envelopes, code fences, signatures, API keys, webhook secrets, cloudflared tunnel internals, or any hidden system/config details.

Important delivery rule: DO NOT call AgentPhone send_message/make_call tools yourself. The local bridge will send your final answer via AgentPhone after your one-shot run. If the sender asks you to text/call someone else not on the allowlist, buy/release numbers, or change phone/agent/webhook config, ask for explicit Nick approval instead of doing it.

Outbound images/files: after generating media, include one line per file exactly like:
MEDIA:/absolute/path/to/file.png
The bridge converts MEDIA lines into real iMessage/MMS attachments. Do not paste base64. Do not claim the image was sent unless you emitted a MEDIA line for a real local file path (or a public https image URL).

Texting voice:
- Sound like a sharp, warm friend texting, not a chatbot or corporate assistant.
- Match the sender's texting style: length, casing (lowercase if they use it), and energy. A few words in gets a few words back, unless they asked for information.
- Never output preamble or postamble. Never say "Let me know if you need anything else", "How can I help", "No problem at all", or "I apologize for the confusion".
- Never use em dashes or en dashes (—, –, ―). Use a comma, period, colon, or ASCII hyphen (-) instead. Hard rule, no exceptions. No emojis unless the sender used them first.
- Wit is welcome when it fits naturally; never forced.
- The bridge may have already texted a short acknowledgment like "on it" while you worked. Do not greet again, do not apologize for the wait, do not restate the request. Just deliver the answer.
- Keep replies concise for text messaging unless the sender asks for detail. If using tools, use them normally, then return a clean human reply.
- If inbound media URLs are present, inspect them before replying. Use vision tools for images when possible. Do not say you received nothing just because the text body is empty.

Toolset tier selected by bridge: {toolsets}
Sender: {fields.get('sender')}
Channel: {fields.get('channel')}
Conversation ID: {fields.get('conversation_id')}
Timestamp: {fields.get('timestamp')}
Inbound text:
{message}

Inbound media URLs:
{media_block}

Recent AgentPhone history, if supplied by webhook:
{recent_json}
"""


CLASSIC_REACTIONS = {"love", "like", "dislike", "laugh", "emphasize", "question"}
REACTION_TEXT_MAP = {
    "nice": "like",
    "cool": "like",
    "great": "like",
    "awesome": "like",
    "sweet": "like",
    "perfect": "like",
    "sounds good": "like",
    "sgtm": "like",
    "ok": "like",
    "okay": "like",
    "k": "like",
    "kk": "like",
    "got it": "like",
    "yep": "like",
    "yes": "like",
    "yeah": "like",
    "thanks": "love",
    "thank you": "love",
    "ty": "love",
    "thx": "love",
    "appreciate it": "love",
    "lol": "laugh",
    "lmao": "laugh",
    "haha": "laugh",
    "hahaha": "laugh",
}


def compact_text(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").lower()).strip(" .!?…")


def parse_agentphone_time(value: str) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def reaction_for_message(fields: dict[str, str]) -> tuple[str | None, str]:
    if not bool_config("AGENTPHONE_REACTIONS_ENABLED", False):
        return None, "disabled"
    if fields.get("channel") != "imessage":
        return None, "not-imessage"
    mode = str(CONFIG.get("AGENTPHONE_REACTION_MODE", "smart")).strip().lower()
    if mode in ("0", "false", "no", "off", "never"):
        return None, "disabled"
    forced = CONFIG.get("AGENTPHONE_REACTION_ALWAYS")
    if mode in ("1", "true", "yes", "on", "always"):
        reaction = (forced or "like").strip()
        return reaction, "always"
    text = compact_text(fields.get("text") or "")
    reaction = REACTION_TEXT_MAP.get(text)
    if reaction:
        return reaction, "casual-map"
    # Only auto-react to trivial closers. Task-like messages should get typing/ack/final answer.
    return None, "not-reaction-only"


def find_inbound_message_id(fields: dict[str, str]) -> str:
    if fields.get("message_id"):
        return fields["message_id"]
    conversation_id = fields.get("conversation_id") or ""
    if not conversation_id:
        return ""
    try:
        resp = api_request("GET", f"/v1/conversations/{conversation_id}/messages?limit=20", None, timeout=10)
    except Exception as exc:
        log_event("reaction_message_lookup_failed", conversation_id=conversation_id, error=str(exc)[:300])
        return ""
    messages = resp.get("data") if isinstance(resp, dict) else resp
    if not isinstance(messages, list):
        return ""
    want_body = (fields.get("text") or "").strip()
    want_sender = normalize_phone(fields.get("sender") or "")
    want_time = parse_agentphone_time(fields.get("timestamp") or "")
    fallback = ""
    for msg in messages:
        if not isinstance(msg, dict):
            continue
        if str(msg.get("direction") or "").lower() != "inbound":
            continue
        msg_sender = normalize_phone(str(msg.get("senderIdentifier") or msg.get("fromNumber") or ""))
        if want_sender and msg_sender and msg_sender != want_sender:
            continue
        msg_body = str(msg.get("body") or msg.get("message") or "").strip()
        if want_body and msg_body != want_body:
            continue
        msg_id = str(msg.get("id") or "")
        if not msg_id:
            continue
        if not fallback:
            fallback = msg_id
        msg_time = parse_agentphone_time(str(msg.get("receivedAt") or msg.get("createdAt") or ""))
        if want_time and msg_time and abs((msg_time - want_time).total_seconds()) <= 60:
            return msg_id
    return fallback


def send_reaction(message_id: str, reaction: str) -> bool:
    if not message_id:
        return False
    reaction = reaction.strip()
    if not reaction:
        return False
    try:
        resp = api_request("POST", f"/v1/messages/{message_id}/reactions", {"reaction": reaction}, timeout=8)
        log_event("reaction_sent", message_id=message_id, reaction=reaction, response=resp)
        return True
    except Exception as exc:
        # SMS, old iMessage lines, custom emoji, or stale messages can fail; do not invoke Hermes for casual closers just because tapback failed.
        log_event("reaction_failed", message_id=message_id, reaction=reaction, error=str(exc)[:500])
        return False


def handle_reaction_only(fields: dict[str, str]) -> bool:
    reaction, reason = reaction_for_message(fields)
    if not reaction:
        log_event("reaction_skipped", reason=reason)
        return False
    message_id = find_inbound_message_id(fields)
    if not message_id:
        log_event("reaction_skipped", reason="no-message-id", intended_reaction=reaction)
        return True
    sent = send_reaction(message_id, reaction)
    if not sent:
        return True
    log_event("reaction_only_handled", reason=reason, reaction=reaction, message_id=message_id)
    return True


def send_typing(conversation_id: str) -> None:
    if not conversation_id:
        return
    try:
        api_request("POST", f"/v1/conversations/{conversation_id}/typing", None, timeout=8)
        log_event("typing_sent", conversation_id=conversation_id)
    except Exception as exc:
        # SMS and stale iMessage conversations can return 400; non-fatal.
        log_event("typing_skipped", conversation_id=conversation_id, error=str(exc)[:300])


ACK_TEMPLATES = [
    "on it",
    "checking now",
    "looking into it",
    "yep, give me a sec",
    "digging in",
    "got it, one sec",
    "let me check",
    "on it, give me a bit",
    "looking now",
    "yep, on it",
    "checking, one sec",
    "let me look",
    "gotcha, checking now",
    "sure, looking into it",
    "yep, digging in",
    "let me dig in",
    "checking that now",
    "got it, looking now",
    "one sec, checking",
    "on it, back in a sec",
]
_LAST_ACK_LINE: list[str] = [""]

PROGRESS_TEMPLATES = [
    "still working on it",
    "still checking, taking a bit",
    "verifying before i answer",
    "still on it, taking longer than expected",
    "still digging, almost there",
    "taking a bit longer, still working",
    "still looking into it",
    "still going, give me another sec",
    "working on it, this one's a bit involved",
    "still at it, will have an answer soon",
]
_LAST_PROGRESS_LINE: list[str] = [""]

INTERRUPT_LINES = [
    "got it, switching",
    "yep, switching gears",
    "on it, dropping the other thing",
    "gotcha, pivoting now",
    "sure, switching to that",
    "yep, on the new one",
    "got it, let me switch",
    "on it, setting that aside",
]
_LAST_INTERRUPT_LINE: list[str] = [""]


def pick_interrupt_ack() -> str:
    available = [l for l in INTERRUPT_LINES if l != _LAST_INTERRUPT_LINE[0]] or INTERRUPT_LINES
    line = random.choice(available)
    _LAST_INTERRUPT_LINE[0] = line
    return line

TASK_ACK_PATTERNS = [
    r"\b(check|look\s*(at|into|up)?|search|find|pull|scan|read|summarize|research|investigate)\b",
    r"\b(analy[sz]e|compare|review|debug|fix|build|write|draft|create|make|plan)\b",
    r"\b(email|inbox|calendar|meeting|doc|sheet|github|issue|pr|repo|logs?|error|trace|website|url)\b",
    r"\b(remind|schedule|book|call|text|send|reply|forward)\b",
    r"https?://|www\.|/root/|~/|\.com\b|\.ai\b|\.md\b|\.py\b",
]
CASUAL_ACK_SKIP = {
    "hi", "hey", "yo", "sup", "you up", "u up", "nice", "ok", "okay", "k", "kk",
    "yes", "no", "yep", "nah", "thanks", "thank you", "lol", "lmao", "haha",
    "what's your name", "whats your name",
}


def extract_keyword(text: str) -> str:
    """Pull a short keyword/phrase from the user's message for contextual acks.

    Tries to find the most meaningful noun-ish thing in the text:
    - URLs -> 'that link'
    - Email addresses -> 'that email'
    - File paths -> basename
    - Action verb + object -> the object (e.g. "check the github repo" -> "github repo")
    - Otherwise -> first content word

    Falls back to 'that' if nothing better is found.

    GUARD: if the extracted phrase contains second-person pronouns (you, youre,
    your, u, ur), it means the user is talking ABOUT the agent, not giving a
    task keyword. In that case return 'that' so the ack stays generic.
    """
    t = text.strip()
    if not t:
        return "that"
    compact = re.sub(r"\s+", " ", t.lower()).strip(" .!?…")
    # URL
    if re.search(r"https?://|www\.", compact):
        return "that link"
    # Email
    if re.search(r"\b[\w.+-]+@[\w.-]+\.\w+\b", compact):
        return "that email"
    # File paths
    m = re.search(r"(?:/root/|~/)[^\s]+", t)
    if m:
        parts = m.group(0).rstrip(".,;!?")
        basename = parts.rstrip("/").split("/")[-1]
        return basename if basename else "that"

    # Second-person guard: if the user is talking about/to the agent
    # ("youre on agentphone", "you should use deepseek", etc.), the text
    # after a verb is NOT a task keyword. Return a safe fallback.
    second_person_re = re.compile(r"\b(?:you|youre|your|yours|ur|u\s+are|u\s+should|youll|youve)\b")
    
    # Only match clear action verbs that take a noun object as a task.
    # Exclude "have" (it's a yes/no question, not a task) and other
    # conversational verbs that don't indicate work.
    m = re.search(r"\b(?:check|look\s+at|look\s+into|find|search|pull\s+up|read|review|fix|debug|build|write|draft|send|reply\s+to|forward|remind|call|text|book|schedule)\s+(.+)", compact)
    if m:
        phrase = m.group(1).strip()
        # If the phrase contains second-person pronouns, it's not a task keyword
        if second_person_re.search(phrase):
            return "that"
        # Strip leading pronouns, articles, and filler
        phrase = re.sub(r"^(?:me\s+to\s+|us\s+to\s+|him\s+to\s+|her\s+to\s+|them\s+to\s+)?", "", phrase)
        phrase = re.sub(r"^(?:the\s+|a\s+|an\s+|some\s+)?", "", phrase).strip()
        # Trim to first clause boundary
        phrase = re.split(r"[,;.]|\band\b|\bso\b|\bbut\b|\bbecause\b|\bfor\b|\bfrom\b|\babout\b|\bshould\b|\bso\b|\bthat\b", phrase)[0].strip()
        words = phrase.split()
        # Keep at most 3 words for natural reading
        if len(words) > 3:
            words = words[:3]
        short = " ".join(words)
        if 3 <= len(short) <= 30:
            return short
        if len(words) >= 2:
            short = " ".join(words[:2])
            if len(short) <= 30:
                return short
    # Fall back to the most content-heavy word
    stop = {"the","a","an","is","are","was","were","can","you","i","to","for","of","in","on","at","my","your","it","this","that","with","and","or","but","so","do","did","does","how","what","why","when","where","who","is","im","ive","me","up","tomorrow","today","now","just","like","want","need","going","u","ur","go","should","dont","wont","cant","be","its","sure","well","thanks","thank","ok","okay","nice","good","great","cool","sweet","awesome","right","yes","no","yep","nope","yeah","nah","hey","hi","hello","oh","wow","hmm","lol","lmao","haha","interesting","nice","have","has","had","also","already","from","about","some","know","think","see","say","get","got","put","let","give","make","take","came","come","tell","ask","really","still","even","much","very","more","most"}
    words = re.findall(r"[a-z]+", compact)
    content = [w for w in words if w not in stop and len(w) >= 3]
    if content:
        # Guard against second-person words in fallback too
        if second_person_re.search(content[0]):
            return "that"
        return content[0]
    return "that"


def pick_ack(lines: list[str], last: list[str]) -> str:
    """Pick a random ack line, avoiding repeating the last one."""
    available = [l for l in lines if l != last[0]] or lines
    return random.choice(available)


def bool_config(name: str, default: bool = True) -> bool:
    raw = str(CONFIG.get(name, "1" if default else "0")).strip().lower()
    return raw not in ("0", "false", "no", "off", "")


def job_key_for_fields(fields: dict[str, Any]) -> str:
    return str(fields.get("conversation_id") or fields.get("reply_to") or fields.get("sender") or "")


def start_conversation_job(fields: dict[str, Any], reply_target: str) -> dict[str, Any]:
    """Register a per-conversation Hermes run and cancel any stale run."""
    key = job_key_for_fields(fields)
    job = {
        "key": key,
        "id": hashlib.sha256(f"{key}\x1f{time.time()}\x1f{random.random()}".encode()).hexdigest()[:16],
        "cancelled": threading.Event(),
        "proc": None,
        "started_at": time.time(),
        "message_id": fields.get("message_id") or "",
        "interrupted_previous": False,
    }
    if not key or not bool_config("AGENTPHONE_INTERRUPTION_ENABLED", True):
        return job
    old: dict[str, Any] | None = None
    with JOB_LOCK:
        old = RUNNING_JOBS.get(key)
        if old:
            old["cancelled"].set()
            proc = old.get("proc")
            if proc is not None and getattr(proc, "poll", lambda: None)() is None:
                try:
                    proc.terminate()
                except Exception as exc:
                    log_event("job_interrupt_terminate_failed", job_id=old.get("id"), conversation_id=key, error=str(exc)[:300])
        RUNNING_JOBS[key] = job
    if old:
        job["interrupted_previous"] = True
        log_event("job_interrupted", conversation_id=key, old_job_id=old.get("id"), new_job_id=job.get("id"))
        if reply_target and bool_config("AGENTPHONE_INTERRUPTION_ACK_ENABLED", True):
            send_agentphone_message(reply_target, pick_interrupt_ack())
    return job


def set_job_proc(job: dict[str, Any], proc: subprocess.Popen[str]) -> None:
    job["proc"] = proc


def finish_conversation_job(job: dict[str, Any]) -> None:
    key = job.get("key") or ""
    if not key:
        return
    with JOB_LOCK:
        if RUNNING_JOBS.get(key) is job:
            RUNNING_JOBS.pop(key, None)


def is_job_cancelled(job: dict[str, Any]) -> bool:
    ev = job.get("cancelled")
    return bool(ev and ev.is_set())


def should_send_ack(fields: dict[str, Any]) -> tuple[bool, str]:
    """Return whether a Poke-style working ack should be sent for this inbound text."""
    if fields.get("_skip_ack"):
        return False, "already-interrupted-ack"
    mode = str(CONFIG.get("AGENTPHONE_ACK_MODE", "smart")).strip().lower()
    if mode in ("0", "false", "no", "off", "never"):
        return False, "disabled"
    if mode in ("1", "true", "yes", "on", "always"):
        return True, "always"

    if fields.get("media_urls"):
        return True, "media"
    text = (fields.get("text") or "").strip()
    compact = re.sub(r"\s+", " ", text.lower()).strip(" .!?…")
    if not compact:
        return False, "empty"
    if compact in CASUAL_ACK_SKIP:
        return False, "casual"
    if len(compact) >= int(CONFIG.get("AGENTPHONE_ACK_MIN_CHARS", "80")):
        return True, "length"
    if any(re.search(pattern, compact, re.I) for pattern in TASK_ACK_PATTERNS):
        return True, "task-pattern"
    # Questions that are not just small talk often imply work, but short fact/persona
    # questions should just get the answer rather than an extra "looking" text.
    if "?" in text and len(compact) >= 45:
        return True, "question"
    return False, "not-taskish"


def ack_and_typing_keepalive(done: threading.Event, reply_target: str, fields: dict[str, Any]) -> None:
    """Contextual ack + typing keepalive while Hermes is working.

    Sends a short ack that references what the user actually asked about,
    then typing indicators until done. For long runs (>45s), sends one
    contextual progress message. This keeps acks feeling connected to
    the conversation rather than generic filler.
    """
    try:
        refresh = max(15.0, float(CONFIG.get("AGENTPHONE_TYPING_REFRESH_SECONDS", "25")))
        ack_enabled = bool_config("AGENTPHONE_ACK_ENABLED", True)
        ack_wanted, reason = should_send_ack(fields)
        user_text = (fields.get("text") or "").strip()

        # Interruption context: send brief contextual ack
        if ack_enabled and ack_wanted and reply_target and fields.get("_skip_ack"):
            ack_delay = max(0.0, float(CONFIG.get("AGENTPHONE_ACK_DELAY_SECONDS", "1.25")))
            if not done.wait(ack_delay):
                line = pick_interrupt_ack()
                send_agentphone_message(reply_target, line)
                _LAST_ACK_LINE[0] = line
                log_event("ack_sent", to_number=reply_target, ack=line, reason="interrupt")
        elif ack_enabled and ack_wanted and reply_target:
            # Normal contextual ack referencing the user's message
            ack_delay = max(0.0, float(CONFIG.get("AGENTPHONE_ACK_DELAY_SECONDS", "1.25")))
            if not done.wait(ack_delay):
                line = pick_ack(ACK_TEMPLATES, _LAST_ACK_LINE)
                _LAST_ACK_LINE[0] = line
                send_agentphone_message(reply_target, line)
                log_event("ack_sent", to_number=reply_target, ack=line, reason=reason)
        else:
            log_event("ack_skipped", reason=reason if ack_enabled else "disabled")

        # Always send typing indicators while working.
        send_typing(fields.get("conversation_id") or "")
        started = time.time()

        # Contextual progress: one message after threshold, referencing the task
        progress_enabled = bool_config("AGENTPHONE_PROGRESS_ENABLED", True) and ack_wanted and reply_target
        progress_after = max(20.0, float(CONFIG.get("AGENTPHONE_PROGRESS_AFTER_SECONDS", "45")))
        progress_sent = False
        while not done.wait(refresh):
            send_typing(fields.get("conversation_id") or "")
            if progress_enabled and not progress_sent and time.time() - started >= progress_after:
                line = pick_ack(PROGRESS_TEMPLATES, _LAST_PROGRESS_LINE)
                _LAST_PROGRESS_LINE[0] = line
                send_agentphone_message(reply_target, line)
                log_event("progress_sent", to_number=reply_target, progress=line, elapsed_seconds=round(time.time() - started, 1))
                progress_sent = True
    except Exception as exc:
        log_event("ack_keepalive_failed", error=str(exc)[:300])


def run_hermes_and_reply(payload: dict[str, Any], fields: dict[str, Any], toolsets: str, job: dict[str, Any] | None = None) -> None:
    reply_target = fields.get("reply_to") or fields.get("sender")
    if job is None:
        job = start_conversation_job(fields, reply_target or "")
    send_typing(fields.get("conversation_id") or "")
    prompt = build_hermes_prompt(payload, fields, toolsets)
    max_turns = CONFIG.get("AGENTPHONE_HERMES_MAX_TURNS", "90")
    timeout = int(CONFIG.get("AGENTPHONE_HERMES_TIMEOUT_SECONDS", "900"))
    hermes_bin = CONFIG.get("HERMES_BIN", "/root/.local/bin/hermes")
    if not Path(hermes_bin).exists():
        hermes_bin = "hermes"
    cmd = [
        hermes_bin,
        "chat",
        "-Q",
        "--source",
        "agentphone-bridge",
        "--max-turns",
        str(max_turns),
    ]
    # Per-bridge model/provider override (passed as CLI flags, not env vars,
    # because HERMES_INFERENCE_MODEL only works for -z/--oneshot and --tui)
    bridge_model = CONFIG.get("AGENTPHONE_HERMES_MODEL", "")
    if bridge_model:
        cmd.extend(["-m", bridge_model])
    bridge_provider = CONFIG.get("AGENTPHONE_HERMES_PROVIDER", "")
    if bridge_provider:
        cmd.extend(["--provider", bridge_provider])
    cmd.extend(["-q", prompt])
    if toolsets:
        cmd.extend(["-t", toolsets])
    env = os.environ.copy()
    env.update(CONFIG)
    env.setdefault("HERMES_YOLO_MODE", "1")
    log_event("hermes_start", sender=fields.get("sender"), conversation_id=fields.get("conversation_id"), toolsets=toolsets, job_id=job.get("id"), model=bridge_model or "default", provider=bridge_provider or "default")
    done = threading.Event()
    ack_fields = dict(fields)
    if job.get("interrupted_previous"):
        ack_fields["_skip_ack"] = True
    threading.Thread(
        target=ack_and_typing_keepalive, args=(done, reply_target or "", ack_fields),
        name="ack-keepalive", daemon=True,
    ).start()
    proc: subprocess.Popen[str] | None = None
    try:
        proc = subprocess.Popen(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
        set_job_proc(job, proc)
        deadline = time.time() + timeout
        while proc.poll() is None:
            if is_job_cancelled(job):
                log_event("hermes_cancelled", sender=fields.get("sender"), conversation_id=fields.get("conversation_id"), job_id=job.get("id"))
                proc.terminate()
                try:
                    proc.wait(timeout=8)
                except subprocess.TimeoutExpired:
                    proc.kill()
                return
            if time.time() > deadline:
                log_event("hermes_timeout", sender=fields.get("sender"), conversation_id=fields.get("conversation_id"), timeout=timeout, job_id=job.get("id"))
                proc.kill()
                body = "I received your text, but the agent run timed out before I could finish."
                send_agentphone_reply(reply_target, body, fields.get("conversation_id") or "")
                return
            time.sleep(0.25)
        stdout, stderr = proc.communicate(timeout=5)
    finally:
        done.set()
        finish_conversation_job(job)
    if is_job_cancelled(job):
        log_event("reply_suppressed_cancelled", sender=fields.get("sender"), conversation_id=fields.get("conversation_id"), job_id=job.get("id"))
        return
    stdout = stdout or ""
    stderr = stderr or ""
    returncode = proc.returncode if proc is not None else 1
    if returncode != 0:
        # Hermes can finish generation and print a valid answer, then abort during
        # CLI/memory cleanup (observed as SIGABRT / returncode -6). Preserve that
        # answer instead of replacing it with a misleading canned failure.
        raw_stdout = ANSI_RE.sub("", stdout).strip()
        if raw_stdout and not raw_stdout.startswith(("Traceback (most recent call last):", "Fatal Python error:")):
            body = clean_hermes_output(stdout)
            log_event(
                "hermes_failed_but_stdout_recovered",
                returncode=returncode,
                stderr=stderr[-4000:],
                chars=len(body),
                sender=fields.get("sender"),
                conversation_id=fields.get("conversation_id"),
                job_id=job.get("id"),
            )
        else:
            log_event("hermes_failed", returncode=returncode, stderr=stderr[-4000:], job_id=job.get("id"))
            body = "I received your text, but Hermes hit an internal error while generating a reply."
    else:
        body = clean_hermes_output(stdout)
        log_event("hermes_done", sender=fields.get("sender"), conversation_id=fields.get("conversation_id"), chars=len(body), job_id=job.get("id"))
    send_agentphone_reply(reply_target, body, fields.get("conversation_id") or "")


def send_agentphone_message(to_number: str, body: str, media_urls: list[str] | None = None) -> None:
    # Final outbound gate: strip em/en dashes from every message (final reply, ack, progress).
    body = strip_em_dashes(body or "")
    media_urls = [u for u in (media_urls or []) if u]
    payload: dict[str, Any] = {
        "to_number": to_number,
        "body": body,
    }
    if media_urls:
        # AgentPhone rejects media_url and media_urls together (HTTP 400).
        if len(media_urls) == 1:
            payload["media_url"] = media_urls[0]
        else:
            payload["media_urls"] = media_urls
    if CONFIG.get("AGENTPHONE_NUMBER_ID"):
        payload["number_id"] = CONFIG["AGENTPHONE_NUMBER_ID"]
    if CONFIG.get("AGENTPHONE_AGENT_ID"):
        payload["agent_id"] = CONFIG["AGENTPHONE_AGENT_ID"]
    try:
        resp = api_request("POST", "/v1/messages", payload, timeout=45)
        log_event(
            "reply_sent",
            to_number=to_number,
            media_count=len(media_urls),
            response=resp,
        )
    except Exception as exc:
        log_event(
            "reply_send_failed",
            to_number=to_number,
            media_count=len(media_urls),
            error=str(exc),
        )


class BridgeHTTPServer(ThreadingHTTPServer):
    allow_reuse_address = True


class Handler(BaseHTTPRequestHandler):
    server_version = "AgentPhoneHermesBridge/1.0"

    def log_message(self, fmt: str, *args: Any) -> None:
        log_event("http_access", client=self.client_address[0], message=fmt % args)

    def send_json(self, status: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        path_only = self.path.split("?", 1)[0]
        if path_only == "/health":
            self.send_json(200, {"ok": True, "public_url": PUBLIC_URL or None})
            return
        if path_only == HOOK_PATH:
            self.send_json(405, {"ok": False, "error": "POST required"})
            return
        if path_only.startswith(MEDIA_PATH_PREFIX):
            self.serve_media(path_only)
            return
        self.send_json(404, {"ok": False, "error": "not found"})

    def serve_media(self, path_only: str) -> None:
        """Serve short-lived outbound media for AgentPhone to fetch."""
        purge_expired_media()
        # /media/{token}/{filename}
        parts = [p for p in path_only.split("/") if p]
        if len(parts) < 2 or parts[0] != "media":
            self.send_json(404, {"ok": False, "error": "not found"})
            return
        token = parts[1]
        # tokens are url-safe; reject path tricks
        if not re.fullmatch(r"[A-Za-z0-9_\-]{8,64}", token or ""):
            self.send_json(404, {"ok": False, "error": "expired or unknown media"})
            return
        with MEDIA_LOCK:
            meta = dict(MEDIA_REGISTRY.get(token) or {})
        if not meta:
            meta_path = MEDIA_CACHE_DIR / f"{token}.json"
            try:
                if meta_path.is_file():
                    meta = json.loads(meta_path.read_text(encoding="utf-8"))
                    with MEDIA_LOCK:
                        MEDIA_REGISTRY[token] = dict(meta)
            except Exception:
                meta = {}
        if not meta:
            self.send_json(404, {"ok": False, "error": "expired or unknown media"})
            return
        if float(meta.get("expires", 0)) <= time.time():
            purge_expired_media()
            self.send_json(404, {"ok": False, "error": "expired media"})
            return
        file_path = Path(str(meta.get("path") or ""))
        try:
            resolved = file_path.resolve()
            if MEDIA_CACHE_DIR.resolve() not in resolved.parents and resolved.parent != MEDIA_CACHE_DIR.resolve():
                self.send_json(403, {"ok": False, "error": "forbidden"})
                return
            data = resolved.read_bytes()
        except Exception as exc:
            log_event("media_serve_failed", token=token[:8], error=str(exc)[:200])
            self.send_json(404, {"ok": False, "error": "missing media"})
            return
        ctype = str(meta.get("ctype") or "application/octet-stream")
        name = str(meta.get("name") or resolved.name)
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Content-Disposition", f'inline; filename="{name}"')
        self.send_header("Cache-Control", "private, max-age=300")
        self.end_headers()
        self.wfile.write(data)
        log_event("media_served", token=token[:8], name=name, bytes=len(data))

    def do_POST(self) -> None:  # noqa: N802
        if self.path.split("?", 1)[0] != HOOK_PATH:
            self.send_json(404, {"ok": False, "error": "not found"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self.send_json(400, {"ok": False, "error": "bad content-length"})
            return
        raw_body = self.rfile.read(length)
        ok, reason = verify_signature(raw_body, self.headers, WEBHOOK_SECRET)
        if not ok:
            log_event("signature_rejected", reason=reason, webhook_id=self.headers.get("X-Webhook-ID"), webhook_event=self.headers.get("X-Webhook-Event"))
            self.send_json(401, {"ok": False, "error": "unauthorized"})
            return
        try:
            payload = json.loads(raw_body.decode("utf-8"))
        except json.JSONDecodeError:
            log_event("bad_json")
            self.send_json(400, {"ok": False, "error": "bad json"})
            return
        fields = extract_event_fields(payload)
        log_event("webhook_received", webhook_id=self.headers.get("X-Webhook-ID"), fields=safe_fields_for_log(fields))

        if fields["event"] != "agent.message" or fields["channel"] not in {"sms", "mms", "imessage"}:
            log_event("webhook_ignored_event", fields=safe_fields_for_log(fields))
            self.send_json(200, {"ok": True, "ignored": "unsupported event/channel"})
            return
        if fields.get("direction") and fields["direction"].lower() != "inbound":
            log_event("webhook_ignored_direction", fields=safe_fields_for_log(fields))
            self.send_json(200, {"ok": True, "ignored": "not inbound"})
            return
        allowed = csv_phones(CONFIG.get("AGENTPHONE_ALLOWED_SENDERS"))
        full_access = csv_phones(CONFIG.get("AGENTPHONE_FULL_ACCESS_NUMBERS"))
        sender = fields["sender"]
        if allowed and sender not in allowed:
            log_event("webhook_ignored_sender", sender=sender, allowed=sorted(allowed), conversation_id=fields.get("conversation_id"))
            self.send_json(200, {"ok": True, "ignored": "sender not allowlisted"})
            return
        key = event_dedupe_key(fields)
        if not mark_seen_once(key, fields):
            log_event("webhook_duplicate", sender=sender, conversation_id=fields.get("conversation_id"), dedupe_key=key)
            self.send_json(200, {"ok": True, "duplicate": True})
            return
        fresh, latest_timestamp = mark_conversation_event_if_fresh(fields)
        if not fresh:
            log_event(
                "webhook_stale",
                sender=sender,
                conversation_id=fields.get("conversation_id"),
                message_id=fields.get("message_id"),
                message_timestamp=fields.get("timestamp"),
                latest_timestamp=latest_timestamp,
            )
            self.send_json(200, {"ok": True, "ignored": "stale message"})
            return
        if handle_reaction_only(fields):
            self.send_json(200, {"ok": True, "reaction_only": True})
            return
        toolsets = CONFIG.get("AGENTPHONE_FULL_HERMES_TOOLSETS", "all") if sender in full_access else CONFIG.get("AGENTPHONE_HERMES_TOOLSETS", "web,vision")
        job = start_conversation_job(fields, fields.get("reply_to") or fields.get("sender") or "")
        thread = threading.Thread(target=run_hermes_and_reply, args=(payload, fields, toolsets, job), daemon=True)
        thread.start()
        self.send_json(200, {"ok": True, "accepted": True})


def start_http_server() -> BridgeHTTPServer:
    server = BridgeHTTPServer((HOST, PORT), Handler)
    thread = threading.Thread(target=server.serve_forever, name="http-server", daemon=True)
    thread.start()
    log_event("http_server_started", host=HOST, port=PORT)
    return server


def cloudflared_reader(proc: subprocess.Popen[str], q: queue.Queue[str]) -> None:
    try:
        assert proc.stdout is not None
        with CLOUDFLARED_LOG.open("a", encoding="utf-8") as log:
            for line in proc.stdout:
                safe_line = redact_string(line.rstrip("\n"))
                log.write(safe_line + "\n")
                log.flush()
                m = TUNNEL_RE.search(line)
                if m:
                    q.put(m.group(0))
    except Exception as exc:
        log_event("cloudflared_reader_failed", error=str(exc))


def start_cloudflared() -> tuple[subprocess.Popen[str], str]:
    cloudflared = CONFIG.get("CLOUDFLARED_BIN", "/usr/local/bin/cloudflared")
    if not Path(cloudflared).exists():
        cloudflared = "cloudflared"
    cmd = [cloudflared, "tunnel", "--no-autoupdate", "--url", LOCAL_URL]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
    q: queue.Queue[str] = queue.Queue()
    threading.Thread(target=cloudflared_reader, args=(proc, q), name="cloudflared-reader", daemon=True).start()
    deadline = time.time() + 90
    public_url = ""
    while time.time() < deadline:
        if proc.poll() is not None:
            raise RuntimeError(f"cloudflared exited before tunnel URL, code={proc.returncode}")
        try:
            public_url = q.get(timeout=1)
            break
        except queue.Empty:
            continue
    if not public_url:
        proc.terminate()
        raise RuntimeError("timed out waiting for cloudflared quick tunnel URL")
    log_event("cloudflared_started", public_url=public_url)
    return proc, public_url


def register_agent_webhook(public_url: str) -> dict[str, Any]:
    agent_id = require_config(CONFIG, "AGENTPHONE_AGENT_ID")
    hook_url = public_url.rstrip("/") + HOOK_PATH
    payload = {
        "url": hook_url,
        "contextLimit": int(CONFIG.get("AGENTPHONE_WEBHOOK_CONTEXT_LIMIT", "10")),
        "timeout": int(CONFIG.get("AGENTPHONE_WEBHOOK_TIMEOUT", "30")),
    }
    resp = api_request("POST", f"/v1/agents/{agent_id}/webhook", payload, timeout=45)
    if not isinstance(resp, dict) or not resp.get("secret"):
        raise RuntimeError(f"webhook registration response missing secret: {sanitize(resp)}")
    state = {
        "public_url": public_url,
        "hook_url": hook_url,
        "agent_id": agent_id,
        "webhook_id": resp.get("id"),
        "webhook_secret": resp.get("secret"),
        "status": resp.get("status"),
        "contextLimit": resp.get("contextLimit"),
        "timeout": resp.get("timeout"),
        "registered_at": utc_now(),
    }
    # Keep the real secret in state.json for verification after restarts; sanitize only logs.
    tmp = STATE_PATH.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(state, indent=2, sort_keys=True), encoding="utf-8")
    os.chmod(tmp, 0o600)
    tmp.replace(STATE_PATH)
    os.chmod(STATE_PATH, 0o600)
    log_event("webhook_registered", public_url=public_url, hook_url=hook_url, status=resp.get("status"), webhook_id=resp.get("id"))
    return state


def shutdown(server: BridgeHTTPServer | None = None) -> None:
    STOP.set()
    if server:
        try:
            server.shutdown()
        except Exception:
            pass
    proc = CLOUDFLARED_PROC
    if proc and proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()


def main() -> int:
    global CONFIG, WEBHOOK_SECRET, PUBLIC_URL, CLOUDFLARED_PROC
    BRIDGE_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG = load_config()
    for key in ("AGENTPHONE_API_KEY", "AGENTPHONE_AGENT_ID"):
        require_config(CONFIG, key)
    # Ensure sidecar files are not world-readable if they already exist.
    for path in (BRIDGE_ENV, STATE_PATH, SEEN_PATH, WATERMARK_PATH):
        if path.exists():
            try:
                os.chmod(path, 0o600)
            except OSError:
                pass

    server: BridgeHTTPServer | None = None

    def _signal_handler(signum: int, _frame: Any) -> None:
        log_event("signal", signum=signum)
        shutdown(server)

    signal.signal(signal.SIGTERM, _signal_handler)
    signal.signal(signal.SIGINT, _signal_handler)

    server = start_http_server()
    last_error: Exception | None = None
    for attempt in range(1, 3):
        try:
            stable_url = str(CONFIG.get("AGENTPHONE_PUBLIC_URL") or "").strip().rstrip("/")
            if stable_url:
                CLOUDFLARED_PROC, public_url = None, stable_url
                log_event("stable_public_url", public_url=stable_url)
            else:
                CLOUDFLARED_PROC, public_url = start_cloudflared()
            state = register_agent_webhook(public_url)
            PUBLIC_URL = public_url
            WEBHOOK_SECRET = str(state["webhook_secret"])
            break
        except Exception as exc:
            last_error = exc
            log_event("startup_attempt_failed", attempt=attempt, error=str(exc))
            if CLOUDFLARED_PROC and CLOUDFLARED_PROC.poll() is None:
                CLOUDFLARED_PROC.terminate()
            time.sleep(3)
    else:
        log_event("startup_failed", error=str(last_error))
        shutdown(server)
        return 1

    print(f"AgentPhone bridge running on {LOCAL_URL}{HOOK_PATH} via {PUBLIC_URL}{HOOK_PATH}", flush=True)
    log_event("bridge_ready", public_url=PUBLIC_URL, hook_path=HOOK_PATH)
    try:
        while not STOP.is_set():
            if CLOUDFLARED_PROC and CLOUDFLARED_PROC.poll() is not None:
                log_event("cloudflared_exited", returncode=CLOUDFLARED_PROC.returncode)
                return 1
            time.sleep(2)
    finally:
        shutdown(server)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
