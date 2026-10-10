#!/usr/bin/env python3
"""Generate the Fariyad launcher icon (mipmap/ic_launcher.png) without any image
libraries — hand-rolled PNG encoder. Dark tile + yellow speech bubble.
Run: python3 scripts/gen_icon.py
"""
import os
import struct
import zlib

W = H = 96

def make_png(width, height, pixel_fn):
    rows = bytearray()
    for y in range(height):
        row = bytearray(b"\x00")  # filter type 0
        for x in range(width):
            r, g, b = pixel_fn(x, y)
            row += bytes((r, g, b))
        rows += row

    def chunk(tag, data):
        payload = tag + data
        return struct.pack(">I", len(data)) + payload + struct.pack(">I", zlib.crc32(payload) & 0xFFFFFFFF)

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", ihdr)
            + chunk(b"IDAT", zlib.compress(bytes(rows), 9))
            + chunk(b"IEND", b""))

# palette
BG = (10, 14, 20)        # #0a0e14
YELLOW = (255, 214, 10)  # #ffd60a
DARK = (10, 14, 20)
EDGE = (184, 155, 10)    # #b89b0a

def pixel(x, y):
    # speech bubble: rounded rect 12..84 x 12..64, tail at bottom-left
    in_main = 14 <= x <= 82 and 14 <= y <= 62
    if in_main:
        # rounded corners
        cx, cy = 14, 14
        r = 10
        for (ccx, ccy) in ((14, 14), (82, 14), (14, 62), (82, 62)):
            pass
        near_corner = (x < 24 and y < 24) or (x > 72 and y < 24) or (x < 24 and y > 52) or (x > 72 and y > 52)
        if near_corner:
            # carve circles
            import math
            centers = [(24, 24), (72, 24), (24, 52), (72, 52)]
            inside_round = any((x - ccx) ** 2 + (y - ccy) ** 2 <= 100 for (ccx, ccy) in centers)
            if not inside_round:
                return BG
        # three "lines" of text (queue bars) in dark
        if 26 <= y <= 32 and 26 <= x <= (26 + (x and 0)) + (44 if y <= 32 else 0):
            pass
        if 26 <= y <= 31 and 26 <= x <= 70:
            return DARK
        if 40 <= y <= 45 and 26 <= x <= 58:
            return DARK
        if 54 <= y <= 59 and 26 <= x <= 48:
            return DARK
        return YELLOW
    # tail: triangle from (26, 62) down to (34, 80)
    if 62 <= y <= 80:
        if 26 <= x <= 42:
            x0 = 26
            x1 = 26 + (y - 62) * 0.9
            if x0 <= x <= x1:
                return YELLOW
    # border ring
    return BG

png = make_png(W, H, pixel)
out = os.path.join(os.path.dirname(__file__), "..", "android", "app", "src", "main", "res", "mipmap")
os.makedirs(out, exist_ok=True)
with open(os.path.join(out, "ic_launcher.png"), "wb") as f:
    f.write(png)
print("icon written:", os.path.join(out, "ic_launcher.png"), f"({len(png)} bytes)")
