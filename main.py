#!/usr/bin/env python3
"""The World in One Page - 21 November 2026.

Draws a one-page newspaper front page summing up the world's news of
Saturday 21 November 2026 as a 1024x1024 PNG, pixel by pixel, using only
the Python standard library. No network access, fully deterministic:
two runs write byte-identical files.

Run:  MAKEFUN_OUTPUT_DIR=out python3 main.py   (writes out/entry.png)
"""

import binascii
import math
import os
import struct
import zlib

W = 1024
H = 1024

# ---------------------------------------------------------------- palette
PAPER = (246, 241, 231)
NAVY = (22, 35, 63)
NAVY_DARK = (13, 22, 42)
NIGHT = (16, 24, 54)
GOLD = (217, 164, 65)
GOLD_LIGHT = (240, 196, 90)
WHITE = (255, 255, 255)
INK = (26, 26, 26)
GREY = (74, 68, 56)
BORDER = (201, 191, 169)
RED_DARK = (122, 31, 31)
TEAL = (14, 90, 122)
GREEN = (30, 122, 52)
BURNT = (179, 84, 30)
PURPLE = (106, 31, 160)
SKY_DARK = (24, 28, 66)
FLAME = (255, 140, 0)
FLAME_CORE = (255, 220, 60)

# ---------------------------------------------------------------- canvas
canvas = bytearray(W * H * 3)


def set_px(x, y, color):
    if 0 <= x < W and 0 <= y < H:
        i = (y * W + x) * 3
        canvas[i] = color[0]
        canvas[i + 1] = color[1]
        canvas[i + 2] = color[2]


def fill_rect(x, y, w, h, color):
    if w <= 0 or h <= 0:
        return
    x0 = max(0, x)
    y0 = max(0, y)
    x1 = min(W, x + w)
    y1 = min(H, y + h)
    if x0 >= x1 or y0 >= y1:
        return
    row = bytes(color) * (x1 - x0)
    for yy in range(y0, y1):
        i = (yy * W + x0) * 3
        canvas[i:i + len(row)] = row


def hline(x0, x1, y, color, thick=1):
    for t in range(thick):
        for x in range(x0, x1 + 1):
            set_px(x, y + t, color)


def vline(x, y0, y1, color, thick=1):
    for t in range(thick):
        for y in range(y0, y1 + 1):
            set_px(x + t, y, color)


def line(x0, y0, x1, y1, color, thick=1):
    dx = abs(x1 - x0)
    dy = -abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx + dy
    x, y = x0, y0
    while True:
        for a in range(thick):
            for b in range(thick):
                set_px(x + a, y + b, color)
        if x == x1 and y == y1:
            break
        e2 = 2 * err
        if e2 >= dy:
            err += dy
            x += sx
        if e2 <= dx:
            err += dx
            y += sy


def fill_circle(cx, cy, r, color):
    for dy in range(-r, r + 1):
        dx = int(math.sqrt(max(0, r * r - dy * dy)))
        for x in range(cx - dx, cx + dx + 1):
            set_px(x, cy + dy, color)


def circle_outline(cx, cy, r, color, thick=2):
    for a in range(360):
        rad = math.radians(a)
        for t in range(thick):
            set_px(int(cx + (r + t) * math.cos(rad)),
                   int(cy + (r + t) * math.sin(rad)), color)


def fill_triangle(x0, y0, x1, y1, x2, y2, color):
    ymin = min(y0, y1, y2)
    ymax = max(y0, y1, y2)
    for y in range(ymin, ymax + 1):
        xs = []
        for (ax, ay, bx, by) in ((x0, y0, x1, y1), (x1, y1, x2, y2),
                                 (x2, y2, x0, y0)):
            if ay == by:
                continue
            if (y >= min(ay, by)) and (y < max(ay, by)):
                xs.append(ax + (y - ay) * (bx - ax) / (by - ay))
        if len(xs) >= 2:
            for x in range(int(min(xs)), int(max(xs)) + 1):
                set_px(x, y, color)


def lerp(c1, c2, t):
    return (int(c1[0] + (c2[0] - c1[0]) * t),
            int(c1[1] + (c2[1] - c1[1]) * t),
            int(c1[2] + (c2[2] - c1[2]) * t))


# ---------------------------------------------------------------- 5x7 font
# Each glyph: 7 rows of 5 bits, "1" = ink.
FONT = {
    "A": ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    "B": ("11110", "10001", "10001", "11110", "10001", "10001", "11110"),
    "C": ("01110", "10001", "10000", "10000", "10000", "10001", "01110"),
    "D": ("11110", "10001", "10001", "10001", "10001", "10001", "11110"),
    "E": ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    "F": ("11111", "10000", "10000", "11110", "10000", "10000", "10000"),
    "G": ("01110", "10001", "10000", "10111", "10001", "10001", "01111"),
    "H": ("10001", "10001", "10001", "11111", "10001", "10001", "10001"),
    "I": ("01110", "00100", "00100", "00100", "00100", "00100", "01110"),
    "J": ("00111", "00010", "00010", "00010", "00010", "10010", "01100"),
    "K": ("10001", "10010", "10100", "11000", "10100", "10010", "10001"),
    "L": ("10000", "10000", "10000", "10000", "10000", "10000", "11111"),
    "M": ("10001", "11011", "10101", "10101", "10001", "10001", "10001"),
    "N": ("10001", "11001", "10101", "10011", "10001", "10001", "10001"),
    "O": ("01110", "10001", "10001", "10001", "10001", "10001", "01110"),
    "P": ("11110", "10001", "10001", "11110", "10000", "10000", "10000"),
    "Q": ("01110", "10001", "10001", "10001", "10101", "10010", "01101"),
    "R": ("11110", "10001", "10001", "11110", "10100", "10010", "10001"),
    "S": ("01111", "10000", "10000", "01110", "00001", "00001", "11110"),
    "T": ("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
    "U": ("10001", "10001", "10001", "10001", "10001", "10001", "01110"),
    "V": ("10001", "10001", "10001", "10001", "10001", "01010", "00100"),
    "W": ("10001", "10001", "10001", "10101", "10101", "11011", "10001"),
    "X": ("10001", "10001", "01010", "00100", "01010", "10001", "10001"),
    "Y": ("10001", "10001", "01010", "00100", "00100", "00100", "00100"),
    "Z": ("11111", "00001", "00010", "00100", "01000", "10000", "11111"),
    "0": ("01110", "10001", "10011", "10101", "11001", "10001", "01110"),
    "1": ("00100", "01100", "00100", "00100", "00100", "00100", "01110"),
    "2": ("01110", "10001", "00001", "00110", "01000", "10000", "11111"),
    "3": ("11111", "00010", "00100", "00010", "00001", "10001", "01110"),
    "4": ("00010", "00110", "01010", "10010", "11111", "00010", "00010"),
    "5": ("11111", "10000", "11110", "00001", "00001", "10001", "01110"),
    "6": ("00110", "01000", "10000", "11110", "10001", "10001", "01110"),
    "7": ("11111", "00001", "00010", "00100", "01000", "01000", "01000"),
    "8": ("01110", "10001", "10001", "01110", "10001", "10001", "01110"),
    "9": ("01110", "10001", "10001", "01111", "00001", "00010", "01100"),
    " ": ("00000", "00000", "00000", "00000", "00000", "00000", "00000"),
    ".": ("00000", "00000", "00000", "00000", "00000", "01100", "01100"),
    ",": ("00000", "00000", "00000", "00000", "01100", "00100", "01000"),
    "'": ("00100", "00100", "01000", "00000", "00000", "00000", "00000"),
    "&": ("01100", "10010", "10100", "01000", "10101", "10010", "01101"),
    "-": ("00000", "00000", "00000", "01110", "00000", "00000", "00000"),
    ":": ("00000", "01100", "01100", "00000", "01100", "01100", "00000"),
    "/": ("00001", "00010", "00010", "00100", "01000", "01000", "10000"),
    "(": ("00010", "00100", "01000", "01000", "01000", "00100", "00010"),
    ")": ("01000", "00100", "00010", "00010", "00010", "00100", "01000"),
    "%": ("11001", "11010", "00010", "00100", "01000", "01011", "10011"),
    "$": ("00100", "01111", "10100", "01110", "00101", "11110", "00100"),
    "!": ("00100", "00100", "00100", "00100", "00100", "00000", "00100"),
    "?": ("01110", "10001", "00001", "00110", "00100", "00000", "00100"),
    "+": ("00000", "00100", "00100", "01110", "00100", "00100", "00000"),
    "=": ("00000", "00000", "11111", "00000", "11111", "00000", "00000"),
    "*": ("00000", "10101", "01110", "10101", "00000", "00000", "00000"),
}


def text_width(text, scale):
    return len(text) * 6 * scale - scale


def draw_text(x, y, text, scale, color):
    text = text.upper()
    cx = x
    for ch in text:
        glyph = FONT.get(ch, FONT[" "])
        for row in range(7):
            bits = glyph[row]
            for col in range(5):
                if bits[col] == "1":
                    fill_rect(cx + col * scale, y + row * scale,
                              scale, scale, color)
        cx += 6 * scale
    return cx


def draw_text_centered(cx, y, text, scale, color):
    x = cx - text_width(text, scale) // 2
    draw_text(x, y, text, scale, color)


def wrap_text(text, scale, max_width):
    """Greedy word wrap; returns list of lines."""
    words = text.upper().split(" ")
    lines = []
    cur = ""
    for w in words:
        trial = w if not cur else cur + " " + w
        if text_width(trial, scale) <= max_width or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


# ---------------------------------------------------------------- PNG writer
def chunk(ctype, data):
    out = struct.pack(">I", len(data)) + ctype + data
    out += struct.pack(">I", binascii.crc32(ctype + data) & 0xFFFFFFFF)
    return out


def write_png(path):
    raw = bytearray()
    for y in range(H):
        raw.append(0)  # filter: none
        raw += canvas[y * W * 3:(y + 1) * W * 3]
    ihdr = struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0)
    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", ihdr)
    png += chunk(b"IDAT", zlib.compress(bytes(raw), 9))
    png += chunk(b"IEND", b"")
    with open(path, "wb") as f:
        f.write(png)
    return len(png)


# ---------------------------------------------------------------- card icons
def icon_rubble(cx, top):
    # A damaged apartment block: cracked walls, rubble at the base.
    c = RED_DARK
    fill_rect(cx - 52, top + 14, 104, 66, c)
    fill_triangle(cx - 52, top + 14, cx - 10, top + 14, cx - 30, top - 6, c)
    fill_triangle(cx - 6, top + 14, cx + 30, top + 14, cx + 12, top - 2, c)
    # Broken windows, dark.
    for wx, wy in ((-40, 26), (-8, 26), (24, 26), (-40, 52), (24, 52)):
        fill_rect(cx + wx, top + wy, 16, 12, NAVY_DARK)
    # Crack lines.
    line(cx - 4, top + 14, cx + 8, top + 44, INK, 2)
    line(cx + 8, top + 44, cx - 2, top + 66, INK, 2)
    # Rubble.
    fill_triangle(cx - 56, top + 80, cx - 30, top + 80, cx - 44, top + 64,
                  GREY)
    fill_triangle(cx - 28, top + 80, cx + 4, top + 80, cx - 12, top + 66,
                  INK)
    fill_triangle(cx + 6, top + 80, cx + 38, top + 80, cx + 22, top + 68,
                  GREY)


def icon_shield(cx, top):
    # A shield with a check mark: air defence.
    c = TEAL
    fill_triangle(cx - 52, top + 8, cx + 52, top + 8, cx, top + 88, c)
    fill_rect(cx - 52, top + 8, 104, 26, c)
    fill_triangle(cx - 34, top + 10, cx + 34, top + 10, cx, top + 72,
                  WHITE)
    fill_rect(cx - 34, top + 10, 68, 18, WHITE)
    line(cx - 22, top + 40, cx - 6, top + 56, TEAL, 5)
    line(cx - 6, top + 56, cx + 26, top + 22, TEAL, 5)


def icon_clock(cx, top):
    # A clock face: a decision postponed.
    c = NAVY
    circle_outline(cx, top + 44, 42, c, 4)
    fill_circle(cx, top + 44, 4, c)
    line(cx, top + 44, cx, top + 14, c, 4)
    line(cx, top + 44, cx + 26, top + 58, c, 4)
    for a in (0, 90, 180, 270):
        rad = math.radians(a)
        x = int(cx + 34 * math.cos(rad))
        y = int(top + 44 + 34 * math.sin(rad))
        fill_rect(x - 2, y - 2, 4, 4, c)


def icon_ballot(cx, top):
    # A ballot box with a paper going in.
    c = GREEN
    fill_rect(cx - 48, top + 34, 96, 48, c)
    fill_rect(cx - 48, top + 34, 96, 8, (20, 90, 38))
    fill_rect(cx - 14, top + 6, 28, 30, WHITE)
    line(cx - 14, top + 6, cx + 14, top + 6, INK, 2)
    line(cx - 14, top + 6, cx - 14, top + 36, INK, 2)
    line(cx + 14, top + 6, cx + 14, top + 36, INK, 2)
    # A big check on the box.
    line(cx - 30, top + 56, cx - 12, top + 72, WHITE, 5)
    line(cx - 12, top + 72, cx + 30, top + 42, WHITE, 5)


def icon_compass(cx, top):
    # A four-point compass star.
    c = GOLD
    fill_triangle(cx, top + 2, cx - 12, top + 44, cx + 12, top + 44, c)
    fill_triangle(cx, top + 86, cx - 12, top + 44, cx + 12, top + 44, c)
    fill_triangle(cx - 42, top + 44, cx, top + 32, cx, top + 56, c)
    fill_triangle(cx + 42, top + 44, cx, top + 32, cx, top + 56, c)
    fill_circle(cx, top + 44, 8, NAVY)
    circle_outline(cx, top + 44, 34, NAVY, 3)


def icon_flags(cx, top):
    # Three small flags: USA, China, Russia.
    fw, fh, gap = 34, 22, 6
    x = cx - (3 * fw + 2 * gap) // 2
    # USA
    for s in range(5):
        fill_rect(x, top + s * 4, fw, 4,
                  (178, 34, 52) if s % 2 == 0 else WHITE)
    fill_rect(x, top, 15, 10, (60, 59, 110))
    # China
    x += fw + gap
    fill_rect(x, top, fw, fh, (222, 41, 16))
    fill_circle(x + 8, top + 8, 3, GOLD_LIGHT)
    # Russia
    x += fw + gap
    fill_rect(x, top, fw, 7, WHITE)
    fill_rect(x, top + 7, fw, 7, (0, 57, 166))
    fill_rect(x, top + 15, fw, 7, (213, 0, 50))
    # Flag poles.
    for px in (cx - (3 * fw + 2 * gap) // 2,
               cx - (3 * fw + 2 * gap) // 2 + fw + gap,
               cx - (3 * fw + 2 * gap) // 2 + 2 * (fw + gap)):
        vline(px, top, top + fh + 44, INK, 2)
    # A handshake line under the flags.
    hline(cx - 52, cx + 52, top + 76, NAVY, 4)


ICONS = {
    "rubble": icon_rubble,
    "shield": icon_shield,
    "clock": icon_clock,
    "ballot": icon_ballot,
    "compass": icon_compass,
    "flags": icon_flags,
}


def draw_card(x, y, accent, label, icon, headline, sub):
    w, h = 330, 280
    fill_rect(x, y, w, h, WHITE)
    # Border.
    hline(x, x + w - 1, y, BORDER, 2)
    hline(x, x + w - 1, y + h - 1, BORDER, 2)
    vline(x, y, y + h - 1, BORDER, 2)
    vline(x + w - 1, y, y + h - 1, BORDER, 2)
    # Accent label bar.
    fill_rect(x + 2, y + 2, w - 4, 22, accent)
    draw_text(x + 12, y + 7, label, 2, WHITE)
    # Icon.
    top = y + 30
    ICONS[icon](x + w // 2, top)
    # Headline, up to two lines, scale 3.
    lines = wrap_text(headline, 3, w - 24)
    hy = y + 140
    for ln in lines[:2]:
        draw_text(x + 12, hy, ln, 3, INK)
        hy += 26
    # Sub-headline, up to two lines, scale 2.
    sub_lines = wrap_text(sub, 2, w - 24)
    sy = y + 196
    for ln in sub_lines[:2]:
        draw_text(x + 12, sy, ln, 2, GREY)
        sy += 17


# ---------------------------------------------------------------- lead panel
def draw_lead():
    # Night sky gradient, dark navy -> deep purple.
    top = NIGHT
    bot = (74, 44, 110)
    for y in range(108, 270):
        t = (y - 108) / 162.0
        fill_rect(0, y, W, 1, lerp(top, bot, t))
    # Stars, fixed positions.
    for i in range(70):
        sx = 12 + (i * 97 + 31) % 1000
        sy = 112 + (i * 53 + 17) % 140
        fill_rect(sx, sy, 2, 2, WHITE if i % 4 else GOLD_LIGHT)
    # Three missile trails streaking down from the upper right.
    for (mx, my, mlen) in ((880, 128, 190), (760, 148, 150), (640, 122, 120)):
        line(mx, my, mx - mlen, my + 62, (255, 200, 120), 3)
        line(mx, my, mx - mlen, my + 62, WHITE, 1)
        fill_circle(mx, my, 7, FLAME)
        fill_circle(mx, my, 4, FLAME_CORE)
    # City skyline silhouette along the base of the sky.
    heights = [52, 78, 60, 90, 68, 104, 56, 82, 64, 96, 50, 86, 62, 72,
               98, 54, 80, 66, 92, 58, 74, 52, 84, 60]
    x = 8
    i = 0
    while x < W - 8 and i < len(heights):
        bw = 36 if i % 3 else 44
        bh = heights[i]
        top_y = 270 - bh
        fill_rect(x, top_y, bw, bh, SKY_DARK)
        for wy in range(top_y + 8, 266, 12):
            for wx in range(x + 5, x + bw - 5, 10):
                if (wx * 7 + wy * 13 + i * 5) % 4 == 0:
                    fill_rect(wx, wy, 3, 4, GOLD_LIGHT)
        x += bw + 4
        i += 1
    # Navy ribbon with the lead headline.
    fill_rect(0, 270, W, 122, NAVY)
    fill_rect(0, 270, W, 3, GOLD)
    draw_text_centered(512, 284, "RUSSIAN MISSILES LAND IN POLAND", 5, WHITE)
    draw_text_centered(512, 330, "TUSK: DELIBERATE PROVOCATION", 5, GOLD)
    draw_text_centered(512, 374,
                       "NATO CALLS IT A GRAVE VIOLATION - JETS SCRAMBLED",
                       2, (220, 220, 220))


# ---------------------------------------------------------------- page
def draw_page():
    fill_rect(0, 0, W, H, PAPER)
    # Masthead.
    fill_rect(0, 0, W, 104, NAVY)
    draw_text_centered(512, 20, "THE WORLD IN ONE PAGE", 5, WHITE)
    draw_text_centered(512, 64, "SATURDAY 21 NOVEMBER 2026", 3, GOLD)
    fill_rect(0, 104, W, 4, GOLD)
    draw_lead()
    # Six story cards, 2 rows x 3 columns.
    cards = [
        (RED_DARK, "UKRAINE", "rubble",
         "DOUBLE-TAP KILLS TWO IN KRYVYI RIH",
         "A BOY, 7, AND A PARAMEDIC DEAD, 42 HURT"),
        (TEAL, "MIDDLE EAST", "shield",
         "RIYADH DOWNS 3 HOUTHI MISSILES",
         "THIRD NIGHT OF ALERTS IN THE CAPITAL"),
        (NAVY, "USA", "clock",
         "TRUMP DELAYS IRAN STRIKE CALL",
         "NO DECISION ON NEW STRIKES UNTIL NEXT YEAR"),
        (GREEN, "LATIN AMERICA", "ballot",
         "BUKELE SEEKS THIRD TERM",
         "EL SALVADOR PRESIDENT EYES RULE TO 2033"),
        (GOLD, "NATO", "compass",
         "JETS SCRAMBLED, RUTTE TO WARSAW",
         "ALLIANCE STANDS WITH POLAND"),
        (PURPLE, "SUMMIT", "flags",
         "TRUMP-XI-PUTIN: NO BREAKTHROUGH",
         "HISTORY MADE IN SHENZHEN, WAR UNMOVED"),
    ]
    xs = (8, 346, 684)
    ys = (400, 688)
    for i, (accent, label, icon, headline, sub) in enumerate(cards):
        draw_card(xs[i % 3], ys[i // 3], accent, label, icon, headline, sub)
    # Also-today strip.
    fill_rect(8, 974, 1008, 22, NAVY)
    draw_text(16, 979,
              "ALSO TODAY: EU APPROVES 1BN EUROS MORE MILITARY AID FOR UKRAINE",
              2, WHITE)
    # Footer.
    draw_text_centered(512, 1004,
                       "COMPILED FROM AP, REUTERS, THE TIMES - 21 NOVEMBER 2026",
                       2, GREY)


def main():
    draw_page()
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "entry.png")
    size = write_png(path)
    print(f"wrote {path} {W}x{H} {size} bytes")


if __name__ == "__main__":
    main()
