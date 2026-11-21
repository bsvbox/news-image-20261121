#!/usr/bin/env python3
"""The World in One Page - Saturday 21 November 2026.

A tiny newspaper front page drawn pixel by pixel with nothing but the
Python standard library. It sums up the world's news of 21 November 2026
in one 1024x1024 PNG. No network, no randomness, no clock: running it
twice writes the same bytes twice.

Run:  MAKEFUN_OUTPUT_DIR=out python3 main.py
"""

import binascii
import math
import os
import struct
import zlib

SIDE = 1024

# --- inks ---------------------------------------------------------------
BG = (246, 241, 231)        # paper
NAV = (22, 35, 63)          # masthead navy
NAVDEEP = (13, 22, 42)      # darkest navy
NIGHTSKY = (16, 24, 54)     # lead sky top
AURUM = (217, 164, 65)      # gold rule
AURUM_LT = (240, 196, 90)   # pale gold
SNOW = (255, 255, 255)
SOOT = (26, 26, 26)
ASH = (74, 68, 56)
EDGE = (201, 191, 169)      # card border
WINE = (122, 31, 31)
SEA = (14, 90, 122)
LEAF = (30, 122, 52)
EMBER = (179, 84, 30)
GRAPE = (106, 31, 160)
DUSK = (24, 28, 66)         # skyline blocks
FLAME = (255, 140, 0)
FLAME_HOT = (255, 220, 60)

# --- the sheet ----------------------------------------------------------
sheet = bytearray(SIDE * SIDE * 3)


def px(x, y, c):
    """Paint one pixel, silently ignoring out-of-sheet coordinates."""
    if 0 <= x < SIDE and 0 <= y < SIDE:
        o = (y * SIDE + x) * 3
        sheet[o] = c[0]
        sheet[o + 1] = c[1]
        sheet[o + 2] = c[2]


def rect(x, y, w, h, c):
    """Paint a filled rectangle, clipped to the sheet."""
    if w <= 0 or h <= 0:
        return
    xa = x if x > 0 else 0
    ya = y if y > 0 else 0
    xb = x + w if x + w < SIDE else SIDE
    yb = y + h if y + h < SIDE else SIDE
    if xa >= xb or ya >= yb:
        return
    stripe = bytes(c) * (xb - xa)
    for yy in range(ya, yb):
        o = (yy * SIDE + xa) * 3
        sheet[o:o + len(stripe)] = stripe


def hbar(xa, xb, y, c, thick=1):
    for k in range(thick):
        for xx in range(xa, xb + 1):
            px(xx, y + k, c)


def vbar(x, ya, yb, c, thick=1):
    for k in range(thick):
        for yy in range(ya, yb + 1):
            px(x + k, yy, c)


def seg(xa, ya, xb, yb, c, thick=1):
    """Bresenham segment, thickened by stamping squares."""
    dx = xb - xa if xb >= xa else xa - xb
    dy = yb - ya if yb >= ya else ya - yb
    sx = 1 if xa < xb else -1
    sy = 1 if ya < yb else -1
    err = dx - dy
    x, y = xa, ya
    while True:
        for a in range(thick):
            for b in range(thick):
                px(x + a, y + b, c)
        if x == xb and y == yb:
            return
        e2 = 2 * err
        if e2 > -dy:
            err -= dy
            x += sx
        if e2 < dx:
            err += dx
            y += sy


def disc(cx, cy, r, c):
    for dy in range(-r, r + 1):
        half = int(math.sqrt(max(0, r * r - dy * dy)))
        for xx in range(cx - half, cx + half + 1):
            px(xx, cy + dy, c)


def ring(cx, cy, r, c, thick=2):
    for deg in range(360):
        rad = math.radians(deg)
        for t in range(thick):
            px(int(cx + (r + t) * math.cos(rad)),
               int(cy + (r + t) * math.sin(rad)), c)


def tri(xa, ya, xb, yb, xc, yc, c):
    """Scanline-filled triangle."""
    lo = ya if ya < yb and ya < yc else (yb if yb < yc else yc)
    hi = ya if ya > yb and ya > yc else (yb if yb > yc else yc)
    for yy in range(lo, hi + 1):
        hits = []
        for (px0, py0, qx0, qy0) in ((xa, ya, xb, yb), (xb, yb, xc, yc),
                                     (xc, yc, xa, ya)):
            if py0 == qy0:
                continue
            if min(py0, qy0) <= yy < max(py0, qy0):
                hits.append(px0 + (yy - py0) * (qx0 - px0) / (qy0 - py0))
        if len(hits) >= 2:
            for xx in range(int(min(hits)), int(max(hits)) + 1):
                px(xx, yy, c)


def blend(a, b, t):
    return (int(a[0] + (b[0] - a[0]) * t),
            int(a[1] + (b[1] - a[1]) * t),
            int(a[2] + (b[2] - a[2]) * t))


# --- letterforms ---------------------------------------------------------
# One 35-character string per glyph: seven rows of five bits, row-major.
GLYPHS = {
    "A": "01110100011000111111100011000110001",
    "B": "11110100011000111110100011000111110",
    "C": "01110100011000010000100001000101110",
    "D": "11110100011000110001100011000111110",
    "E": "11111100001000011110100001000011111",
    "F": "11111100001000011110100001000010000",
    "G": "01110100011000010111100011000101111",
    "H": "10001100011000111111100011000110001",
    "I": "01110001000010000100001000010001110",
    "J": "00111000100001000010000101001001100",
    "K": "10001100101010011000101001001010001",
    "L": "10000100001000010000100001000011111",
    "M": "10001110111010110101100011000110001",
    "N": "10001110011010110011100011000110001",
    "O": "01110100011000110001100011000101110",
    "P": "11110100011000111110100001000010000",
    "Q": "01110100011000110001101011001001101",
    "R": "11110100011000111110101001001010001",
    "S": "01111100001000001110000010000111110",
    "T": "11111001000010000100001000010000100",
    "U": "10001100011000110001100011000101110",
    "V": "10001100011000110001100010101000100",
    "W": "10001100011000110101101011101110001",
    "X": "10001100010101000100010101000110001",
    "Y": "10001100010101000100001000010000100",
    "Z": "11111000010001000100010001000011111",
    "0": "01110100011001110101110011000101110",
    "1": "00100011000010000100001000010001110",
    "2": "01110100010000100110010001000011111",
    "3": "11111000100010000010000011000101110",
    "4": "00010001100101010010111110001000010",
    "5": "11111100001111000001000011000101110",
    "6": "00110010001000011110100011000101110",
    "7": "11111000010001000100010001000010000",
    "8": "01110100011000101110100011000101110",
    "9": "01110100011000101111000010001001100",
    " ": "00000000000000000000000000000000000",
    ".": "00000000000000000000000001100011000",
    ",": "000000000000000000000011000010001000",
    "'": "00100001000100000000000000000000000",
    "&": "01100100101010001000101011001001101",
    "-": "00000000000000001110000000000000000",
    ":": "00000011000110000000011000110000000",
    "/": "00001000100001000100010001000010000",
    "(": "00010001000100001000010000010000010",
    ")": "01000001000001000010000100010001000",
    "%": "11001110100001000100010000101110011",
    "$": "00100011111010001110001011111000100",
    "!": "00100001000010000100001000000000100",
    "?": "01110100010000100110001000000000100",
    "+": "00000001000010001110001000010000000",
    "=": "00000000001111100000111110000000000",
    "*": "00000101010111010101000000000000000",
}


def glyph_width(text, scale):
    return len(text) * 6 * scale - scale


def put_text(x, y, text, scale, c):
    """Stamp upper-case text; returns the x just past the last glyph."""
    cx = x
    for ch in text.upper():
        bits = GLYPHS.get(ch, GLYPHS[" "])
        for row in range(7):
            for col in range(5):
                if bits[row * 5 + col] == "1":
                    rect(cx + col * scale, y + row * scale,
                         scale, scale, c)
        cx += 6 * scale
    return cx


def put_centred(cx, y, text, scale, c):
    put_text(cx - glyph_width(text, scale) // 2, y, text, scale, c)


def wrap(text, scale, max_w):
    """Greedy wrap into lines no wider than max_w pixels."""
    out = []
    cur = ""
    for word in text.upper().split(" "):
        trial = word if not cur else cur + " " + word
        if glyph_width(trial, scale) <= max_w or not cur:
            cur = trial
        else:
            out.append(cur)
            cur = word
    if cur:
        out.append(cur)
    return out


# --- png -----------------------------------------------------------------
def png_chunk(kind, payload):
    head = struct.pack(">I", len(payload)) + kind + payload
    tail = struct.pack(">I", binascii.crc32(kind + payload) & 0xFFFFFFFF)
    return head + tail


def save_png(path):
    body = bytearray()
    for yy in range(SIDE):
        body.append(0)
        body += sheet[yy * SIDE * 3:(yy + 1) * SIDE * 3]
    header = struct.pack(">IIBBBBB", SIDE, SIDE, 8, 2, 0, 0, 0)
    blob = b"\x89PNG\r\n\x1a\n"
    blob += png_chunk(b"IHDR", header)
    blob += png_chunk(b"IDAT", zlib.compress(bytes(body), 9))
    blob += png_chunk(b"IEND", b"")
    with open(path, "wb") as fh:
        fh.write(blob)
    return len(blob)


# --- story icons -----------------------------------------------------------
def pic_rubble(cx, top):
    # A shelled apartment block: broken roofline, cracked walls, rubble.
    rect(cx - 52, top + 14, 104, 66, WINE)
    tri(cx - 52, top + 14, cx - 10, top + 14, cx - 30, top - 6, WINE)
    tri(cx - 6, top + 14, cx + 30, top + 14, cx + 12, top - 2, WINE)
    for wx, wy in ((-40, 26), (-8, 26), (24, 26), (-40, 52), (24, 52)):
        rect(cx + wx, top + wy, 16, 12, NAVDEEP)
    seg(cx - 4, top + 14, cx + 8, top + 44, SOOT, 2)
    seg(cx + 8, top + 44, cx - 2, top + 66, SOOT, 2)
    tri(cx - 56, top + 80, cx - 30, top + 80, cx - 44, top + 64, ASH)
    tri(cx - 28, top + 80, cx + 4, top + 80, cx - 12, top + 66, SOOT)
    tri(cx + 6, top + 80, cx + 38, top + 80, cx + 22, top + 68, ASH)


def pic_shield(cx, top):
    # Air-defence shield carrying a check mark.
    rect(cx - 52, top + 8, 104, 26, SEA)
    tri(cx - 52, top + 8, cx + 52, top + 8, cx, top + 88, SEA)
    rect(cx - 34, top + 10, 68, 18, SNOW)
    tri(cx - 34, top + 10, cx + 34, top + 10, cx, top + 72, SNOW)
    seg(cx - 22, top + 40, cx - 6, top + 56, SEA, 5)
    seg(cx - 6, top + 56, cx + 26, top + 22, SEA, 5)


def pic_clock(cx, top):
    # A clock face: the decision is put off.
    ring(cx, top + 44, 42, NAV, 4)
    disc(cx, top + 44, 4, NAV)
    seg(cx, top + 44, cx, top + 14, NAV, 4)
    seg(cx, top + 44, cx + 26, top + 58, NAV, 4)
    for deg in (0, 90, 180, 270):
        rad = math.radians(deg)
        mx = int(cx + 34 * math.cos(rad))
        my = int(top + 44 + 34 * math.sin(rad))
        rect(mx - 2, my - 2, 4, 4, NAV)


def pic_ballot(cx, top):
    # A ballot box, a paper sliding in, a big check on its face.
    rect(cx - 14, top + 6, 28, 30, SNOW)
    vbar(cx - 14, top + 6, top + 36, SOOT, 2)
    vbar(cx + 14, top + 6, top + 36, SOOT, 2)
    hbar(cx - 14, cx + 14, top + 6, SOOT, 2)
    rect(cx - 48, top + 34, 96, 48, LEAF)
    rect(cx - 48, top + 34, 96, 8, (20, 90, 38))
    seg(cx - 30, top + 56, cx - 12, top + 72, SNOW, 5)
    seg(cx - 12, top + 72, cx + 30, top + 42, SNOW, 5)


def pic_compass(cx, top):
    # A four-point compass star in a ring.
    tri(cx, top + 2, cx - 12, top + 44, cx + 12, top + 44, AURUM)
    tri(cx, top + 86, cx - 12, top + 44, cx + 12, top + 44, AURUM)
    tri(cx - 42, top + 44, cx, top + 32, cx, top + 56, AURUM)
    tri(cx + 42, top + 44, cx, top + 32, cx, top + 56, AURUM)
    ring(cx, top + 44, 34, NAV, 3)
    disc(cx, top + 44, 8, NAV)


def pic_flags(cx, top):
    # USA, China and Russia on poles above a rule.
    fw, fh, gap = 34, 22, 6
    start = cx - (3 * fw + 2 * gap) // 2
    x = start
    for s in range(5):
        rect(x, top + s * 4, fw, 4,
             (178, 34, 52) if s % 2 == 0 else SNOW)
    rect(x, top, 15, 10, (60, 59, 110))
    x += fw + gap
    rect(x, top, fw, fh, (222, 41, 16))
    disc(x + 8, top + 8, 3, AURUM_LT)
    x += fw + gap
    rect(x, top, fw, 7, SNOW)
    rect(x, top + 7, fw, 7, (0, 57, 166))
    rect(x, top + 15, fw, 7, (213, 0, 50))
    for pole in (start, start + fw + gap, start + 2 * (fw + gap)):
        vbar(pole, top, top + fh + 44, SOOT, 2)
    hbar(cx - 52, cx + 52, top + 76, NAV, 4)


PICS = {
    "rubble": pic_rubble,
    "shield": pic_shield,
    "clock": pic_clock,
    "ballot": pic_ballot,
    "compass": pic_compass,
    "flags": pic_flags,
}


def paint_card(x, y, accent, label, pic, headline, sub):
    """One 330x280 story card: label bar, icon, headline, sub-headline."""
    w, h = 330, 280
    rect(x, y, w, h, SNOW)
    hbar(x, x + w - 1, y, EDGE, 2)
    hbar(x, x + w - 1, y + h - 1, EDGE, 2)
    vbar(x, y, y + h - 1, EDGE, 2)
    vbar(x + w - 1, y, y + h - 1, EDGE, 2)
    rect(x + 2, y + 2, w - 4, 22, accent)
    put_text(x + 12, y + 7, label, 2, SNOW)
    PICS[pic](x + w // 2, y + 30)
    hy = y + 140
    for ln in wrap(headline, 3, w - 24)[:2]:
        put_text(x + 12, hy, ln, 3, SOOT)
        hy += 26
    sy = y + 196
    for ln in wrap(sub, 2, w - 24)[:2]:
        put_text(x + 12, sy, ln, 2, ASH)
        sy += 17


# --- lead story ------------------------------------------------------------
def paint_lead():
    # Night sky, deep navy melting into purple.
    for yy in range(108, 270):
        t = (yy - 108) / 162.0
        rect(0, yy, SIDE, 1, blend(NIGHTSKY, (74, 44, 110), t))
    # Fixed stars.
    for i in range(70):
        sx = 12 + (i * 97 + 31) % 1000
        sy = 112 + (i * 53 + 17) % 140
        rect(sx, sy, 2, 2, SNOW if i % 4 else AURUM_LT)
    # Three missile trails streaking down from the upper right.
    for (mx, my, mlen) in ((880, 128, 190), (760, 148, 150), (640, 122, 120)):
        seg(mx, my, mx - mlen, my + 62, (255, 200, 120), 3)
        seg(mx, my, mx - mlen, my + 62, SNOW, 1)
        disc(mx, my, 7, FLAME)
        disc(mx, my, 4, FLAME_HOT)
    # Skyline silhouette with lit windows.
    heights = [52, 78, 60, 90, 68, 104, 56, 82, 64, 96, 50, 86, 62, 72,
               98, 54, 80, 66, 92, 58, 74, 52, 84, 60]
    x = 8
    i = 0
    while x < SIDE - 8 and i < len(heights):
        bw = 36 if i % 3 else 44
        bh = heights[i]
        top_y = 270 - bh
        rect(x, top_y, bw, bh, DUSK)
        for wy in range(top_y + 8, 266, 12):
            for wx in range(x + 5, x + bw - 5, 10):
                if (wx * 7 + wy * 13 + i * 5) % 4 == 0:
                    rect(wx, wy, 3, 4, AURUM_LT)
        x += bw + 4
        i += 1
    # Navy ribbon carrying the lead headline.
    rect(0, 270, SIDE, 122, NAV)
    rect(0, 270, SIDE, 3, AURUM)
    put_centred(512, 284, "RUSSIAN MISSILES LAND IN POLAND", 5, SNOW)
    put_centred(512, 330, "TUSK: DELIBERATE PROVOCATION", 5, AURUM)
    put_centred(512, 374,
                "NATO CALLS IT A GRAVE VIOLATION - JETS SCRAMBLED",
                2, (220, 220, 220))


# --- the page ---------------------------------------------------------------
def paint_page():
    rect(0, 0, SIDE, SIDE, BG)
    # Masthead.
    rect(0, 0, SIDE, 104, NAV)
    put_centred(512, 20, "THE WORLD IN ONE PAGE", 5, SNOW)
    put_centred(512, 64, "SATURDAY 21 NOVEMBER 2026", 3, AURUM)
    rect(0, 104, SIDE, 4, AURUM)
    paint_lead()
    # Six stories, two rows of three.
    stories = [
        (WINE, "UKRAINE", "rubble",
         "DOUBLE-TAP KILLS TWO IN KRYVYI RIH",
         "A BOY, 7, AND A PARAMEDIC DEAD, 42 HURT"),
        (SEA, "MIDDLE EAST", "shield",
         "RIYADH DOWNS 3 HOUTHI MISSILES",
         "THIRD NIGHT OF ALERTS IN THE CAPITAL"),
        (NAV, "USA", "clock",
         "TRUMP DELAYS IRAN STRIKE CALL",
         "NO DECISION ON NEW STRIKES UNTIL NEXT YEAR"),
        (LEAF, "LATIN AMERICA", "ballot",
         "BUKELE SEEKS THIRD TERM",
         "EL SALVADOR PRESIDENT EYES RULE TO 2033"),
        (AURUM, "NATO", "compass",
         "JETS SCRAMBLED, RUTTE TO WARSAW",
         "ALLIANCE STANDS WITH POLAND"),
        (GRAPE, "SUMMIT", "flags",
         "TRUMP-XI-PUTIN: NO BREAKTHROUGH",
         "HISTORY MADE IN SHENZHEN, WAR UNMOVED"),
    ]
    xs = (8, 346, 684)
    ys = (400, 688)
    for i, (accent, label, pic, headline, sub) in enumerate(stories):
        paint_card(xs[i % 3], ys[i // 3], accent, label, pic, headline, sub)
    # Also-today strip.
    rect(8, 974, 1008, 22, NAV)
    put_text(16, 979,
             "ALSO TODAY: EU APPROVES 1BN EUROS MORE MILITARY AID FOR UKRAINE",
             2, SNOW)
    # Footer.
    put_centred(512, 1004,
                "COMPILED FROM AP, REUTERS, THE TIMES - 21 NOVEMBER 2026",
                2, ASH)


def entry():
    paint_page()
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "entry.png")
    size = save_png(path)
    print(f"wrote {path} {SIDE}x{SIDE} {size} bytes")


if __name__ == "__main__":
    entry()
