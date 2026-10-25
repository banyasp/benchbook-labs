"""Three figures for the observation write-up: how a reward is computed from a model's structured output.

House style comes from /home/claude/benchbook/fig/figs.py. Colors: blue = done by a judge model,
plain grey = done by code, amber = problems / misses (and the gold labels that feed in).
Run:  python3 ofigs.py     (writes o1-*, o2-*, o3-* .svg and .png next to this file, then runs a layout check)
"""
import json
import os
import sys

sys.path.insert(0, "/home/claude/benchbook/fig")
from figs import text, box, arrow, svg, INK, QUIET, LINE, FAINT, ACC, ACCF, HUM, HUMF  # noqa: E402
from PIL import ImageFont  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
W = 1000
BAND = "#F6F8FA"

# ---------------------------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------------------------
_FONT = {400: "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
         700: "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"}
_cache = {}


def tw(s, size, weight=400):
    """Rendered width of s in px (Liberation Sans, the house font)."""
    w = 700 if weight >= 600 else 400
    if w not in _cache:
        _cache[w] = ImageFont.truetype(_FONT[w], 100)
    return _cache[w].getlength(s) * size / 100


def head(title, sub):
    return [text(40, 42, title, 18, 700, INK), text(40, 66, sub, 14, 400, QUIET)]


def check(cx, cy, color=INK, s=1.0, w=2.3):
    """Vector check mark (Liberation Sans has no U+2713)."""
    return (f'<path d="M{cx-5*s:.1f} {cy+0.5*s:.1f}L{cx-1.5*s:.1f} {cy+4*s:.1f}L{cx+5.5*s:.1f} {cy-4.5*s:.1f}" '
            f'fill="none" stroke="{color}" stroke-width="{w}" stroke-linecap="round" stroke-linejoin="round"/>')


def cross(cx, cy, color=HUM, s=1.0, w=2.3):
    return (f'<path d="M{cx-4.5*s:.1f} {cy-4.5*s:.1f}L{cx+4.5*s:.1f} {cy+4.5*s:.1f}M{cx+4.5*s:.1f} {cy-4.5*s:.1f}L{cx-4.5*s:.1f} {cy+4.5*s:.1f}" '
            f'fill="none" stroke="{color}" stroke-width="{w}" stroke-linecap="round"/>')


def varrow(x, base, length=16, color=QUIET, both=False, w=1.5):
    """Small inline arrow drawn as a path (the font's arrow glyphs are tiny). base = text baseline."""
    cy = base - 4.8
    d = f"M{x:.1f} {cy:.1f}H{x+length:.1f}M{x+length-4.2:.1f} {cy-3.6:.1f}L{x+length:.1f} {cy:.1f}L{x+length-4.2:.1f} {cy+3.6:.1f}"
    if both:
        d += f"M{x+4.2:.1f} {cy-3.6:.1f}L{x:.1f} {cy:.1f}L{x+4.2:.1f} {cy+3.6:.1f}"
    return f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{w}" stroke-linecap="round" stroke-linejoin="round"/>'


def pair(x, y, a, b, both=False, size=14, fill=INK, gap=7, length=16, arrow_color=QUIET):
    """'a -> b' (or 'a <-> b') with a drawn arrow; returns (elements, right edge)."""
    out = [text(x, y, a, size, 400, fill)]
    ax = x + tw(a, size) + gap
    out.append(varrow(ax, y, length, arrow_color, both))
    bx = ax + length + gap
    out.append(text(bx, y, b, size, 400, fill))
    return out, bx + tw(b, size)


def tag(x, y, label="×2", w=28, h=20):
    """Small weight tag; (x, y) is its top-left corner."""
    return (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{h/2}" fill="{BAND}" stroke="{LINE}" stroke-width="1.2"/>'
            + text(x + w / 2, y + h - 5.5, label, 12, 700, INK, "middle"))


def swatch(x, y, kind, w=22, h=14):
    stroke, fill, sw = {"accent": (ACC, ACCF, 2.0), "plain": (LINE, "#FFFFFF", 1.3), "human": (HUM, HUMF, 2.0)}[kind]
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="3.5" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>'


def caption(x, y, lines, size=13):
    return "\n".join(text(x, y + i * 17, ln, size, 400, QUIET, italic=True) for i, ln in enumerate(lines))


def dashed(d, color=HUM):
    return arrow(d, color, dash="6 5", w=1.8)


figs = {}

# =============================================================================================
# O1  From a generation to a reward
# =============================================================================================
b = head("From a generation to a reward", "The judge only aligns; code does every check and every score.")

AY, AH = 96, 122            # row A
BY, BH = 304, 104           # row B
GY, GH = 470, 104           # gold
mid = AY + AH / 2

# row A: start node, 1 Parse, 2 Gate, 3 Align
cx_, cw = 40, 124
px_, pw = 193, 232
gx_, gw = 454, 176
ax_, aw = 658, 262
b.append(box(cx_, mid - 48, cw, 96, "Completion", ["YAML reply +", "tool calls"], kind="band"))
b.append(box(px_, AY, pw, AH, "1 Parse", ["strip thinking; read fenced YAML", "read the tool calls"]))
b.append(box(gx_, AY, gw, AH, "2 Gate", ["well formed; ids exist", "each item in one bucket", "says what it does"]))
b.append(box(ax_, AY, aw, AH, "3 Align", [], kind="accent"))
b.append(f'<rect x="{ax_+aw-70}" y="{AY+10}" width="58" height="24" rx="12" fill="#FFFFFF" stroke="{ACC}" stroke-width="1.3"/>'
         + text(ax_ + aw - 41, AY + 26.5, "judge", 13, 600, INK, "middle"))
ly = AY + 47
for ln, indent in [("facts: judge P(same) for each pair,", 0), ("then a one-to-one match", 14),
                   ("options: tool order", 0), ("considerations: equity + cited facts", 0)]:
    b.append(text(ax_ + 14 + indent, ly, ln, 14, 400, INK)); ly += 19
for x0, x1 in [(cx_ + cw, px_), (px_ + pw, gx_), (gx_ + gw, ax_)]:
    b.append(arrow(f"M{x0} {mid}H{x1}"))
# captions (output of each stage)
b.append(caption(px_, AY + AH + 20, ["output: reply sections, tool calls"]))
b.append(caption(gx_, AY + AH + 20, ["output: pass, or −3", "(no judge calls)"]))
b.append(caption(ax_, AY + AH + 20, ["output: dictionaries:", "model id → gold id"]))

# row B: 4 Translate, 5 Score, 6 Combine
tx_, tw_ = 40, 232
sx_, sw_ = 306, 232
kx_, kw_ = 572, 190
b.append(box(tx_, BY, tw_, BH, "4 Translate", ["rewrite the model's mappings", "and verdict in gold ids"]))
b.append(box(sx_, BY, sw_, BH, "5 Score", ["precision, recall, F1", "mapping accuracy, relation,", "action, invariance, calibration"]))
b.append(box(kx_, BY, kw_, BH, "6 Combine", ["branch formula", "and tier bands"]))
b.append(arrow(f"M{tx_+tw_} {BY+BH/2}H{sx_}"))
b.append(arrow(f"M{sx_+sw_} {BY+BH/2}H{kx_}"))
b.append(caption(tx_, BY + BH + 20, ["output: mappings in gold ids"]))
b.append(caption(sx_, BY + BH + 20, ["output: sub-scores in [0, 1]"]))
b.append(caption(kx_, BY + BH + 20, ["output: reward"]))

# wrap arrow: stage 3 down and back to stage 4
wrap_x = ax_ + aw - 90      # 830
wrap_y = 276
b.append(arrow(f"M{wrap_x} {AY+AH}V{wrap_y}H{tx_+tw_/2}V{BY}"))

# gold box and its dashed feeds
gold_x, gold_w = 680, 240
b.append(box(gold_x, GY, gold_w, GH, "Gold", ["from the gold reply:", "facts, considerations, mappings,", "options, verdict, signatures"], kind="human"))
b.append(dashed(f"M{ax_+aw-25} {GY}V{AY+AH}"))                        # into stage 3 (Align)
b.append(dashed(f"M{gold_x} {GY+GH/2}H{sx_+sw_-26}V{BY+BH}"))          # into stage 5 (Score)

# legend
lx, lyy = 40, GY + GH - 14
b.append(swatch(lx, lyy - 11, "accent")); b.append(text(lx + 30, lyy, "judge model", 13, 400, QUIET))
lx2 = lx + 30 + tw("judge model", 13) + 26
b.append(swatch(lx2, lyy - 11, "plain")); b.append(text(lx2 + 30, lyy, "code", 13, 400, QUIET))
lx3 = lx2 + 30 + tw("code", 13) + 26
b.append(swatch(lx3, lyy - 11, "human")); b.append(text(lx3 + 30, lyy, "gold labels (dashed arrows)", 13, 400, QUIET))

figs["o1-pipeline"] = svg(W, GY + GH + 26, "\n".join(b))

# =============================================================================================
# O2  Aligning facts
# =============================================================================================
ex = json.load(open(os.path.join(HERE, "..", "example_v7.json")))
P = ex["P"]
GOLD_LAB = ["collection on an armed group", "acts only through tools", "duty-to-warn procedure", "liaison agreement",
            "plan: kill journalist 0700", "plan assessed credible", "warning exposes channel", "partner needs ~48 h",
            "no one else aware", "access regained in months", "no human source"]
DOUBLE = {4, 5, 7, 8}                                  # F5, F6, F8, F9 support the decisive consideration
MATCHES = [(0, 7), (1, 6), (2, 5), (4, 0), (5, 1), (6, 2), (7, 3), (9, 4)]
# the matches must agree with the dictionary computed by the prototype
assert {f"M{j+1}": f"LIVE-F{i+1}" for i, j in MATCHES} == ex["facts"]["dictionary"]
assert [f"{ex['facts'][k]:.2f}" for k in ("recall", "precision", "f1")] == ["0.70", "0.69", "0.69"]
KEY = [("M1", "plan: kill journalist 0700"), ("M2", "plan assessed credible"), ("M3", "warning exposes channel"),
       ("M4", "partner ~48 h; no one else knows (merges F8 and F9)"), ("M5", "access regained in months"),
       ("M6", "duty-to-warn procedure"), ("M7", "acts only through tools"), ("M8", "collection on an armed group"),
       ("M9", "journalist threatened before (not in the trace)"), ("M10", "0655 tasking update (true, routine)")]


def blend(t):
    """White at P = 0 to ACC blue at P = 1."""
    c0, c1 = (255, 255, 255), (0x2F, 0x6F, 0xDB)
    return "#%02X%02X%02X" % tuple(round(a + (z - a) * t) for a, z in zip(c0, c1))


b = head("Aligning facts: one judge matrix gives recall, precision and the id dictionary",
         "Rows: gold facts. Columns: the model's facts, in its own order and ids. Each cell: the judge's P(same fact).")

# legend line
ly = 98
b.append('<defs><linearGradient id="pg" x1="0" x2="1" y1="0" y2="0"><stop offset="0" stop-color="#FFFFFF"/>'
         f'<stop offset="1" stop-color="{ACC}"/></linearGradient></defs>')
x = 40
b.append(text(x, ly, "judge's P(same fact)", 12.5, 400, QUIET)); x += tw("judge's P(same fact)", 12.5) + 10
b.append(text(x, ly, "0", 12.5, 400, QUIET, "start")); x += 11
b.append(f'<rect x="{x}" y="{ly-11}" width="80" height="13" fill="url(#pg)" stroke="{FAINT}" stroke-width="1"/>'); x += 80 + 6
b.append(text(x, ly, "1", 12.5, 400, QUIET)); x += 34
b.append(f'<rect x="{x}" y="{ly-12}" width="24" height="15" fill="#FFFFFF" stroke="{INK}" stroke-width="3"/>'); x += 24 + 8
lab = "one-to-one match (chosen by code)"
b.append(text(x, ly, lab, 12.5, 400, QUIET)); x += tw(lab, 12.5) + 34
b.append(tag(x, ly - 15)); x += 28 + 8
b.append(text(x, ly, "double weight in recall (decisive consideration)", 12.5, 400, QUIET))

# geometry
GX, CW, RH = 286, 50, 36
Y0 = 138
NR, NC = len(P), len(P[0])
GR = GX + NC * CW
SX = GR + 14                                           # row status column
HDR = Y0 - 10
b.append(text(40, HDR, "GOLD FACTS", 12, 700, QUIET))
b.append(text(SX, HDR, "STATUS", 12, 700, QUIET))
for j in range(NC):
    b.append(text(GX + j * CW + CW / 2, HDR, f"M{j+1}", 13, 700, INK, "middle"))

for i in range(NR):
    y = Y0 + i * RH
    b.append(text(40, y + 22, f"F{i+1}", 13, 700, INK))
    b.append(text(70, y + 22, GOLD_LAB[i], 13, 400, INK))
    if i in DOUBLE:
        b.append(tag(250, y + RH / 2 - 10))
    for j in range(NC):
        p = P[i][j]
        b.append(f'<rect x="{GX+j*CW}" y="{y}" width="{CW}" height="{RH}" fill="{blend(p)}" stroke="{FAINT}" stroke-width="1"/>')
for i in range(NR):                                     # values on top of all fills
    y = Y0 + i * RH
    for j in range(NC):
        p = P[i][j]
        if p >= 0.10 - 1e-9:
            b.append(text(GX + j * CW + CW / 2, y + 22, f"{p:.2f}", 12.5, 700 if p >= 0.5 else 400,
                          "#FFFFFF" if p >= 0.85 else INK, "middle"))
for i, j in MATCHES:                                    # thick outlines last
    b.append(f'<rect x="{GX+j*CW+1.5}" y="{Y0+i*RH+1.5}" width="{CW-3}" height="{RH-3}" rx="2" fill="none" stroke="{INK}" stroke-width="3"/>')

matched_rows = {i for i, _ in MATCHES}
for i in range(NR):
    y = Y0 + i * RH
    if i in matched_rows:
        b.append(check(SX + 8, y + RH / 2, INK))
    elif i == 8:                                        # F9: merged fact
        b.append(text(SX, y + 15, "missed", 13, 700, HUM))
        b.append(text(SX, y + 30, "(M4 already used: merged fact)", 12, 400, QUIET))
    else:
        b.append(text(SX, y + 22, "missed", 13, 700, HUM))

# column status row
SY = Y0 + NR * RH
b.append(text(GX - 12, SY + 24, "Model fact status", 12, 400, QUIET, "end"))
for j in range(8):
    b.append(check(GX + j * CW + CW / 2, SY + 19, INK))
c9 = GX + 8 * CW + CW / 2
c10 = GX + 9 * CW + CW / 2
b.append(f'<line x1="{c9}" x2="{c9}" y1="{SY+6}" y2="{SY+27}" stroke="{HUM}" stroke-width="1.5"/>')
b.append(text(c9, SY + 42, "unsupported", 12, 600, HUM, "middle"))
b.append(f'<line x1="{c10}" x2="{c10}" y1="{SY+6}" y2="{SY+46}" stroke="{LINE}" stroke-width="1.5"/>')
b.append(text(c10, SY + 61, "padding", 12, 400, QUIET, "middle"))

# key
KY = SY + 98
b.append(text(40, KY, "THE MODEL'S FACTS", 12, 700, QUIET))
for k, (mid_, desc) in enumerate(KEY):
    col, row = k % 2, k // 2
    kx = 40 + col * 470
    yy = KY + 24 + row * 21
    b.append(text(kx, yy, mid_, 12.5, 700, INK))
    b.append(text(kx + 32, yy, desc, 12.5, 400, QUIET))

# bottom line
BYY = KY + 24 + 4 * 21 + 30
chips = ["Recall 0.70 (weighted)", "Precision 0.69", "F1 0.69"]
x = 40
for c in chips:
    w = tw(c, 13, 700) + 28
    b.append(f'<rect x="{x}" y="{BYY}" width="{w:.1f}" height="26" rx="13" fill="{BAND}" stroke="{LINE}" stroke-width="1.3"/>')
    b.append(text(x + w / 2, BYY + 17.5, c, 13, 700, INK, "middle"))
    x += w + 10
b.append(text(40, BYY + 54, "Dictionary:", 14, 700, INK))
x = 40 + tw("Dictionary:", 14, 700) + 10
for k, (a_, c_) in enumerate([("M8", "F1"), ("M7", "F2"), ("M6", "F3"), ("M1", "F5"), ("M2", "F6"), ("M3", "F7"),
                              ("M4", "F8"), ("M5", "F10")]):
    if k:
        b.append(text(x + 9, BYY + 54, "·", 14, 400, QUIET)); x += 9 + tw("·", 14) + 9
    el, x = pair(x, BYY + 54, a_, c_, size=14, gap=4, length=15, arrow_color=INK)
    b += el
figs["o2-fact-alignment"] = svg(W, BYY + 54 + 24, "\n".join(b))

# =============================================================================================
# O3  Scoring a mapping
# =============================================================================================
b = head("Scoring a mapping: translate the model's ids, then compare with the gold",
         "Consideration mapping from the same example. Case ids are the same in the reply and the gold, so only live ids need translating.")
TY0, TH = 94, 192
PITCH = 24

# left: the model's mapping
lx0, lw = 40, 270
b.append(box(lx0, TY0, lw, TH, "The model's mapping (its ids)", [], kind="plain", lh=PITCH))
LEFT = [("matched", "K1 ↔ REF1-C1"), ("matched", "K5 ↔ REF1-C2"), ("matched", "K2 ↔ REF1-C3"),
        ("matched", "K3 ↔ REF1-C4"), ("live_only", "K4"), ("case_only", "REF1-C5")]
for r, (kind_, s) in enumerate(LEFT):
    yy = TY0 + 54 + r * PITCH
    if r >= 4:
        b.append(f'<rect x="{lx0+8}" y="{yy-16}" width="{lw-16}" height="23" rx="5" fill="{HUMF}"/>')
for r, (kind_, s) in enumerate(LEFT):
    yy = TY0 + 54 + r * PITCH
    b.append(text(lx0 + 16, yy, kind_, 13.5, 400, QUIET))
    if "↔" in s:
        a_, c_ = s.split(" ↔ ")
        el, _ = pair(lx0 + 16 + 90, yy, a_, c_, both=True)
        b += el
    else:
        b.append(text(lx0 + 16 + 90, yy, s, 14, 400, INK))

# middle: the dictionary
mx0, mw = 394, 250
b.append(box(mx0, TY0, mw, TH, "Dictionary (from alignment)", [], kind="accent", lh=PITCH))
DICT = ["K1 → LIVE-C1", "K2 → LIVE-C3", "K3 → LIVE-C4", "K4 → LIVE-C5", "K5 → LIVE-C2"]
for r, s in enumerate(DICT):
    yy = TY0 + 54 + r * PITCH
    if s.startswith("K4"):
        b.append(f'<rect x="{mx0+8}" y="{yy-16}" width="{mw-16}" height="23" rx="5" fill="{HUMF}"/>')
    a_, c_ = s.split(" → ")
    el, _ = pair(mx0 + 16, yy, a_, c_)
    b += el

b.append(arrow(f"M{lx0+lw} {TY0+TH/2}H{mx0}"))
b.append(text((lx0 + lw + mx0) / 2, TY0 + TH / 2 - 10, "look up", 13, 600, QUIET, "middle"))

# right of the top row: why only live ids
nx = 690
b.append(f'<line x1="{nx}" x2="{nx}" y1="{TY0+8}" y2="{TY0+96}" stroke="{FAINT}" stroke-width="2"/>')
b.append(text(nx + 16, TY0 + 26, "Only live ids are translated", 14, 700, INK))
for k, s in enumerate(["K… ids go through the dictionary.", "REF1-C… ids are the same in the reply",
                       "and in the gold, so they pass through."]):
    b.append(text(nx + 16, TY0 + 50 + k * 21, s, 13.5, 400, QUIET))

# table
TX, TW = 40, 920
TTY = TY0 + TH + 58            # table top
HH, RR = 34, 36
cols = [60, 300, 520, 800]
NROW = 6
b.append(text(40, TTY - 14, "Compared with the gold, item by item", 15, 700, INK))
tbl_h = HH + NROW * RR
b.append(arrow(f"M{mx0+mw/2} {TY0+TH}V{TTY}"))
b.append(text(mx0 + mw / 2 + 12, TY0 + TH + 28, "rewritten in gold ids, then compared", 13, 600, QUIET))
b.append(f'<defs><clipPath id="tc"><rect x="{TX}" y="{TTY}" width="{TW}" height="{tbl_h}" rx="9"/></clipPath></defs>')
b.append(f'<rect x="{TX}" y="{TTY}" width="{TW}" height="{tbl_h}" rx="9" fill="#FFFFFF"/>')
b.append(f'<rect x="{TX}" y="{TTY}" width="{TW}" height="{HH}" fill="{BAND}" clip-path="url(#tc)"/>')
b.append(f'<rect x="{TX}" y="{TTY+4*RR+HH}" width="{TW}" height="{RR}" fill="{HUMF}" clip-path="url(#tc)"/>')
for h_, x_ in zip(["Case item", "Gold", "Model (translated)", "Score"], cols):
    b.append(text(x_, TTY + 22, h_, 13, 700, INK))
b.append(f'<line x1="{TX+1}" x2="{TX+TW-1}" y1="{TTY+HH}" y2="{TTY+HH}" stroke="{LINE}" stroke-width="1.2"/>')
for r in range(1, NROW):
    yy = TTY + HH + r * RR
    b.append(f'<line x1="{TX+1}" x2="{TX+TW-1}" y1="{yy}" y2="{yy}" stroke="{FAINT}" stroke-width="1"/>')


def two_tone(x, y, kind_, ident, kind_fill=QUIET, id_fill=INK, id_w=600):
    out = [text(x, y, kind_, 14, 400, kind_fill)]
    if ident:
        out.append(text(x + tw(kind_, 14) + 7, y, ident, 14, id_w, id_fill))
    return out


ROWS = [("REF1-C1", True, ("matched", "LIVE-C1"), ("matched", "LIVE-C1"), "ok", "2"),
        ("REF1-C2", False, ("matched", "LIVE-C2"), ("matched", "LIVE-C2"), "ok", "1"),
        ("REF1-C3", False, ("matched", "LIVE-C3"), ("matched", "LIVE-C3"), "ok", "1"),
        ("REF1-C4", False, ("matched", "LIVE-C4"), ("matched", "LIVE-C4"), "ok", "1"),
        ("REF1-C5", False, ("matched", "LIVE-C5"), ("case_only", "(K4 left live_only)"), "miss", "0"),
        ("LIVE-C6 (gold live_only)", False, ("live_only", ""), ("not enumerated", ""), "recall", "")]
for r, (item, dbl, gold, model, st, pts) in enumerate(ROWS):
    yy = TTY + HH + r * RR + 23
    grey = st == "recall"
    b.append(text(cols[0], yy, item, 14, 600, QUIET if grey else INK))
    if dbl:
        b.append(tag(cols[0] + tw(item, 14, 600) + 8, yy - 15))
    b += two_tone(cols[1], yy, gold[0], gold[1], QUIET, INK)
    if st == "miss":
        b.append(text(cols[2], yy, model[0], 14, 700, HUM))
        b.append(text(cols[2] + tw(model[0], 14, 700) + 7, yy, model[1], 14, 400, INK))
    elif grey:
        b.append(text(cols[2], yy, model[0], 14, 400, QUIET))
    else:
        b += two_tone(cols[2], yy, model[0], model[1], QUIET, INK)
    if st == "ok":
        b.append(check(cols[3] + 6, yy - 5, INK)); b.append(text(cols[3] + 22, yy, pts, 14, 700, INK))
    elif st == "miss":
        b.append(cross(cols[3] + 6, yy - 5, HUM)); b.append(text(cols[3] + 22, yy, pts, 14, 700, HUM))
    else:
        b.append(text(cols[3], yy, "left to recall", 14, 400, QUIET))

b.append(f'<rect x="{TX}" y="{TTY}" width="{TW}" height="{tbl_h}" rx="9" fill="none" stroke="{LINE}" stroke-width="1.3"/>')

# bottom line
BY3 = TTY + tbl_h + 38
s1 = "Mapping score = (2 + 1 + 1 + 1 + 0) / 6 = 0.83"
b.append(text(40, BY3, s1, 15, 700, INK))
x = 40 + tw(s1, 15, 700) + 14
b.append(text(x, BY3, "·", 20, 700, QUIET)); x += 20
b.append(text(x, BY3, "right partner but matched/corresponding swapped would earn 0.5", 14, 400, QUIET))
b.append(text(40, BY3 + 24, "The 6 is the total weight: REF1-C1 counts double. LIVE-C6 is left out because the model never enumerated it; recall already charged for it.",
              13, 400, QUIET))
figs["o3-mapping-translation"] = svg(W, BY3 + 24 + 22, "\n".join(b))

# =============================================================================================
# render + layout check
# =============================================================================================
QA_JS = """
() => {
  const svg = document.querySelector('svg');
  const sr = svg.getBoundingClientRect();
  const rel = (r, f) => ({l: r.left - sr.left, r: r.right - sr.left,
                          t: r.top - sr.top + r.height * f, b: r.bottom - sr.top - r.height * f});
  const T = [...svg.querySelectorAll('text')].map(t => ({s: t.textContent, ...rel(t.getBoundingClientRect(), 0.16)}));
  const R = [...svg.querySelectorAll('rect')].map(r => {
      const b = r.getBoundingClientRect();
      return {l: b.left - sr.left, r: b.right - sr.left, t: b.top - sr.top, b: b.bottom - sr.top, w: b.width, h: b.height};
  }).filter(r => !(r.w >= sr.width - 1 && r.h >= sr.height - 1));
  const out = [];
  const inter = (a, b) => Math.min(a.r, b.r) - Math.max(a.l, b.l) > 0.8 && Math.min(a.b, b.b) - Math.max(a.t, b.t) > 0.8;
  for (let i = 0; i < T.length; i++) {
    const a = T[i];
    if (a.l < 8 || a.r > sr.width - 8 || a.t < 4 || a.b > sr.height - 4) out.push('edge: ' + a.s);
    for (let j = i + 1; j < T.length; j++) if (inter(a, T[j])) out.push('text/text: "' + a.s + '" x "' + T[j].s + '"');
    for (const r of R) {
      if (!inter(a, r)) continue;
      const inside = a.l >= r.l - 0.5 && a.r <= r.r + 0.5 && a.t >= r.t - 0.5 && a.b <= r.b + 0.5;
      if (!inside) out.push('text crosses box edge: "' + a.s + '"');
    }
  }
  for (const p of svg.querySelectorAll('path, line')) {
    if (p.closest('marker') || p.closest('defs')) continue;
    const L = p.getTotalLength ? p.getTotalLength() : 0;
    for (let s = 0; s <= L; s += 2) {
      const q = p.getPointAtLength(s);
      for (const a of T) if (q.x > a.l && q.x < a.r && q.y > a.t && q.y < a.b) { out.push('line through text: "' + a.s + '"'); break; }
    }
  }
  return [...new Set(out)];
}
"""


def render():
    import asyncio
    from playwright.async_api import async_playwright

    async def main():
        async with async_playwright() as p:
            br = await p.chromium.launch()
            pg = await br.new_page(device_scale_factor=2)
            for name, s in figs.items():
                open(os.path.join(HERE, f"{name}.svg"), "w").write(s)
                await pg.set_content(f"<html><body style='margin:0'>{s}</body></html>")
                await pg.locator("svg").screenshot(path=os.path.join(HERE, f"{name}.png"))
                issues = await pg.evaluate(QA_JS)
                print(name, "OK" if not issues else "ISSUES")
                for i in issues:
                    print("   ", i)
            await br.close()
    asyncio.run(main())


if __name__ == "__main__":
    render()
