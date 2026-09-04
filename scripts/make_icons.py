#!/usr/bin/env python3
"""
Generates the PWA home-screen icons (icon-192.png, icon-512.png, icon-maskable-512.png)
using only the standard library. Run once; re-run if you change the colors.

    python scripts/make_icons.py
"""

import os
import struct
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

TEAL = (15, 118, 110)
WHITE = (255, 255, 255)
SS = 3  # supersampling factor for smooth edges


def rounded_rect(x, y, w, h, r):
    """True if (x,y) is inside a rounded rect occupying 0..w, 0..h."""
    cx = min(max(x, r), w - r)
    cy = min(max(y, r), h - r)
    return (x - cx) ** 2 + (y - cy) ** 2 <= r * r


def in_triangle(px, py, a, b, c):
    def sign(p1, p2, p3):
        return (p1[0] - p3[0]) * (p2[1] - p3[1]) - (p2[0] - p3[0]) * (p1[1] - p3[1])
    d1 = sign((px, py), a, b)
    d2 = sign((px, py), b, c)
    d3 = sign((px, py), c, a)
    neg = (d1 < 0) or (d2 < 0) or (d3 < 0)
    pos = (d1 > 0) or (d2 > 0) or (d3 > 0)
    return not (neg and pos)


def shade(u, v, maskable):
    """Return colour at normalised (u, v) in 0..1, or None for transparent."""
    # Maskable icons need their art inside a safe circle, so shrink the glyph.
    k = 0.78 if maskable else 1.0
    cu = 0.5 + (u - 0.5) / k
    cv = 0.5 + (v - 0.5) / k

    house = False
    # roof
    if in_triangle(cu, cv, (0.50, 0.19), (0.11, 0.51), (0.89, 0.51)):
        house = True
    # body
    if 0.215 <= cu <= 0.785 and 0.48 <= cv <= 0.815:
        house = True
    if not house:
        return None
    # door punched back out
    if 0.425 <= cu <= 0.575 and 0.60 <= cv <= 0.815:
        return None
    # two windows
    if 0.285 <= cu <= 0.385 and 0.585 <= cv <= 0.685:
        return None
    if 0.615 <= cu <= 0.715 and 0.585 <= cv <= 0.685:
        return None
    return WHITE


def render(size, maskable=False):
    n = size * SS
    radius = n * (0.5 if maskable else 0.22)
    rows = []
    for py in range(size):
        row = bytearray()
        for px in range(size):
            rs = gs = bs = 0
            for sy in range(SS):
                for sx in range(SS):
                    X = px * SS + sx + 0.5
                    Y = py * SS + sy + 0.5
                    if not rounded_rect(X, Y, n, n, radius):
                        c = (246, 247, 246)  # page background outside the tile
                    else:
                        g = shade(X / n, Y / n, maskable)
                        c = g if g else TEAL
                    rs += c[0]; gs += c[1]; bs += c[2]
            k = SS * SS
            row += bytes((rs // k, gs // k, bs // k))
        rows.append(bytes(row))
    return rows


def write_png(path, size, rows):
    raw = b"".join(b"\x00" + r for r in rows)
    comp = zlib.compress(raw, 9)

    def chunk(tag, data):
        return (struct.pack(">I", len(data)) + tag + data +
                struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))

    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 2, 0, 0, 0))
    png += chunk(b"IDAT", comp)
    png += chunk(b"IEND", b"")
    with open(path, "wb") as f:
        f.write(png)
    print("  wrote {} ({:,} bytes)".format(os.path.basename(path), len(png)))


def main():
    print("Generating icons…")
    for size, name, mask in [
        (192, "icon-192.png", False),
        (512, "icon-512.png", False),
        (512, "icon-maskable-512.png", True),
    ]:
        write_png(os.path.join(ROOT, name), size, render(size, mask))


if __name__ == "__main__":
    main()
