#!/usr/bin/env python3
"""Orgo template REST helper for Hermes (list / get / validate / build-status / delete).

Requires ORGO_API_KEY. Never prints the key.
"""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

API_BASE = os.environ.get("ORGO_API_BASE", "https://www.orgo.ai/api").rstrip("/")


def _load_key() -> str:
    key = os.environ.get("ORGO_API_KEY", "").strip()
    if key:
        return key
    env_path = Path.home() / ".hermes" / ".env"
    if env_path.is_file():
        for line in env_path.read_text(encoding="utf-8", errors="replace").splitlines():
            if line.startswith("ORGO_API_KEY="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise SystemExit("ORGO_API_KEY not set")


def req(method: str, path: str, body=None):
    data = None if body is None else json.dumps(body).encode()
    request = urllib.request.Request(
        f"{API_BASE}{path}",
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {_load_key()}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=180) as resp:
            raw = resp.read().decode()
            return resp.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        raw = e.read().decode()
        try:
            parsed = json.loads(raw)
        except Exception:
            parsed = raw[:2000]
        return e.code, parsed


def cmd_list(_args):
    st, body = req("GET", "/templates")
    if st >= 300:
        raise SystemExit(f"list failed {st}: {body}")
    templates = body.get("templates") or []
    for t in sorted(templates, key=lambda x: x.get("ref") or ""):
        print(f"{t.get('ref')}\tpublished={t.get('published')}\tdigest={(t.get('digest') or '')[:12]}")
    print(f"# count={len(templates)}", file=sys.stderr)


def cmd_get(args):
    if len(args) < 3:
        raise SystemExit("usage: get <namespace> <name> <version>")
    ns, name, ver = args[:3]
    st, body = req("GET", f"/templates/{ns}/{name}/{ver}")
    print(json.dumps(body, indent=2))
    if st >= 300:
        raise SystemExit(st)


def cmd_validate(args):
    if not args:
        raise SystemExit("usage: validate <template.json>")
    path = Path(args[0])
    doc = json.loads(path.read_text(encoding="utf-8"))
    # accept raw document or {"template": <full doc>} wrapper from GET
    if "api_version" not in doc and "template" in doc and isinstance(doc["template"], dict):
        if "api_version" in doc["template"]:
            doc = doc["template"]
    st, body = req("POST", "/templates/validate", doc)
    print(json.dumps(body, indent=2) if isinstance(body, dict) else body)
    ok = st < 300 and isinstance(body, dict) and body.get("ok") is True
    raise SystemExit(0 if ok else 1)


def cmd_build_status(args):
    if len(args) < 3:
        raise SystemExit("usage: build-status <namespace> <name> <version>")
    ns, name, ver = args[:3]
    st, body = req("GET", f"/templates/{ns}/{name}/{ver}/build")
    print(json.dumps(body, indent=2) if isinstance(body, dict) else body)
    if st >= 300:
        raise SystemExit(st)
    if isinstance(body, dict) and body.get("status") == "ready":
        raise SystemExit(0)
    raise SystemExit(2)


def cmd_delete(args):
    if len(args) < 3:
        raise SystemExit("usage: delete <namespace> <name> <version>")
    ns, name, ver = args[:3]
    st, body = req("DELETE", f"/templates/{ns}/{name}/{ver}")
    print(json.dumps(body, indent=2) if isinstance(body, dict) else body)
    raise SystemExit(0 if st < 300 else 1)


def cmd_global(_args):
    st, body = req("GET", "/templates/global")
    print(json.dumps(body, indent=2))
    raise SystemExit(0 if st < 300 else 1)


def main():
    if len(sys.argv) < 2:
        print(
            "usage: orgo_template_ops.py "
            "{list|global|get|validate|build-status|delete} ...",
            file=sys.stderr,
        )
        raise SystemExit(2)
    cmd, *args = sys.argv[1:]
    {
        "list": cmd_list,
        "global": cmd_global,
        "get": cmd_get,
        "validate": cmd_validate,
        "build-status": cmd_build_status,
        "delete": cmd_delete,
    }[cmd](args)


if __name__ == "__main__":
    main()
