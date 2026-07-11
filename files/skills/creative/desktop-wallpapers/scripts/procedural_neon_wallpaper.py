#!/usr/bin/env python3
"""
Dependency-free procedural PNG wallpaper generator.

Creates a 1920x1080 dark neon Linux command-center wallpaper using only
Python stdlib. Useful when AI image generation is unavailable or the VM lacks
ImageMagick/Pillow.

Usage:
  python3 procedural_neon_wallpaper.py /root/Pictures/hermes-linux-neon-command-center.png
"""
from __future__ import annotations

from pathlib import Path
import math
import random
import struct
import sys
import zlib

W, H = 1920, 1080


def clamp(v: float) -> int:
    return 0 if v < 0 else 255 if v > 255 else int(v)


def add_glow(px, x, y, cx, cy, color, radius, strength=1.0):
    dx = x - cx
    dy = y - cy
    d2 = dx * dx + dy * dy
    r2 = radius * radius
    if d2 > r2:
        return px
    t = (1 - d2 / r2) ** 2 * strength
    return tuple(clamp(px[k] + color[k] * t) for k in range(3))


def dist_to_seg(px, py, x1, y1, x2, y2):
    vx = x2 - x1
    vy = y2 - y1
    wx = px - x1
    wy = py - y1
    c1 = vx * wx + vy * wy
    if c1 <= 0:
        return math.hypot(px - x1, py - y1)
    c2 = vx * vx + vy * vy
    if c2 <= c1:
        return math.hypot(px - x2, py - y2)
    b = c1 / c2
    bx = x1 + b * vx
    by = y1 + b * vy
    return math.hypot(px - bx, py - by)


def chunk(tag: bytes, data: bytes) -> bytes:
    return (
        struct.pack(">I", len(data))
        + tag
        + data
        + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
    )


def generate(out: Path) -> None:
    random.seed(1337)
    stars = [(random.randrange(W), random.randrange(H), random.random()) for _ in range(420)]
    nodes = [
        (random.randrange(80, W - 80), random.randrange(80, H - 80), random.random())
        for _ in range(34)
    ]
    connections = []
    for i, (x1, y1, _) in enumerate(nodes):
        dists = []
        for j, (x2, y2, __) in enumerate(nodes):
            if i < j:
                d = (x1 - x2) ** 2 + (y1 - y2) ** 2
                if d < 260000:
                    dists.append((d, j))
        for d, j in sorted(dists)[:3]:
            connections.append((i, j, d))

    rows = []
    for y in range(H):
        row = bytearray()
        for x in range(W):
            tx = x / W
            ty = y / H
            r = 5 + 12 * tx + 5 * ty
            g = 8 + 10 * tx + 4 * math.sin(ty * math.pi)
            b = 22 + 38 * (1 - ty) + 18 * tx

            # Vignette.
            dx = (x - W * 0.5) / (W * 0.74)
            dy = (y - H * 0.48) / (H * 0.72)
            vig = max(0, 1 - 0.72 * (dx * dx + dy * dy))
            r *= 0.45 + 0.55 * vig
            g *= 0.45 + 0.55 * vig
            b *= 0.50 + 0.60 * vig
            px = (r, g, b)

            # Perspective grid near bottom.
            if y > H * 0.58:
                horizon = H * 0.58
                yy = (y - horizon) / (H - horizon)
                for k in range(1, 15):
                    gy = horizon + (H - horizon) * (k / 15) ** 1.9
                    d = abs(y - gy)
                    if d < 1.4:
                        glow = (1 - d / 1.4) * 0.45 * yy
                        px = (px[0] + 10 * glow, px[1] + 170 * glow, px[2] + 210 * glow)
                cx = W * 0.52
                for angle in [a * 0.055 for a in range(-16, 17)]:
                    xx = cx + (y - horizon) * math.tan(angle)
                    d = abs(x - xx)
                    if d < 1.2:
                        glow = (1 - d / 1.2) * 0.33 * yy
                        px = (px[0] + 70 * glow, px[1] + 70 * glow, px[2] + 210 * glow)

            px = add_glow(px, x, y, W * 0.74, H * 0.35, (110, 0, 210), 520, 0.55)
            px = add_glow(px, x, y, W * 0.28, H * 0.34, (0, 190, 210), 500, 0.42)
            px = add_glow(px, x, y, W * 0.52, H * 0.85, (0, 130, 255), 420, 0.28)

            # Abstract terminal panels; no readable text/logos.
            panels = [(1110, 180, 520, 250), (1260, 470, 420, 210), (820, 360, 360, 200)]
            for px0, py0, pw, ph in panels:
                if px0 <= x <= px0 + pw and py0 <= y <= py0 + ph:
                    border = min(x - px0, px0 + pw - x, y - py0, py0 + ph - y)
                    shade = 0.95 if border < 3 else 0.20
                    scan = 0.06 if (y - py0) % 12 < 2 else 0
                    px = (px[0] + 5, px[1] + 18 + 150 * shade + 70 * scan, px[2] + 22 + 190 * shade + 90 * scan)
                    if 24 < y - py0 < ph - 20 and ((y - py0 - 24) % 28) < 4 and 28 < x - px0 < pw - 40:
                        line_len = pw * (0.25 + 0.55 * ((((y - py0) // 28) * 37) % 100) / 100)
                        if x - px0 < 28 + line_len:
                            px = (40, 230, 220)

            # Network graph.
            for i, j, d2 in connections:
                x1, y1, _ = nodes[i]
                x2, y2, _ = nodes[j]
                d = dist_to_seg(x, y, x1, y1, x2, y2)
                if d < 1.1:
                    alpha = (1 - d / 1.1) * max(0.15, 1 - d2 / 260000) * 0.55
                    px = (px[0] + 20 * alpha, px[1] + 180 * alpha, px[2] + 230 * alpha)
            for nx, ny, p in nodes:
                dd = (x - nx) ** 2 + (y - ny) ** 2
                if dd < 30:
                    a = (1 - dd / 30) * (0.35 + 0.65 * p)
                    px = (px[0] + 80 * a, px[1] + 210 * a, px[2] + 255 * a)

            # Subtle abstract penguin silhouette.
            cx, cy = 410, 675
            body = ((x - cx) / 150) ** 2 + ((y - cy) / 205) ** 2
            belly = ((x - cx) / 93) ** 2 + ((y - (cy + 48)) / 142) ** 2
            head = ((x - cx) / 100) ** 2 + ((y - (cy - 184)) / 88) ** 2
            if body < 1 or head < 1:
                px = (px[0] * 0.32 + 4, px[1] * 0.32 + 7, px[2] * 0.32 + 16)
                if 0.86 < body < 1.05 or 0.84 < head < 1.04:
                    px = (px[0] + 10.5, px[1] + 112, px[2] + 133)
            if belly < 1 and body < 1:
                a = 1 - belly
                px = (px[0] + 32 * a, px[1] + 50 * a, px[2] + 70 * a)
            for ex in (cx - 36, cx + 36):
                if (x - ex) ** 2 + (y - (cy - 202)) ** 2 < 42:
                    px = (105, 255, 245)
            if abs(x - cx) < 34 - (y - (cy - 174)) * 0.9 and cy - 174 <= y <= cy - 144:
                px = (255, 134, 52)

            row += bytes((clamp(px[0]), clamp(px[1]), clamp(px[2])))
        rows.append(bytearray(row))

    # Star overlay.
    for sx, sy, p in stars:
        for yy in range(max(0, sy - 1), min(H, sy + 2)):
            for xx in range(max(0, sx - 1), min(W, sx + 2)):
                d = abs(xx - sx) + abs(yy - sy)
                if d <= 1:
                    idx = xx * 3
                    boost = int((180 if d == 0 else 70) * (0.3 + 0.7 * p))
                    rows[yy][idx] = clamp(rows[yy][idx] + boost)
                    rows[yy][idx + 1] = clamp(rows[yy][idx + 1] + boost)
                    rows[yy][idx + 2] = clamp(rows[yy][idx + 2] + boost + 20)

    raw = b"".join(b"\x00" + bytes(r) for r in rows)
    png = (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(raw, 6))
        + chunk(b"IEND", b"")
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(png)


def main() -> int:
    out = Path(sys.argv[1]).expanduser() if len(sys.argv) > 1 else Path.home() / "Pictures/hermes-linux-neon-command-center.png"
    generate(out)
    data = out.read_bytes()
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise SystemExit("Generated file is not a PNG")
    width, height = struct.unpack(">II", data[16:24])
    print(f"{out.resolve()}\nPNG OK: {width}x{height}, {out.stat().st_size} bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
