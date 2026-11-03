"""Build project-image.png (1600x900) for the AI-collusion audit briefing.

All drawing is local vector-style raster at 2x supersampling; no diffusion API.
The schematic encodes: four agents, one shared public cue, one private message,
and the auditor's question. It is labelled a concept schematic, not a result.
"""
import os
from PIL import Image, ImageDraw, ImageFont

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "project-image.png")
W, H = 1600, 900
S = 2  # supersample factor

FONTS = r"C:/Windows/Fonts"
GEORGIA_B = os.path.join(FONTS, "georgiab.ttf")
GEORGIA_I = os.path.join(FONTS, "georgiai.ttf")
SEGOE = os.path.join(FONTS, "segoeui.ttf")
SEGOE_B = os.path.join(FONTS, "segoeuib.ttf")

CRIMSON = (160, 24, 44)
CRIMSON_DARK = (110, 17, 32)
CRIMSON_SOFT = (198, 96, 112)
CHARCOAL = (34, 36, 41)
INK = (58, 60, 66)
GRAY = (108, 108, 112)
OFFWHITE = (248, 244, 236)
PANEL = (255, 253, 249)
LINE = (222, 213, 200)

img = Image.new("RGB", (W * S, H * S), OFFWHITE)
d = ImageDraw.Draw(img)


def f(path, size):
    return ImageFont.truetype(path, int(size * S))


def tw(text, font):
    return d.textlength(text, font=font) / S


def text(x, y, s, font, fill, tracking=0.0, anchor="la"):
    """Draw text with optional letter-spacing, coordinates in 1600x900 units."""
    if tracking <= 0:
        d.text((x * S, y * S), s, font=font, fill=fill, anchor=anchor)
        return
    cx = x * S
    for ch in s:
        d.text((cx, y * S), ch, font=font, fill=fill, anchor="ls" if anchor == "ls" else "la")
        cx += d.textlength(ch, font=font) + tracking * S


def wrap(s, font, maxw):
    words, lines, cur = s.split(), [], ""
    for w_ in words:
        t = (cur + " " + w_).strip()
        if tw(t, font) <= maxw:
            cur = t
        else:
            if cur:
                lines.append(cur)
            cur = w_
    if cur:
        lines.append(cur)
    return lines


def rrect(box, r, fill=None, outline=None, width=2):
    x0, y0, x1, y1 = [v * S for v in box]
    d.rounded_rectangle([x0, y0, x1, y1], radius=r * S, fill=fill,
                        outline=outline, width=int(width * S))


def dashed(p0, p1, fill, width=2, dash=9, gap=7):
    import math
    x0, y0 = p0
    x1, y1 = p1
    dist = math.hypot(x1 - x0, y1 - y0)
    if dist == 0:
        return
    ux, uy = (x1 - x0) / dist, (y1 - y0) / dist
    t = 0.0
    while t < dist:
        e = min(t + dash, dist)
        d.line([((x0 + ux * t) * S, (y0 + uy * t) * S),
                ((x0 + ux * e) * S, (y0 + uy * e) * S)],
               fill=fill, width=int(width * S))
        t = e + gap


def arrow(p0, p1, fill, width=3, head=13):
    import math
    d.line([(p0[0] * S, p0[1] * S), (p1[0] * S, p1[1] * S)], fill=fill, width=int(width * S))
    ang = math.atan2(p1[1] - p0[1], p1[0] - p0[0])
    for sgn in (0.45, -0.45):
        d.line([(p1[0] * S, p1[1] * S),
                ((p1[0] - head * math.cos(ang + sgn)) * S,
                 (p1[1] - head * math.sin(ang + sgn)) * S)],
               fill=fill, width=int(width * S))


def check_width(s, font, maxw, label):
    got = tw(s, font)
    assert got <= maxw, f"overflow {label}: {got:.1f}px > {maxw:.1f}px :: {s[:40]}"
    return got


# ---------------------------------------------------------------- header
d.rectangle([80 * S, 66 * S, 86 * S, 112 * S], fill=CRIMSON)
text(104, 64, "RESEARCH BRIEFING  ·  CONCEPT SCHEMATIC", f(SEGOE_B, 17), CRIMSON, tracking=2.6)
check_width("RESEARCH BRIEFING  ·  CONCEPT SCHEMATIC", f(SEGOE_B, 17), 700, "eyebrow")

title = "Auditing AI Coordination"
text(78, 100, title, f(GEORGIA_B, 76), CHARCOAL)
check_width(title, f(GEORGIA_B, 76), 1440, "title")

sub = ("Four agents, one shared cue, one private message \u2014 "
       "and a score that cannot tell them apart.")
fs = f(SEGOE, 27)
sub_lines = wrap(sub, fs, 1430)
assert len(sub_lines) == 1, sub_lines
text(80, 206, sub_lines[0], fs, INK)
check_width(sub_lines[0], fs, 1430, "subtitle")

# ---------------------------------------------------------------- panels
rrect((80, 258, 770, 648), 18, fill=PANEL, outline=LINE, width=2)
rrect((830, 258, 1520, 648), 18, fill=PANEL, outline=LINE, width=2)

fh = f(SEGOE_B, 17)
text(116, 288, "CAUSE 1  ·  SHARED PUBLIC CUE", fh, CRIMSON, tracking=2.2)
text(866, 288, "CAUSE 2  ·  PRIVATE MESSAGE", fh, CRIMSON, tracking=2.2)

# cue pill
rrect((300, 330, 550, 410), 10, fill=CHARCOAL)
text(425, 344, "PUBLIC CUE: ROCK", f(SEGOE_B, 23), OFFWHITE, anchor="ma")
text(425, 380, "shown to all four", f(SEGOE, 14), (198, 192, 180), anchor="ma")

AX = [230, 360, 490, 620]
for i, x in enumerate(AX):
    dashed((425, 412), (x, 484), CRIMSON_SOFT, width=2, dash=8, gap=7)
    d.ellipse([(x - 34) * S, (486 - 34) * S, (x + 34) * S, (486 + 34) * S],
              fill=PANEL, outline=CHARCOAL, width=int(2.4 * S))
    text(x, 486, "ABCD"[i], f(GEORGIA_B, 28), CHARCOAL, anchor="mm")

cap = f(SEGOE, 18)
text(120, 560, "All four see it. Two are told to follow it.", cap, INK)
text(120, 594, "No message passes between them.", cap, GRAY)

# right panel agents
BX = [980, 1110, 1240, 1370]
for i, x in enumerate(BX):
    a_fill = PANEL if i < 2 else (238, 234, 226)
    d.ellipse([(x - 34) * S, (486 - 34) * S, (x + 34) * S, (486 + 34) * S],
              fill=a_fill, outline=CHARCOAL if i < 2 else GRAY, width=int(2.4 * S))
    text(x, 486, "ABCD"[i], f(GEORGIA_B, 28), CHARCOAL if i < 2 else GRAY, anchor="mm")

# private message arc A -> B
import math
cx0, cy0, cx1, cy1 = BX[0], 452, BX[1], 452
pts = []
for k in range(41):
    t = k / 40
    x = cx0 + (cx1 - cx0) * t
    y = 452 - math.sin(math.pi * t) * 46
    pts.append((x * S, y * S))
d.line(pts, fill=CRIMSON, width=int(3.2 * S), joint="curve")
arrow((pts[-2][0] / S, pts[-2][1] / S), (cx1, 452), CRIMSON, width=3.2, head=14)
text((cx0 + cx1) / 2, 366, "\u201cplay ROCK\u201d", f(GEORGIA_I, 21), CRIMSON, anchor="ma")

text(866, 560, "One agent receives the target. One acts on it.", cap, INK)
text(866, 594, "The auditor never sees the message.", cap, GRAY)

# small role tags
text(120, 620, "DESIGNATED PAIR", f(SEGOE_B, 13), CRIMSON, tracking=1.6)
text(866, 620, "SEEDED CHANNEL", f(SEGOE_B, 13), CRIMSON, tracking=1.6)

# ---------------------------------------------------------------- auditor band
rrect((80, 676, 1520, 800), 14, fill=CHARCOAL)
text(120, 698, "THE AUDITOR'S VIEW", f(SEGOE_B, 15), CRIMSON_SOFT, tracking=2.4)
text(120, 726, "Four action columns and the recorded cue.", f(SEGOE, 22), OFFWHITE)
text(120, 758, "Messages, reasoning, recommendations and payoffs are hidden.", f(SEGOE, 18), (198, 192, 180))
d.line([(860 * S, 700 * S), (860 * S, 776 * S)], fill=(80, 82, 88), width=int(2 * S))
text(900, 698, "THE QUESTION", f(SEGOE_B, 15), CRIMSON_SOFT, tracking=2.4)
text(900, 724, "Which cause produced this dependence?", f(GEORGIA_I, 26), OFFWHITE)

foot = ("Schematic only \u2014 not an experimental graph. Quantitative claims in the "
        "accompanying deck are cited to the manuscript.")
text(80, 834, foot, f(SEGOE, 15), GRAY)
assert tw(foot, f(SEGOE, 15)) <= 1440

img = img.resize((W, H), Image.LANCZOS)
img.save(OUT, "PNG", optimize=True)
print("saved", OUT, img.size, os.path.getsize(OUT))
