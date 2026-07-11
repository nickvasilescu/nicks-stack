#!/usr/bin/env python3
"""Dependency-free OTLP/HTTP test trace sender for Latitude-like endpoints.

Required env:
  LATITUDE_API_KEY
  LATITUDE_PROJECT_SLUG

Optional env:
  LATITUDE_INGEST_URL=https://ingest.latitude.so/v1/traces
  LATITUDE_SERVICE_NAME=agent-observability-test
  LATITUDE_TRACE_NAME=agent-observability-test-trace

This is a reusable skill helper. It never prints the API key.
"""
from __future__ import annotations

import json
import os
import secrets
import sys
import time
import urllib.error
import urllib.request


def attr(key: str, value: str) -> dict:
    return {"key": key, "value": {"stringValue": value}}


def main() -> int:
    api_key = os.environ.get("LATITUDE_API_KEY")
    project = os.environ.get("LATITUDE_PROJECT_SLUG")
    ingest_url = os.environ.get("LATITUDE_INGEST_URL", "https://ingest.latitude.so/v1/traces")
    service = os.environ.get("LATITUDE_SERVICE_NAME", "agent-observability-test")
    trace_name = os.environ.get("LATITUDE_TRACE_NAME", "agent-observability-test-trace")
    if not api_key or not project:
        missing = [k for k, v in {"LATITUDE_API_KEY": api_key, "LATITUDE_PROJECT_SLUG": project}.items() if not v]
        print("missing_required_env=" + ",".join(missing), file=sys.stderr)
        return 2

    now_ns = time.time_ns()
    trace_id = secrets.token_hex(16)
    span_id = secrets.token_hex(8)
    body = {
        "resourceSpans": [{
            "resource": {"attributes": [attr("service.name", service)]},
            "scopeSpans": [{
                "scope": {"name": "agent-observability-skill", "version": "1.0.0"},
                "spans": [{
                    "traceId": trace_id,
                    "spanId": span_id,
                    "name": trace_name,
                    "kind": 1,
                    "startTimeUnixNano": str(now_ns),
                    "endTimeUnixNano": str(now_ns + 50_000_000),
                    "attributes": [
                        attr("gen_ai.system", "agent"),
                        attr("latitude.setup.source", "skill-script"),
                    ],
                }],
            }],
        }]
    }
    req = urllib.request.Request(
        ingest_url,
        data=json.dumps(body, separators=(",", ":")).encode(),
        method="POST",
        headers={
            "Authorization": f"Bearer {api_key}",
            "X-Latitude-Project": project,
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            response = resp.read().decode("utf-8", errors="replace")
            print(json.dumps({
                "ok": 200 <= resp.status < 300,
                "status": resp.status,
                "project": project,
                "trace_id": trace_id,
                "span_id": span_id,
                "response": response,
            }, indent=2))
            return 0 if 200 <= resp.status < 300 else 1
    except urllib.error.HTTPError as exc:
        print(json.dumps({
            "ok": False,
            "status": exc.code,
            "project": project,
            "error": exc.read().decode("utf-8", errors="replace"),
        }, indent=2), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
