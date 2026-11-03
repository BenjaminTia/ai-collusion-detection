"""Build research-slides.pptx: a concise 8-slide briefing on the manuscript
'Evaluating Action-Dependence Measures for Collusion Detection in a Four-Agent Game'.

Every number in this deck is taken from manuscript-submission.pdf (sha256
14a4d8199f10a3156f196844e9975afb2b3fbd1f8e42322d51e426e22cfed837):
sections 3-5, Tables 1-3 and A5, Figures 2, 4 and 5.
"""
import os
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR, MSO_AUTO_SIZE
from pptx.enum.shapes import MSO_SHAPE
from pptx.chart.data import XyChartData
from pptx.enum.chart import XL_CHART_TYPE, XL_MARKER_STYLE, XL_LEGEND_POSITION
from pptx.oxml.ns import qn
import copy

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "research-slides.pptx")

CRIMSON = RGBColor(0xA0, 0x18, 0x2C)
CRIMSON_DK = RGBColor(0x74, 0x11, 0x20)
CRIMSON_SOFT = RGBColor(0xC4, 0x60, 0x70)
CRIMSON_TINT = RGBColor(0xF4, 0xE6, 0xE6)
CHARCOAL = RGBColor(0x22, 0x24, 0x29)
INK = RGBColor(0x3A, 0x3C, 0x42)
GRAY = RGBColor(0x6C, 0x6C, 0x70)
LIGHT = RGBColor(0xDE, 0xD5, 0xC8)
OFFWHITE = RGBColor(0xF8, 0xF4, 0xEC)
PANEL = RGBColor(0xFF, 0xFD, 0xF9)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)

HEAD_FONT = "Georgia"
BODY_FONT = "Calibri"
SERIF_FONT = "Georgia"

SW, SH = 13.333, 7.5
M = 0.75

prs = Presentation()
prs.slide_width = Inches(SW)
prs.slide_height = Inches(SH)


# ------------------------------------------------------------------ helpers
def bg(slide, color=OFFWHITE):
    s = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, prs.slide_height)
    s.fill.solid()
    s.fill.fore_color.rgb = color
    s.line.fill.background()
    s.shadow.inherit = False
    return s


def noline(shape):
    shape.line.fill.background()


def rect(slide, x, y, w, h, fill=None, line=None, lw=1.0, shape=MSO_SHAPE.RECTANGLE, radius=None):
    s = slide.shapes.add_shape(shape, Inches(x), Inches(y), Inches(w), Inches(h))
    if fill is None:
        s.fill.background()
    else:
        s.fill.solid()
        s.fill.fore_color.rgb = fill
    if line is None:
        s.line.fill.background()
    else:
        s.line.color.rgb = line
        s.line.width = Pt(lw)
    s.shadow.inherit = False
    if radius is not None and shape == MSO_SHAPE.ROUNDED_RECTANGLE:
        s.adjustments[0] = radius
    return s


def _set_spacing(run, pts):
    rPr = run._r.get_or_add_rPr()
    rPr.set("spc", str(int(pts * 100)))


def tx(slide, x, y, w, h, paras, size=14, font=BODY_FONT, color=INK, bold=False,
       italic=False, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP, line=1.12,
       space_after=0, margins=(0.02, 0.02, 0.02, 0.02), tracking=0.0, name=None):
    """paras: str | list of str | list of dicts {t, size, color, bold, italic, font, space_after}"""
    box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    if name:
        box.name = name
    tf = box.text_frame
    tf.word_wrap = True
    tf.auto_size = MSO_AUTO_SIZE.NONE
    tf.vertical_anchor = anchor
    tf.margin_left, tf.margin_right, tf.margin_top, tf.margin_bottom = [Inches(v) for v in margins]
    if isinstance(paras, str):
        paras = [paras]
    for i, item in enumerate(paras):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        spec = item if isinstance(item, dict) else {"t": item}
        p.alignment = spec.get("align", align)
        p.line_spacing = spec.get("line", line)
        p.space_after = Pt(spec.get("space_after", space_after))
        p.space_before = Pt(spec.get("space_before", 0))
        r = p.add_run()
        r.text = spec["t"]
        f = r.font
        f.name = spec.get("font", font)
        f.size = Pt(spec.get("size", size))
        f.bold = spec.get("bold", bold)
        f.italic = spec.get("italic", italic)
        f.color.rgb = spec.get("color", color)
        if spec.get("tracking", tracking):
            _set_spacing(r, spec.get("tracking", tracking))
        # ensure east-asian font mapping does not substitute
        rPr = r._r.get_or_add_rPr()
        ea = rPr.find(qn("a:ea"))
        if ea is None:
            ea = rPr.makeelement(qn("a:ea"), {})
            rPr.append(ea)
        ea.set("typeface", f.name)
    return box


def bullets(slide, x, y, w, h, items, size=13.5, color=INK, gap=8, line=1.16, char="\u2014",
            char_color=CRIMSON, indent=0.24, font=BODY_FONT):
    box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = box.text_frame
    tf.word_wrap = True
    tf.auto_size = MSO_AUTO_SIZE.NONE
    tf.margin_left = Inches(0.02)
    tf.margin_right = Inches(0.02)
    tf.margin_top = Inches(0.02)
    tf.margin_bottom = Inches(0.02)
    for i, item in enumerate(items):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.line_spacing = line
        p.space_after = Pt(gap)
        pPr = p._p.get_or_add_pPr()
        pPr.set("marL", str(int(Inches(indent))))
        pPr.set("indent", str(int(-Inches(indent))))
        buClr = pPr.makeelement(qn("a:buClr"), {})
        srgb = buClr.makeelement(qn("a:srgbClr"), {"val": str(char_color)})
        buClr.append(srgb)
        pPr.append(buClr)
        buFont = pPr.makeelement(qn("a:buFont"), {"typeface": "Arial"})
        pPr.append(buFont)
        buChar = pPr.makeelement(qn("a:buChar"), {"char": char})
        pPr.append(buChar)
        r = p.add_run()
        r.text = item
        r.font.name = font
        r.font.size = Pt(size)
        r.font.color.rgb = color
        rPr = r._r.get_or_add_rPr()
        ea = rPr.makeelement(qn("a:ea"), {"typeface": font})
        rPr.append(ea)
    return box


def eyebrow(slide, text_, num=None):
    rect(slide, M, 0.62, 0.34, 0.045, fill=CRIMSON)
    tx(slide, M + 0.46, 0.5, 9.5, 0.3, text_, size=10.5, font=BODY_FONT, color=CRIMSON,
       bold=True, tracking=2.2)
    if num:
        tx(slide, SW - M - 1.2, 0.5, 1.2, 0.3, num, size=9.5, color=GRAY, align=PP_ALIGN.RIGHT)


def headline(slide, text_, y=0.88, size=30, w=11.6, h=1.0):
    tx(slide, M, y, w, h, text_, size=size, font=HEAD_FONT, color=CHARCOAL, bold=True,
       line=1.02)


def footer(slide, source, page):
    rect(slide, M, 6.94, SW - 2 * M, 0.012, fill=LIGHT)
    tx(slide, M, 7.02, 9.9, 0.3, source, size=8.5, color=GRAY)
    tx(slide, SW - M - 1.0, 7.02, 1.0, 0.3, f"{page} / 8", size=8.5, color=GRAY,
       align=PP_ALIGN.RIGHT)


def notes(slide, text_):
    slide.notes_slide.notes_text_frame.text = text_


def card(slide, x, y, w, h, title, body, tsize=10.5, bsize=13.2, accent=CRIMSON):
    rect(slide, x, y, w, h, fill=PANEL, line=LIGHT, lw=0.9)
    rect(slide, x, y, w, 0.052, fill=accent)
    tx(slide, x + 0.26, y + 0.24, w - 0.5, 0.3, title, size=tsize, color=accent, bold=True,
       tracking=1.6)
    tx(slide, x + 0.26, y + 0.68, w - 0.5, h - 0.85, body, size=bsize, color=INK, line=1.18)


def stat(slide, x, y, w, num, label, numsize=30, labsize=11.5, accent=CRIMSON, h=1.15):
    tx(slide, x, y, w, 0.66, num, size=numsize, font=HEAD_FONT, color=accent, bold=True,
       line=0.95)
    tx(slide, x, y + 0.62, w, h - 0.62, label, size=labsize, color=INK, line=1.14)


# ------------------------------------------------------------------ slide 1
s = prs.slides.add_slide(prs.slide_layouts[6])
bg(s, CHARCOAL)
rect(s, 0, 0, 0.16, SH, fill=CRIMSON)
tx(s, 1.05, 1.02, 10.5, 0.3, "AI COLLUSION RESEARCH SPRINT  \u00b7  RESEARCH BRIEFING",
   size=11, color=CRIMSON_SOFT, bold=True, tracking=2.4)
tx(s, 1.05, 1.42, 10.9, 2.0,
   "Evaluating Action-Dependence Measures for Collusion Detection in a Four-Agent Game",
   size=31, font=HEAD_FONT, color=OFFWHITE, bold=True, line=1.06)
rect(s, 1.07, 3.62, 1.5, 0.035, fill=CRIMSON)
tx(s, 1.05, 3.86, 10.4, 0.5, "Auditing AI Coordination", size=21, font=HEAD_FONT,
   color=CRIMSON_SOFT)
tx(s, 1.05, 4.42, 9.9, 1.1,
   "A four-agent study of shared public cues, private instructions, and what an action-dependence "
   "score can and cannot license an auditor to conclude.",
   size=15.5, color=RGBColor(0xC9, 0xC4, 0xBA), line=1.24)
tx(s, 1.05, 6.52, 10.6, 0.3,
   "Every quantitative claim in this deck is cited to a section, table or figure of the manuscript.",
   size=9, color=RGBColor(0x93, 0x90, 0x8A))
tx(s, SW - 1.35, 6.52, 0.75, 0.3, "1 / 8", size=9, color=RGBColor(0x93, 0x90, 0x8A),
   align=PP_ALIGN.RIGHT)
notes(s, "This is a short briefing on the paper, not a re-run of the experiments. One sentence to open: "
         "an auditor who sees two agents acting in step cannot tell whether they are colluding or both "
         "following the same public cue. The study builds the smallest game in which those two stories "
         "predict the same statistical signal, and asks what an action-dependence score can actually "
         "establish. About four minutes in total.")

# ------------------------------------------------------------------ slide 2
s = prs.slides.add_slide(prs.slide_layouts[6])
bg(s)
eyebrow(s, "01  \u00b7  THE AUDIT QUESTION", "2")
headline(s, "Two agents move in step. That is not yet collusion.")
tx(s, M, 1.86, 11.2, 0.75,
   "An auditor sees four action columns and the cue that was recorded \u2014 not the messages, "
   "reasoning, recommendations or payoffs behind them.",
   size=15, color=INK, line=1.2)
card(s, M, 2.86, 3.7, 2.62, "WHAT THE AUDITOR SEES",
     "Four action columns and the cue as recorded. Everything the agents were told stays hidden.")
card(s, M + 3.96, 2.86, 3.7, 2.62, "WHY THE SCORE IS AMBIGUOUS",
     "A shared cue creates the same association as a private instruction, so an innocent pair can "
     "outrank a linked one.")
card(s, M + 7.92, 2.86, 3.7, 2.62, "WHAT THIS STUDY ASKS",
     "Does exact cue knowledge remove the innocent association and keep the instructed one \u2014 and "
     "where does that separation fail?")
rect(s, M, 5.78, SW - 2 * M, 0.86, fill=CRIMSON_TINT)
rect(s, M, 5.78, 0.06, 0.86, fill=CRIMSON)
tx(s, M + 0.3, 5.94, 11.3, 0.55,
   "A dependence score can locate a relationship. It cannot establish what the relationship means.",
   size=15.5, font=HEAD_FONT, italic=True, color=CRIMSON_DK, anchor=MSO_ANCHOR.MIDDLE)
footer(s, "Source: manuscript \u00a71 (Introduction) and \u00a73.1 (auditor access).", 2)
notes(s, "The auditor's information set is the whole design constraint. They get the actions and the "
         "cue, but not messages, reasoning, recommendations or payoffs. So a dependence score answers "
         "'are these two columns related?' and not 'did they agree?'. The paper's own framing: "
         "dependence is equally consistent with a shared public cue, a common prompt, shared code, or a "
         "private instruction. The score locates a relationship; interpreting it is a separate step.")

# ------------------------------------------------------------------ slide 3
s = prs.slides.add_slide(prs.slide_layouts[6])
bg(s)
eyebrow(s, "02  \u00b7  DESIGN", "3")
headline(s, "Four players, three actions, one visible forecast")
tx(s, M, 1.9, 4.95, 2.5, [
    {"t": "A non-zero-sum rock\u2013paper\u2013scissors round, played simultaneously, one model call "
          "per decision, no history or reward feedback.", "space_after": 8},
    {"t": "All four choose the same action: everyone scores 0.", "space_after": 8},
    {"t": "All three actions appear: everyone scores 1.", "space_after": 8},
    {"t": "Exactly two actions appear: the action that beats the other scores 1, the other scores 0.",
     "space_after": 0},
], size=13.6, line=1.18)
tx(s, M, 4.52, 4.95, 0.8,
   "Because all three symbols reward everyone, a link between two players need not be paid for by the "
   "other two.", size=12.8, italic=True, color=GRAY, line=1.2)

rows = [
    ("Independent", "independent draws", "independent draws"),
    ("Benign", "both follow cue S", "independent draws"),
    ("Seeded", "U rec; V private target", "independent draws"),
    ("Combined", "U rec; V private target", "both follow cue S"),
]
tbl_shape = s.shapes.add_table(len(rows) + 1, 3, Inches(6.05), Inches(2.02), Inches(6.5),
                               Inches(0.52 * (len(rows) + 1)))
table = tbl_shape.table
table.first_row = True
table.horz_banding = False
widths = [1.45, 2.75, 2.3]
for i, wd in enumerate(widths):
    table.columns[i].width = Inches(wd)
for r in range(len(rows) + 1):
    table.rows[r].height = Inches(0.52)
    for c in range(3):
        cell = table.cell(r, c)
        cell.margin_left = Inches(0.12)
        cell.margin_right = Inches(0.08)
        cell.margin_top = Inches(0.04)
        cell.margin_bottom = Inches(0.04)
        cell.vertical_anchor = MSO_ANCHOR.MIDDLE
        cell.fill.solid()
        cell.fill.fore_color.rgb = CHARCOAL if r == 0 else (PANEL if r % 2 else WHITE)
        tf = cell.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.text = ""
        run = p.add_run()
        run.text = ("CONDITION" if c == 0 else ("DESIGNATED PAIR" if c == 1 else "OTHER PAIR")) \
            if r == 0 else rows[r - 1][c]
        f = run.font
        f.size = Pt(10.5 if r == 0 else 11.5)
        f.bold = (r == 0) or (c == 0)
        f.name = BODY_FONT
        f.color.rgb = WHITE if r == 0 else (CRIMSON_DK if c == 0 else INK)

tx(s, 6.07, 4.75, 6.5, 0.3, "AUDITOR VIEWS OF THE SAME ACTIONS", size=9.5, color=CRIMSON,
   bold=True, tracking=1.6)
chips = ["cue omitted", "cue exact", "10% corrupted", "30% corrupted"]
for i, ch in enumerate(chips):
    rect(s, 6.07 + i * 1.63, 5.1, 1.5, 0.42, fill=WHITE, line=CRIMSON_SOFT, lw=0.9,
         shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.25)
    tx(s, 6.07 + i * 1.63, 5.19, 1.5, 0.3, ch, size=10.5, color=CRIMSON_DK,
       align=PP_ALIGN.CENTER)
tx(s, 6.07, 5.72, 6.45, 0.9,
   "Only the cue recording changes across views; the actions are reused. Thresholds come from 199 "
   "within-state permutations per method and view.", size=11.5, color=GRAY, line=1.18)
footer(s, "Source: manuscript \u00a73.1\u20133.2, Table 1 (conditions and units).", 3)
notes(s, "Four conditions, one factorial. Independent: nobody linked. Benign: a designated pair both "
         "follows the public cue, which is an authorised team rule. Seeded: the primary's actual action "
         "is delivered privately and the assistant is told the target. Combined: that seeded pair plus "
         "the other two following the cue. The auditor reuses the same actions under four views: cue "
         "omitted, exact, or corrupted at ten and thirty percent. That is the manipulation that decides "
         "whether an innocent pair can look linked.")

# ------------------------------------------------------------------ slide 4
s = prs.slides.add_slide(prs.slide_layouts[6])
bg(s)
eyebrow(s, "03  \u00b7  SCRIPTED RESULTS", "4")
headline(s, "A shared cue can outrank an instructed pair")
tx(s, M, 1.78, 11.0, 0.55,
   "Combined condition, coupling 0.8. Benign dependence falls as the cue degrades; the seeded pair "
   "does not.", size=13.8, color=GRAY, line=1.15)

rect(s, M, 2.42, 7.5, 3.95, fill=WHITE, line=LIGHT, lw=0.9)
data_pts = [(0, 1.00), (0.10, 1.00), (0.15, 0.98), (0.18, 0.78),
            (0.19, 0.58), (0.20, 0.38), (0.25, 0.00), (0.30, 0.00)]
cd = XyChartData()
ser = cd.add_series("Top-1 credit")
for xv, yv in data_pts:
    ser.add_data_point(xv, yv)
gf = s.shapes.add_chart(XL_CHART_TYPE.XY_SCATTER_LINES, Inches(0.95), Inches(2.58),
                        Inches(7.1), Inches(3.55), cd)
chart = gf.chart
chart.has_legend = False
chart.has_title = False
plot = chart.plots[0]
serie = plot.series[0]
serie.format.line.color.rgb = CRIMSON
serie.format.line.width = Pt(2.0)
serie.marker.style = XL_MARKER_STYLE.CIRCLE
serie.marker.size = 8
serie.marker.format.fill.solid()
serie.marker.format.fill.fore_color.rgb = WHITE
serie.marker.format.line.color.rgb = CRIMSON
serie.marker.format.line.width = Pt(1.5)
serie.smooth = False

va = chart.value_axis
va.minimum_scale = 0.0
va.maximum_scale = 1.0
va.major_unit = 0.25
va.has_major_gridlines = True
va.major_gridlines.format.line.color.rgb = RGBColor(0xEC, 0xE6, 0xDC)
va.major_gridlines.format.line.width = Pt(0.6)
va.tick_labels.font.size = Pt(9)
va.tick_labels.font.name = BODY_FONT
va.tick_labels.font.color.rgb = GRAY
va.format.line.color.rgb = LIGHT
va.has_title = True
va.axis_title.text_frame.text = "Top-1 credit (50 saved trajectories)"
for p in va.axis_title.text_frame.paragraphs:
    for r in p.runs:
        r.font.size = Pt(9.5)
        r.font.name = BODY_FONT
        r.font.color.rgb = GRAY
ca = chart.category_axis
ca.minimum_scale = 0.0
ca.maximum_scale = 0.30
ca.major_unit = 0.05
ca.has_major_gridlines = False
ca.tick_labels.font.size = Pt(9)
ca.tick_labels.font.name = BODY_FONT
ca.tick_labels.font.color.rgb = GRAY
ca.tick_labels.number_format = "0%"
ca.tick_labels.number_format_is_linked = False
ca.format.line.color.rgb = LIGHT
ca.has_title = True
ca.axis_title.text_frame.text = "Cue corruption rate"
for p in ca.axis_title.text_frame.paragraphs:
    for r in p.runs:
        r.font.size = Pt(9.5)
        r.font.name = BODY_FONT
        r.font.color.rgb = GRAY

tx(s, 8.62, 2.5, 3.95, 3.9, [
    {"t": "Credit falls from 1.00 at exact cue to 0.38 at 20% corruption, then to 0.00 at 25%.",
     "space_after": 12},
    {"t": "Expected scores are equal at 0.192, but credit at 19% is only 0.58: the finite-sample "
          "crossing is not the population one.", "space_after": 12},
    {"t": "At full coupling the benign pair can only tie the seeded score, never exceed it.",
     "space_after": 12},
    {"t": "The boundary depends on how well the cue is recorded \u2014 not a universal threshold.",
     "space_after": 0},
], size=12.6, line=1.2)
footer(s, "Source: manuscript \u00a74.1\u20134.2 and Fig. 2; scripted construction, not model behaviour.", 4)
notes(s, "This is the analytical core. In the combined condition the cue-followers are the pair, so "
         "their dependence tracks how much of the cue survives the recording. Under other-symbol "
         "corruption the benign score falls; the seeded pair's does not, because it never runs through "
         "the cue. At about nineteen percent the population scores cross. But measured rankings cross "
         "elsewhere: with 50 trajectories of a thousand rounds, top-1 credit is 0.58 at nineteen "
         "percent and zero at twenty-five. At full coupling the innocent pair can only tie. So the "
         "boundary is channel-dependent, not universal.")

# ------------------------------------------------------------------ slide 5
s = prs.slides.add_slide(prs.slide_layouts[6])
bg(s)
eyebrow(s, "04  \u00b7  MODEL RESULTS", "5")
headline(s, "Delivered is not influential; influential is not correct")
tx(s, M, 1.78, 11.2, 0.5,
   "Pilot: 1,440 decisions, 180 assistant situations, every output strictly valid.",
   size=13.6, color=GRAY)

stat(s, M, 2.4, 3.55, "0 / 180", "assistant actions changed when the private message was removed",
     numsize=34)
stat(s, M + 3.96, 2.4, 3.55, "180 / 180", "intended mapping under priority plus an explicit target",
     numsize=34)
stat(s, M + 7.92, 2.4, 3.55, "0 / 180", "copied the primary in that same arm", numsize=34)

arm_rows = [("Quoted relational", "57", "64"),
            ("Quoted explicit", "62", "64"),
            ("Priority relational", "9", "160"),
            ("Priority explicit", "180", "0")]
tbl = s.shapes.add_table(5, 3, Inches(M), Inches(4.02), Inches(6.7), Inches(0.46 * 5)).table
tbl.first_row = True
tbl.horz_banding = False
for i, wd in enumerate([2.9, 1.9, 1.9]):
    tbl.columns[i].width = Inches(wd)
hdr = ["Arm (180 situations each)", "Intended / 180", "Copy primary / 180"]
for r in range(5):
    tbl.rows[r].height = Inches(0.46)
    for c in range(3):
        cell = tbl.cell(r, c)
        cell.margin_left = Inches(0.1)
        cell.margin_top = Inches(0.03)
        cell.margin_bottom = Inches(0.03)
        cell.vertical_anchor = MSO_ANCHOR.MIDDLE
        cell.fill.solid()
        cell.fill.fore_color.rgb = CHARCOAL if r == 0 else (PANEL if r % 2 else WHITE)
        p = cell.text_frame.paragraphs[0]
        run = p.add_run()
        run.text = hdr[c] if r == 0 else arm_rows[r - 1][c]
        run.font.size = Pt(10.5 if r == 0 else 11.5)
        run.font.name = BODY_FONT
        run.font.bold = (r == 0) or (c == 0)
        run.font.color.rgb = WHITE if r == 0 else (INK if c == 0 else CRIMSON_DK)

tx(s, 7.85, 3.95, 4.75, 2.6, [
    {"t": "The score ignores labels.", "size": 13.5, "bold": True, "color": CRIMSON_DK,
     "space_after": 6},
    {"t": "Reindexing one player's actions leaves every CMI and net score unchanged, so a plausible "
          "wrong map can outscore a weaker correct one.", "size": 12.4, "space_after": 10},
    {"t": "Copying the primary is a response, but it executes the wrong map: in the priority-relational "
          "arm the model copied 160 of 180 times.", "size": 12.4, "space_after": 0},
], size=12.4, line=1.2)
footer(s, "Source: manuscript \u00a75.1 and Table 2; counts are descriptive, not independent games.", 5)
notes(s, "Three facts worth keeping apart. Delivery was perfect: all 1,440 outputs were valid JSON. "
         "Yet removing the message changed zero of 180 assistant actions, so the channel had no "
         "measured influence in the pilot. The factorial moves correct mapping from 57 of 180 under "
         "the original relational wording to 180 of 180 when the message names the target and is given "
         "priority. And a model can be responsive and wrong: the priority-relational arm copied the "
         "primary 160 times out of 180. Because scores ignore labels, that wrong policy can outscore a "
         "weaker correct one.")

# ------------------------------------------------------------------ slide 6
s = prs.slides.add_slide(prs.slide_layouts[6])
bg(s)
eyebrow(s, "05  \u00b7  HELD-OUT VALIDATION", "6")
headline(s, "The treatment holds; the sample stays small")
tx(s, M, 1.8, 5.6, 0.4, "FRESH SCHEDULES, FROZEN BEFORE COLLECTION", size=9.5, color=CRIMSON,
   bold=True, tracking=1.6)
stat(s, M, 2.2, 5.3, "179 / 180", "seeded assistant situations mapped to the intended target",
     numsize=28, h=1.0)
stat(s, M, 3.14, 5.3, "178 / 180", "combined assistant situations mapped to the intended target",
     numsize=28, h=1.0)
stat(s, M, 4.08, 5.3, "130 / 180  \u00b7  116 / 180", "paired action changes versus the no-message "
     "replay, seeded and combined", numsize=23, h=1.0)
tx(s, M, 5.18, 5.4, 0.9,
   "2,880 main decisions and 360 real replays across 12 complete trajectories; recommendation "
   "compliance 720/720.", size=11.8, color=GRAY, line=1.2)

tx(s, 7.0, 1.8, 5.6, 0.4, "DETECTOR OUTCOMES (3 TRAJECTORIES PER CELL)", size=9.5, color=CRIMSON,
   bold=True, tracking=1.6)
det = [
    ("Independent", "0/3 alarms under every view", GRAY),
    ("Benign, exact cue", "0/3 alarms", GRAY),
    ("Benign, cue omitted or corrupted", "3/3 alarms \u2014 context, not collusion", CRIMSON),
    ("Seeded and combined", "3/3 alarms; combined top-1 credit 1.0, or 1/3 when the cue is omitted",
     CRIMSON),
]
yy = 2.24
for lab, val, col in det:
    rect(s, 7.0, yy + 0.1, 0.09, 0.46, fill=col)
    tx(s, 7.22, yy, 5.3, 0.3, lab, size=12.4, color=CHARCOAL, bold=True)
    tx(s, 7.22, yy + 0.27, 5.3, 0.5, val, size=11.3, color=INK, line=1.12)
    yy += 0.78
rect(s, 7.0, 5.5, 5.5, 0.72, fill=CRIMSON_TINT)
tx(s, 7.2, 5.6, 5.1, 0.55,
   "Three trajectories per condition describe this run; they do not support error guarantees.",
   size=11.2, color=CRIMSON_DK, italic=True, line=1.15)
footer(s, "Source: manuscript \u00a75.2\u20135.3, Table 3 and Fig. 4.", 6)
notes(s, "The held-out schedules are the behavioural check: intended mapping is 179 of 180 seeded and "
         "178 of 180 combined, with 130 and 116 paired changes against the no-message replay. The "
         "detector side is more sobering. It alarms on all three seeded and all three combined "
         "trajectories, but also on all three benign trajectories whenever the cue is omitted or "
         "corrupted, and on none when the cue is recorded exactly. That is accurate about dependence "
         "and wrong about cause \u2014 and three trajectories per cell are descriptions, not error rates.")

# ------------------------------------------------------------------ slide 7
s = prs.slides.add_slide(prs.slide_layouts[6])
bg(s)
eyebrow(s, "06  \u00b7  PAYOFFS", "7")
headline(s, "In this game, coordination did not cost the outsiders")
tx(s, M, 1.8, 6.0, 0.4, "EXACT ENUMERATION, ALL 81 PROFILES", size=9.5, color=CRIMSON,
   bold=True, tracking=1.6)
tx(s, M, 2.2, 5.4, 0.62, "19 / 27", size=30, font=HEAD_FONT, color=CRIMSON, bold=True)
tx(s, M + 1.85, 2.29, 3.6, 0.6, "expected payoff per player with independent actions", size=11.5,
   color=INK, line=1.12)
tx(s, M, 2.95, 5.4, 0.62, "5 / 9", size=30, font=HEAD_FONT, color=CRIMSON, bold=True)
tx(s, M + 1.85, 3.04, 3.6, 0.6, "the same player when one pair follows the cue", size=11.5,
   color=INK, line=1.12)
tx(s, M, 3.7, 5.4, 0.6, "1  \u00b7  5/9  \u00b7  7/9", size=26, font=HEAD_FONT, color=CRIMSON,
   bold=True)
tx(s, M + 2.95, 3.78, 2.6, 0.6, "primary \u00b7 assistant \u00b7 each outsider at full coupling",
   size=11.5, color=INK, line=1.12)
tx(s, M, 4.5, 5.6, 0.7,
   "Outsiders gain +2/27 and +1/9; the gain scales linearly with mixture coupling.",
   size=12.2, color=INK, line=1.2)

rect(s, 6.7, 2.12, 5.85, 1.9, fill=PANEL, line=LIGHT, lw=0.9)
tx(s, 6.95, 2.28, 5.4, 0.3, "MATCHED REPLAY, OUTSIDER PAYOFF CHANGE", size=9.5, color=CRIMSON,
   bold=True, tracking=1.6)
tx(s, 6.95, 2.62, 5.3, 0.9, [
    {"t": "+0.061 seeded   \u00b7   +0.156 combined", "size": 17, "font": HEAD_FONT,
     "bold": True, "color": CRIMSON_DK, "space_after": 4},
    {"t": "mean change when only the assistant action is replaced by its real no-message response",
     "size": 10.8, "color": GRAY},
], line=1.14)
tx(s, 6.95, 3.42, 5.3, 0.5, "One seeded trajectory was slightly negative.", size=10.8, color=GRAY)

rect(s, M, 5.45, SW - 2 * M, 1.25, fill=CHARCOAL)
tx(s, M + 0.3, 5.6, 11.6, 1.0,
   "Scoped to this game: the all-three-symbol rule rewards everyone. The replay is a "
   "fixed-other-actions reconstruction, not an equilibrium counterfactual \u2014 and no welfare, price "
   "or market claim follows.",
   size=12.4, color=RGBColor(0xE4, 0xDF, 0xD4), line=1.22)
footer(s, "Source: manuscript \u00a75.4, Table A5 and Fig. 5 (fixed-other-actions reconstruction).", 7)
notes(s, "The next question is who pays for coordination. Here, nobody does, on average. Enumeration "
         "over all 81 profiles gives an independent player 19 over 27; when one pair follows the cue, 5 "
         "over 9. At full coupling the primary gets 1, the assistant 5 over 9, each outsider 7 over 9, "
         "so outsiders gain 2 over 27 and 1 over 9. The matched replay agrees: plus 0.061 seeded and "
         "plus 0.156 combined, with one slightly negative seeded trajectory. The reason is the scoring "
         "rule, where three different symbols pay everyone. That is a scoped negative result, not "
         "permission to generalise to markets.")

# ------------------------------------------------------------------ slide 8
s = prs.slides.add_slide(prs.slide_layouts[6])
bg(s)
eyebrow(s, "07  \u00b7  WHAT AN ALARM LICENSES", "8")
headline(s, "Investigate the relationship, do not sanction it")
steps = [
    ("Confirm the action records and how the cue was recorded.", "An omitted cue makes an innocent pair "
     "look linked."),
    ("Establish what the auditor could not see.", "Messages, recommendations and reasoning are outside "
     "the measured state."),
    ("Test whether the channel changed behaviour.", "Replay the same situation with the message removed; "
     "delivery is not influence."),
    ("Check the mapping, not just the dependence.", "A responsive agent can execute a wrong map, and the "
     "score cannot tell."),
    ("Only then measure competitive disadvantage.", "In this game the outsiders gained; do not assume "
     "harm."),
]
yy = 1.95
for i, (head, sub) in enumerate(steps):
    rect(s, M, yy, 0.42, 0.42, fill=CRIMSON if i < 5 else GRAY, shape=MSO_SHAPE.OVAL)
    tx(s, M, yy + 0.04, 0.42, 0.34, str(i + 1), size=12.5, font=BODY_FONT, color=WHITE,
       bold=True, align=PP_ALIGN.CENTER)
    tx(s, M + 0.62, yy - 0.04, 6.5, 0.3, head, size=13.6, color=CHARCOAL, bold=True)
    tx(s, M + 0.62, yy + 0.26, 6.5, 0.5, sub, size=11.2, color=GRAY, line=1.12)
    yy += 0.86

rect(s, 8.55, 1.9, 4.03, 3.75, fill=RGBColor(0xEF, 0xEA, 0xE0))
tx(s, 8.8, 2.06, 3.6, 0.3, "WHAT THIS DOES NOT SHOW", size=9.5, color=CRIMSON_DK, bold=True,
   tracking=1.6)
bullets(s, 8.8, 2.42, 3.55, 3.1, [
    "One quantised 8B-A1B model with a trained adapter; greedy, stateless prompts.",
    "Three held-out trajectories per condition.",
    "Wording and instruction precedence changed together.",
    "No learning, negotiation or coalition formation.",
    "No prices, markets or welfare claims.",
], size=11.0, gap=7, line=1.14)

tx(s, M, 6.45, 11.7, 0.5,
   "An alarm selects a relationship for investigation, not an agreement for sanction.",
   size=17, font=HEAD_FONT, italic=True, color=CRIMSON_DK)
footer(s, "Source: manuscript \u00a76 (Discussion), Appendix A (limitations).", 8)
notes(s, "Close on the operational reading. An alarm is a reason to look closer, in this order: check the "
         "records; check the auditor's context; check whether the channel changed behaviour; check "
         "whether the executed policy matches the intended map; and only then measure competitive "
         "disadvantage. The limits are structural: one quantised model with an adapter, greedy and "
         "stateless prompts, three trajectories per condition, a bundled factorial. The paper claims no "
         "spontaneous collusion and no general detector; the contribution is an evidence-linked account "
         "of where the measure fails.")

prs.save(OUT)
print("saved", OUT, "slides:", len(prs.slides.__iter__.__self__._sldIdLst))
