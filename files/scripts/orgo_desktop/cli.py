#!/usr/bin/env python3
"""CLI for local Orgo Desktop API.

Examples:
  orgo-desktop doctor
  orgo-desktop screenshot /tmp/desk.png
  orgo-desktop bash 'hostname'
  orgo-desktop click 100 200
  orgo-desktop click 100 200 --verify
  orgo-desktop drag 100 200 300 400 --verify
  orgo-desktop click-path 100 200 300 400
  orgo-desktop type 'hello'
  orgo-desktop key Escape
  orgo-desktop open-url https://lichess.org/
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Allow running as script without install
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from orgo_desktop.client import (  # noqa: E402
    DesktopAPIError,
    OrgoDesktopClient,
    default_client,
    is_colocated,
)


def _out(data) -> None:
    if isinstance(data, (dict, list)):
        print(json.dumps(data, indent=2, default=str))
    else:
        print(data)


def _bbox(args) -> tuple[int, int, int, int] | None:
    if getattr(args, "bbox", None):
        parts = [int(x) for x in args.bbox.split(",")]
        if len(parts) != 4:
            raise SystemExit("--bbox must be left,top,right,bottom")
        return tuple(parts)  # type: ignore[return-value]
    return None


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="orgo-desktop", description="Local Orgo Desktop API client")
    p.add_argument("--base-url", default=None, help="Override ORGO_DESKTOP_API_URL")
    p.add_argument("--timeout", type=float, default=30)
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("doctor", help="Readiness report (health+auth+screenshot+bash+prefer)")
    sub.add_parser("health")
    sub.add_parser("info")
    sub.add_parser("status")
    sub.add_parser("colocated", help="Exit 0 if local desktop-api healthy")

    s = sub.add_parser("screenshot")
    s.add_argument("path", nargs="?", default="/tmp/orgo-desktop-screenshot.png")

    s = sub.add_parser("bash")
    s.add_argument("command")
    s.add_argument("--timeout", type=int, default=60)

    s = sub.add_parser("click")
    s.add_argument("x", type=int)
    s.add_argument("y", type=int)
    s.add_argument("--button", default="left", choices=["left", "right", "middle"])
    s.add_argument("--double", action="store_true")
    s.add_argument("--verify", action="store_true", help="Compare frame fingerprint before/after")
    s.add_argument("--settle", type=float, default=0.2)
    s.add_argument("--bbox", default=None, help="left,top,right,bottom ROI for verify")

    s = sub.add_parser("drag", help="Drag start_x start_y end_x end_y")
    s.add_argument("start_x", type=int)
    s.add_argument("start_y", type=int)
    s.add_argument("end_x", type=int)
    s.add_argument("end_y", type=int)
    s.add_argument("--verify", action="store_true")
    s.add_argument("--settle", type=float, default=0.25)
    s.add_argument("--bbox", default=None, help="left,top,right,bottom ROI for verify")

    s = sub.add_parser("click-path", help="Two-click select→destination with verify")
    s.add_argument("x1", type=int)
    s.add_argument("y1", type=int)
    s.add_argument("x2", type=int)
    s.add_argument("y2", type=int)
    s.add_argument("--settle", type=float, default=0.35)
    s.add_argument("--no-verify", action="store_true")
    s.add_argument("--bbox", default=None, help="left,top,right,bottom ROI for verify")
    s.add_argument("--button", default="left", choices=["left", "right", "middle"])

    s = sub.add_parser("type")
    s.add_argument("text")

    s = sub.add_parser("key")
    s.add_argument("key")

    s = sub.add_parser("scroll")
    s.add_argument("direction", choices=["up", "down"])
    s.add_argument("--amount", type=int, default=3)
    s.add_argument("--x", type=int, default=640)
    s.add_argument("--y", type=int, default=360)

    s = sub.add_parser("wait")
    s.add_argument("seconds", type=float)

    s = sub.add_parser("open-url")
    s.add_argument("url")

    s = sub.add_parser("smoke", help="Run pass/fail smoke suite")
    s.add_argument("--out-dir", default="/tmp/orgo-desktop-smoke")

    args = p.parse_args(argv)

    if args.cmd == "colocated":
        base = args.base_url or __import__("os").environ.get(
            "ORGO_DESKTOP_API_URL", "http://127.0.0.1:8080"
        )
        ok = is_colocated(base)
        print(json.dumps({"colocated": ok, "base_url": base}))
        return 0 if ok else 1

    try:
        client = default_client()
        if args.base_url:
            client = OrgoDesktopClient(base_url=args.base_url, timeout=args.timeout)
        else:
            client.timeout = args.timeout
    except DesktopAPIError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2

    try:
        if args.cmd == "doctor":
            report = client.doctor()
            _out(report)
            return 0 if report.get("ready") else 1
        if args.cmd == "health":
            _out(client.health())
            return 0
        if args.cmd == "info":
            _out(client.info())
            return 0
        if args.cmd == "status":
            _out(client.status())
            return 0
        if args.cmd == "screenshot":
            path = client.save_screenshot(args.path)
            _out({"ok": True, "path": str(path), "bytes": path.stat().st_size})
            return 0
        if args.cmd == "bash":
            _out(client.bash(args.command, timeout=args.timeout))
            return 0
        if args.cmd == "click":
            _out(
                client.click(
                    args.x,
                    args.y,
                    button=args.button,
                    double=args.double,
                    verify=args.verify,
                    settle_s=args.settle,
                    bbox=_bbox(args),
                )
            )
            return 0
        if args.cmd == "drag":
            _out(
                client.drag(
                    args.start_x,
                    args.start_y,
                    args.end_x,
                    args.end_y,
                    verify=args.verify,
                    settle_s=args.settle,
                    bbox=_bbox(args),
                )
            )
            return 0
        if args.cmd == "click-path":
            _out(
                client.click_path(
                    args.x1,
                    args.y1,
                    args.x2,
                    args.y2,
                    settle_s=args.settle,
                    verify=not args.no_verify,
                    bbox=_bbox(args),
                    button=args.button,
                )
            )
            return 0
        if args.cmd == "type":
            _out(client.type_text(args.text))
            return 0
        if args.cmd == "key":
            _out(client.key(args.key))
            return 0
        if args.cmd == "scroll":
            _out(client.scroll(args.direction, args.amount, x=args.x, y=args.y))
            return 0
        if args.cmd == "wait":
            _out(client.wait(args.seconds))
            return 0
        if args.cmd == "open-url":
            _out(client.open_url(args.url))
            return 0
        if args.cmd == "smoke":
            from orgo_desktop.smoke_test import run_smoke

            result = run_smoke(client, out_dir=args.out_dir)
            _out(result)
            return 0 if result.get("passed") else 1
    except DesktopAPIError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    print(f"unknown command {args.cmd}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
