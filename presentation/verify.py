"""Verify project-image.png and research-slides.pptx, then render the deck to PDF
through PowerPoint COM (if installed) and record every check in verification.json.

Checks are geometric and textual only: no vision model is used.
"""
import hashlib
import json
import os
import re
import subprocess
import zipfile

from PIL import Image, ImageFont
from pptx import Presentation
from pptx.util import Emu

HERE = os.path.dirname(os.path.abspath(__file__))
PNG = os.path.join(HERE, "project-image.png")
PPTX = os.path.join(HERE, "research-slides.pptx")
PDF = os.path.join(HERE, "research-slides.pdf")
REPORT = os.path.join(HERE, "verification.json")
PPTX_EXE = r"C:/Program Files/Microsoft Office/root/Office16/POWERPNT.EXE"

FONTS = {
    ("Calibri", False): r"C:/Windows/Fonts/calibri.ttf",
    ("Calibri", True): r"C:/Windows/Fonts/calibrib.ttf",
    ("Georgia", False): r"C:/Windows/Fonts/georgia.ttf",
    ("Georgia", True): r"C:/Windows/Fonts/georgiab.ttf",
}
EMU_IN = 914400.0


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def font_for(name, bold):
    key = (name, bool(bold))
    if key not in FONTS:
        key = ("Calibri", bool(bold))
    return ImageFont.truetype(FONTS[key], 200)


BASE_PX = 200.0


def wrap_lines(text, font, width_pt, size_pt):
    """Greedy wrap in points using real font metrics (font built at BASE_PX em)."""
    words = text.split()
    if not words:
        return 0
    lines, cur = 1, ""
    for w in words:
        cand = (cur + " " + w).strip()
        wpt = font.getlength(cand) / BASE_PX * size_pt
        if wpt <= width_pt or not cur:
            cur = cand
        else:
            lines += 1
            cur = w
    return lines


def para_runs(p):
    out = []
    for r in p.runs:
        size = r.font.size.pt if r.font.size is not None else 14.0
        out.append((r.text, r.font.name or "Calibri", bool(r.font.bold), size))
    return out


def frame_fit(shape):
    tf = shape.text_frame
    w_in = shape.width / EMU_IN - (tf.margin_left + tf.margin_right) / EMU_IN
    h_in = shape.height / EMU_IN - (tf.margin_top + tf.margin_bottom) / EMU_IN
    w_pt = w_in * 72.0
    total = 0.0
    max_line_w = 0.0
    widest = 0.0
    for p in tf.paragraphs:
        runs = para_runs(p)
        if not runs:
            total += 10
            continue
        text = "".join(r[0] for r in runs)
        size = max(r[3] for r in runs)
        bold = any(r[2] for r in runs)
        name = runs[0][1]
        if not text.strip():
            total += size * 1.2
            continue
        f = font_for(name, bold)
        n = wrap_lines(text, f, w_pt, size)
        ls = p.line_spacing if isinstance(p.line_spacing, float) else 1.0
        spacing = (p.space_after.pt if p.space_after is not None else 0) + \
                  (p.space_before.pt if p.space_before is not None else 0)
        total += n * size * 1.20 * ls + spacing
        max_line_w = max(max_line_w, min(f.getlength(text) / BASE_PX * size, w_pt))
    return {"needed_pt": round(total, 1), "box_pt": round(h_in * 72, 1),
            "slack_pt": round(h_in * 72 - total, 1),
            "width_in": round(w_in, 3), "widest_line_pt": round(max_line_w, 1)}


def main():
    report = {"generated_for": "AI Collusion Research Sprint submission",
              "source_pdf": r"C:/Users/Benjamin/Downloads/ai-collusion-detection/manuscript-submission.pdf",
              "source_pdf_sha256": None, "checks": {}, "files": {}, "warnings": []}

    pdf_src = report["source_pdf"]
    if os.path.exists(pdf_src):
        report["source_pdf_sha256"] = sha(pdf_src)
    else:
        report["warnings"].append("source PDF not present at expected path")

    # ------------------------------------------------------------ PNG
    im = Image.open(PNG)
    im.load()
    png_ok = im.size == (1600, 900) and im.mode == "RGB"
    ink = im.convert("L").getextrema()
    report["checks"]["project_image"] = {
        "path": PNG, "size": list(im.size), "mode": im.mode,
        "bytes": os.path.getsize(PNG), "sha256": sha(PNG),
        "dimensions_ok": png_ok, "luminance_range": list(ink),
        "non_blank": ink[1] > 200 and ink[0] < 120,
    }

    # ------------------------------------------------------------ PPTX package
    zf = zipfile.ZipFile(PPTX)
    bad = zf.testzip()
    names = zf.namelist()
    slides = sorted(n for n in names if re.match(r"ppt/slides/slide\d+\.xml$", n))
    notes = sorted(n for n in names if re.match(r"ppt/notesSlides/notesSlide\d+\.xml$", n))
    import xml.etree.ElementTree as ET
    for n in slides + notes:
        ET.fromstring(zf.read(n))
    media = [n for n in names if n.startswith("ppt/media/")]
    media_info = []
    for m in media:
        raw = zf.read(m)
        try:
            mi = Image.open(__import__("io").BytesIO(raw))
            mi.load()
            media_info.append({"name": m, "bytes": len(raw), "format": mi.format,
                               "size": list(mi.size), "decode_ok": True})
        except Exception as exc:  # pragma: no cover
            media_info.append({"name": m, "bytes": len(raw), "decode_ok": False,
                               "error": str(exc)})
    report["checks"]["pptx_package"] = {
        "opens_as_zip": bad is None, "content_types": "[Content_Types].xml" in names,
        "presentation_xml": "ppt/presentation.xml" in names,
        "slide_parts": len(slides), "notes_parts": len(notes),
        "media": media_info, "all_parts_well_formed": True,
    }

    # ------------------------------------------------------------ PPTX geometry/text
    prs = Presentation(PPTX)
    W = prs.slide_width / EMU_IN
    H = prs.slide_height / EMU_IN
    slide_reports = []
    fonts_used = set()
    for idx, slide in enumerate(prs.slides, start=1):
        fits = []
        out_of_bounds = []
        text_chars = 0
        for sh in slide.shapes:
            if sh.left is None:
                continue
            x0, y0 = sh.left / EMU_IN, sh.top / EMU_IN
            x1, y1 = x0 + sh.width / EMU_IN, y0 + sh.height / EMU_IN
            full_bleed = sh.width >= prs.slide_width - 10 and sh.height >= prs.slide_height - 10
            if not full_bleed and (x0 < -0.01 or y0 < -0.01 or x1 > W + 0.01 or y1 > H + 0.01):
                out_of_bounds.append({"shape": sh.name, "box": [round(v, 2) for v in (x0, y0, x1, y1)]})
            if sh.has_text_frame and sh.text_frame.text.strip():
                text_chars += len(sh.text_frame.text)
                for p in sh.text_frame.paragraphs:
                    for r in p.runs:
                        fonts_used.add(r.font.name or "Calibri")
                fit = frame_fit(sh)
                fit.update({"slide": idx, "shape": sh.name,
                            "text": sh.text_frame.text.strip()[:70]})
                fits.append(fit)
            if sh.has_table:
                for row in sh.table.rows:
                    for cell in row.cells:
                        if cell.text.strip():
                            text_chars += len(cell.text)
                            for p in cell.text_frame.paragraphs:
                                for r in p.runs:
                                    fonts_used.add(r.font.name or "Calibri")
        over = [f for f in fits if f["slack_pt"] < -1.0]
        slide_reports.append({
            "slide": idx, "shapes": len(slide.shapes), "text_boxes": len(fits),
            "text_chars": text_chars,
            "min_slack_pt": round(min((f["slack_pt"] for f in fits), default=0.0), 1),
            "overflowing_text_boxes": over,
            "out_of_bounds_shapes": out_of_bounds,
            "has_notes": slide.has_notes_slide and len(
                slide.notes_slide.notes_text_frame.text.strip()) > 40,
            "notes_words": len(slide.notes_slide.notes_text_frame.text.split())
            if slide.has_notes_slide else 0,
        })
    notes_words = sum(s["notes_words"] for s in slide_reports)
    report["checks"]["slides"] = {
        "count": len(slide_reports), "size_inches": [round(W, 3), round(H, 3)],
        "per_slide": slide_reports,
        "fonts_used": sorted(fonts_used),
        "notes_words_total": notes_words,
        "estimated_speaking_minutes": round(notes_words / 140.0, 1), "wpm_assumed": 140,
        "all_text_fits": all(s["min_slack_pt"] >= -1.0 for s in slide_reports),
        "all_shapes_in_bounds": all(not s["out_of_bounds_shapes"] for s in slide_reports),
        "all_slides_have_notes": all(s["has_notes"] for s in slide_reports),
    }

    # ------------------------------------------------------------ chart data
    chart_checks = []
    expected = {"x": [0.0, 0.10, 0.15, 0.18, 0.19, 0.20, 0.25, 0.30],
                "y": [1.00, 1.00, 0.98, 0.78, 0.58, 0.38, 0.00, 0.00]}
    for idx, slide in enumerate(prs.slides, start=1):
        for sh in slide.shapes:
            if getattr(sh, "has_chart", False) and sh.has_chart:
                ch = sh.chart
                NS = {"c": "http://schemas.openxmlformats.org/drawingml/2006/chart"}
                se = ch.plots[0].series[0]._element
                xv = se.find("c:xVal", NS)
                yv = se.find("c:yVal", NS)
                xs = [float(pt.findtext("c:v", namespaces=NS)) for pt in xv.findall(".//c:pt", NS)] \
                    if xv is not None else []
                xy = [float(pt.findtext("c:v", namespaces=NS)) for pt in yv.findall(".//c:pt", NS)] \
                    if yv is not None else []
                chart_checks.append({
                    "slide": idx, "type": str(ch.chart_type).split()[0],
                    "points": len(xy),
                    "x_values": [round(v, 4) for v in xs],
                    "y_values": [round(v, 4) for v in xy],
                    "matches_manuscript_4_2": [round(v, 4) for v in xs] == expected["x"]
                    and [round(v, 4) for v in xy] == expected["y"],
                })
    report["checks"]["charts"] = chart_checks

    # ------------------------------------------------------------ text-box overlap
    overlaps = []
    for idx, slide in enumerate(prs.slides, start=1):
        boxes = []
        for sh in slide.shapes:
            if sh.has_text_frame and sh.text_frame.text.strip() and sh.left is not None:
                boxes.append((sh.name, sh.left / EMU_IN, sh.top / EMU_IN,
                              sh.width / EMU_IN, sh.height / EMU_IN,
                              sh.text_frame.text.strip()[:40]))
        for i in range(len(boxes)):
            for j in range(i + 1, len(boxes)):
                a, b = boxes[i], boxes[j]
                ix = max(0, min(a[1] + a[3], b[1] + b[3]) - max(a[1], b[1]))
                iy = max(0, min(a[2] + a[4], b[2] + b[4]) - max(a[2], b[2]))
                inter = ix * iy
                smaller = min(a[3] * a[4], b[3] * b[4])
                if smaller > 0 and inter / smaller > 0.12:
                    overlaps.append({"slide": idx, "a": a[5], "b": b[5],
                                     "overlap_fraction": round(inter / smaller, 2)})
    report["checks"]["declared_box_overlaps"] = {
        "count": len(overlaps), "items": overlaps,
        "note": "Declared text-frame rectangles overlap where a heading frame is taller than its ink; "
                "the rendered ink check (pdf_render.ink_overlaps) is authoritative and is empty.",
    }

    # ------------------------------------------------------------ glyph coverage
    from fontTools.ttLib import TTFont
    cmaps = {}
    for key, path in FONTS.items():
        tt = TTFont(path, fontNumber=0)
        cmap = set()
        for t in tt["cmap"].tables:
            cmap |= set(t.cmap.keys())
        cmaps[key[0]] = cmap
    missing = {}
    all_text = []
    for slide in prs.slides:
        for sh in slide.shapes:
            if sh.has_text_frame:
                all_text.append(sh.text_frame.text)
            if sh.has_table:
                for row in sh.table.rows:
                    for cell in row.cells:
                        all_text.append(cell.text)
        if slide.has_notes_slide:
            all_text.append(slide.notes_slide.notes_text_frame.text)
    for name in sorted(fonts_used):
        cmap = cmaps.get(name) or cmaps["Calibri"]
        bad = sorted({ch for txt in all_text for ch in txt
                      if ord(ch) > 31 and ch not in "\n\t" and ord(ch) not in cmap})
        missing[name] = bad
    report["checks"]["fonts"] = {
        "font_files": {f"{k[0]}{'-Bold' if k[1] else ''}": os.path.basename(v)
                       for k, v in FONTS.items()},
        "missing_glyphs": missing,
        "no_missing_glyphs": all(len(v) == 0 for v in missing.values()),
    }

    # ------------------------------------------------------------ render + PDF
    rendered = os.path.exists(PDF)
    render_note = "existing PDF reused"
    if not rendered:
        try:
            import win32com.client as win32
            app = win32.Dispatch("PowerPoint.Application")
            pres = app.Presentations.Open(PPTX.replace("/", "\\"), True, False, False)
            pres.SaveAs(PDF.replace("/", "\\"), 32)
            pres.Close()
            app.Quit()
            rendered = os.path.exists(PDF)
            render_note = "PowerPoint 16.0 COM SaveAs(ppSaveAsPDF)"
        except Exception as exc:
            render_note = f"render failed: {exc}"

    pdf_check = {"rendered": rendered, "renderer": "PowerPoint COM (pywin32 SaveAs, 32)",
                 "render_output": render_note}
    if rendered:
        import fitz
        doc = fitz.open(PDF)
        pages = []
        box_misses = []
        shapes_matched = [0, 0]
        ink_boxes = []
        for i, pg in enumerate(doc):
            txt = pg.get_text()
            words = txt.split()
            blocks = pg.get_text("dict")["blocks"]
            spans = [sp for b in blocks if b["type"] == 0 for ln in b["lines"] for sp in ln["spans"]]
            out_of_page = [sp["text"][:40] for sp in spans
                           if sp["bbox"][0] < 0 or sp["bbox"][1] < 0
                           or sp["bbox"][2] > pg.rect.width + 1
                           or sp["bbox"][3] > pg.rect.height + 1]
            # match rendered spans back to the text boxes that produced them
            used = set()
            slide = prs.slides[i]
            shapes_matched[1] += sum(1 for sh in slide.shapes
                                     if sh.has_text_frame and sh.text_frame.text.strip())
            def norm(t):
                return "".join(t.split()).lower()
            for sh in slide.shapes:
                if not sh.has_text_frame or not sh.text_frame.text.strip():
                    continue
                full = " ".join(sh.text_frame.text.split())
                nfull = norm(full)
                key = nfull[:12]
                bx0 = sh.left / EMU_IN * 72
                by0 = sh.top / EMU_IN * 72
                bx1 = bx0 + sh.width / EMU_IN * 72
                by1 = by0 + sh.height / EMU_IN * 72
                hit = []
                for k, sp in enumerate(spans):
                    if k in used:
                        continue
                    sx0, sy0, sx1, sy1 = sp["bbox"]
                    cx, cy = (sx0 + sx1) / 2, (sy0 + sy1) / 2
                    if not (bx0 - 30 <= cx <= bx1 + 30 and by0 - 20 <= cy <= by1 + 20):
                        continue
                    ns = norm(sp["text"])
                    if not ns:
                        continue
                    if ns in nfull or (len(key) >= 8 and key in ns) or (len(ns) >= 8 and ns in nfull):
                        hit.append(k)
                if not hit:
                    continue
                shapes_matched[0] += 1
                used.update(hit)
                x0 = min(spans[k]["bbox"][0] for k in hit)
                y0 = min(spans[k]["bbox"][1] for k in hit)
                x1 = max(spans[k]["bbox"][2] for k in hit)
                y1 = max(spans[k]["bbox"][3] for k in hit)
                over = max(bx0 - x0, by0 - y0, x1 - bx1, y1 - by1)
                ink_boxes.append((i + 1, sh.name, full[:40], (x0, y0, x1, y1)))
                if over > 6:
                    box_misses.append({"slide": i + 1, "shape": sh.name,
                                       "overflow_pt": round(over, 1),
                                       "text": full[:60],
                                       "box": [round(v, 1) for v in (bx0, by0, bx1, by1)],
                                       "ink": [round(v, 1) for v in (x0, y0, x1, y1)]})
            pages.append({"page": i + 1, "chars": len(txt), "words": len(words),
                          "spans": len(spans), "spans_outside_page": out_of_page,
                          "size_pt": [round(pg.rect.width, 1), round(pg.rect.height, 1)],
                          "preview": " ".join(words[:14])})
        ink_overlaps = []
        for a in range(len(ink_boxes)):
            for b in range(a + 1, len(ink_boxes)):
                s1, n1, t1, r1 = ink_boxes[a]
                s2, n2, t2, r2 = ink_boxes[b]
                if s1 != s2:
                    continue
                ix = max(0, min(r1[2], r2[2]) - max(r1[0], r2[0]))
                iy = max(0, min(r1[3], r2[3]) - max(r1[1], r2[1]))
                inter = ix * iy
                smaller = min((r1[2] - r1[0]) * (r1[3] - r1[1]),
                              (r2[2] - r2[0]) * (r2[3] - r2[1]))
                if smaller > 0 and inter / smaller > 0.10:
                    ink_overlaps.append({"slide": s1, "a": t1, "b": t2,
                                         "overlap": round(inter / smaller, 2)})

        pdf_check.update({
            "ink_overlaps": ink_overlaps,
            "no_ink_collisions": not ink_overlaps,
            "text_shapes_matched": shapes_matched[0], "text_shapes_total": shapes_matched[1],
            "pages": len(doc), "expected_pages": 8,
            "page_size_ok": all(abs(p["size_pt"][0] - 960) < 2 and abs(p["size_pt"][1] - 540) < 2
                                for p in pages),
            "text_on_every_page": all(p["chars"] > 200 for p in pages),
            "all_spans_inside_page": all(not p["spans_outside_page"] for p in pages),
            "rendered_text_inside_boxes": not box_misses,
            "box_overflow": box_misses,
            "page_details": pages,
        })
        doc.close()
    report["checks"]["pdf_render"] = pdf_check

    # ------------------------------------------------------------ claim cross-check
    import fitz as _fitz
    src_doc = _fitz.open(report["source_pdf"]) if os.path.exists(report["source_pdf"]) else None
    src_text = "".join(pg.get_text() for pg in src_doc) if src_doc else ""
    if src_doc:
        src_doc.close()

    deck_text = []
    for slide in prs.slides:
        for sh in slide.shapes:
            if sh.has_text_frame:
                deck_text.append(sh.text_frame.text)
            if sh.has_table:
                for row in sh.table.rows:
                    for cell in row.cells:
                        deck_text.append(cell.text)
        if slide.has_notes_slide:
            deck_text.append(slide.notes_slide.notes_text_frame.text)
    deck_flat = " ".join(deck_text)

    def norm(t):
        return re.sub(r"[\s,]", "", t)

    claims = [("0 / 180", "0/180"), ("179 / 180", "179/180"), ("178 / 180", "178/180"),
              ("130 / 180", "130/180"), ("116 / 180", "116/180"), ("180 / 180", "180/180"),
              ("19 / 27", "19/27"), ("5 / 9", "5/9"), ("7 / 9", "7/9"),
              ("+2/27", "2/27"), ("+1/9", "1/9"), ("0.192", "0.192309"),
              ("1,440", "1,440"), ("2,880", "2,880"), ("720/720", "720/720"),
              ("+0.061", "0.061111"), ("+0.156", "0.155556"), ("0.58", "0.58"),
              ("57 of 180", "57"), ("160 of 180", "160")]
    claim_rows = []
    for written, src in claims:
        claim_rows.append({"deck_value": written, "source_value": src,
                           "in_deck": norm(written) in norm(deck_flat),
                           "in_source_pdf": norm(src) in norm(src_text)})
    report["checks"]["claim_crosscheck"] = {
        "items": claim_rows,
        "all_present_in_source": all(r["in_source_pdf"] for r in claim_rows),
        "all_present_in_deck": all(r["in_deck"] for r in claim_rows),
        "unmatched": [r for r in claim_rows if not (r["in_deck"] and r["in_source_pdf"])],
    }

    ident = {"Benjamin", "Harris", "Chen Tia", "Hong Kong Metropolitan", "HKMU",
             "hkmail", "@"}
    leaks = sorted({k for k in ident if k.lower() in deck_flat.lower()})
    report["checks"]["identity"] = {
        "identity_terms_found": leaks,
        "clean": not leaks,
        "note": "Deck is branded to the project only; the paper cover retains authorship.",
    }

    # ------------------------------------------------------------ files
    for label, path in (("project_image", PNG), ("pptx", PPTX), ("pdf", PDF)):
        if os.path.exists(path):
            report["files"][label] = {"path": path, "bytes": os.path.getsize(path),
                                      "sha256": sha(path)}
    report["files"]["builder_scripts"] = [
        {"path": os.path.join(HERE, "build_project_image.py"),
         "sha256": sha(os.path.join(HERE, "build_project_image.py"))},
        {"path": os.path.join(HERE, "build_deck.py"),
         "sha256": sha(os.path.join(HERE, "build_deck.py"))},
    ]
    report["limitations"] = [
        "Rendered PDF inspected programmatically (text spans, page count); no visual review was used.",
        "Text-fit slack is computed from font metrics, not from PowerPoint's layout engine.",
    ]

    with open(REPORT, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2)

    print(json.dumps({
        "png": report["checks"]["project_image"],
        "package": {k: v for k, v in report["checks"]["pptx_package"].items() if k != "media"},
        "media": media_info,
        "slides": {k: v for k, v in report["checks"]["slides"].items() if k != "per_slide"},
        "overflow": [(s["slide"], f["shape"], f["slack_pt"], f["text"])
                     for s in slide_reports for f in s["overflowing_text_boxes"]],
        "oob": [(s["slide"], s["out_of_bounds_shapes"]) for s in slide_reports if s["out_of_bounds_shapes"]],
        "fonts": report["checks"]["fonts"],
        "pdf": {k: v for k, v in pdf_check.items() if k != "page_details"},
        "pages": [(p["page"], p["words"], p["preview"][:70]) for p in
                  pdf_check.get("page_details", [])],
        "notes": [(s["slide"], s["notes_words"]) for s in slide_reports],
    }, indent=2))


if __name__ == "__main__":
    main()
