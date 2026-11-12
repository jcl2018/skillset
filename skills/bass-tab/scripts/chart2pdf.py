#!/usr/bin/env python3
"""Render a song file straight to a compact play-along chart PDF (1-2 pages).

    python3 chart2pdf.py <slug>/<slug>.py -o <slug>/<slug>.pdf [--paper letter|a4] [--template PATH]

Several bars per line, a bold section label where each section starts, repeated
figures drawn once between repeat signs with a count, a section that repeats an
earlier one reduced to one reference line, chord names over bars, lyrics under
the bar they belong to. Tab digits are never smaller than 9 pt: the renderer
tightens spacing and collapses repeats first, and refuses (naming the song) if
two pages are still not enough. Text tab and the long PDF are tabgen + tab2pdf.
"""

from __future__ import annotations

import argparse
import sys

from pdfdraw import PDF
from pdfkit import (_WARNINGS, FOOTER_SIZE, MARGIN, PAPERS, fit_to_width, string_width,
                    wrap_to_width)
import chartformat
from tabcore import SLOTS, rhythm_cells, row_label, section_ranges, strings_for
from tabgen import load_song
import chartplan
from chartplan import UNIT, bar_width, ladder, pack, plan_units, slot_widths

MAX_PAGES = 2
CLEF = 11.0                      # room left of the stave for the T A B clef


def label_w(song, cfg):
    """Width of the widest string label (at least one letter W; a retuned row may be C#)."""
    sz = cfg.t.staff.label_size
    return max([string_width("W", "F3", sz)] +
               [string_width(row_label(song["meta"], r), "F3", sz) for r in song["rows"]])


def gutter(cfg, song):
    """Room left of the stave: the clef (if the template draws it) and the string letters."""
    return (CLEF if cfg.t.staff.clef else 0.0) + label_w(song, cfg) + 3.0


def head_step(cfg):
    return cfg.t.header_size + 3.0


def rule_drop(cfg, n):
    """How far under the title baseline the header rule sits, for N header lines."""
    return cfg.t.header_size + 5.0 + head_step(cfg) * (max(n, 1) - 1) + 6.0


def gap(cfg):
    return cfg.fs * cfg.t.staff.gap
SHORT = {"8": 1, "3": 1, "6": 2}


def read_song(path):
    m = load_song(path)
    meta = m.META
    try:
        rows = strings_for(meta)
    except ValueError as e:
        raise SystemExit("%s: %s" % (meta.get("title", path), e))
    return {"meta": meta, "rows": rows, "report": getattr(m, "REPORT", None) or {},
             "bars": m.BARS, "sections": m.SECTIONS,
            "chords": getattr(m, "CHORDS", None) or {}, "lyrics": getattr(m, "LYRICS", {}) or {},
            "caveats": getattr(m, "CAVEATS", []), "slots": int(meta.get("slots", SLOTS))}


def line_height(line, song, cfg):
    g = gap(cfg)
    if line[0]["kind"] == "ref":
        return 16.0
    bars = [b for u in line for b in u["bars"]]
    h = 3 + (len(song["rows"]) - 1) * g + 5 + cfg.t.bar_numbers.size + 2
    if any(u["reps"] > 1 for u in line):
        h += 10
    if any(u["label"] for u in line):
        h += 12
    if any(song["chords"].get(b) for b in bars):
        h += 10
    if cfg.rhythm:
        h += 1.4 * g + 3
    if any(song["lyrics"].get(b) for b in bars):
        h += 11
    return h + 4


def head_lines(song, cfg, usable):
    t = cfg.t
    text = chartformat.header_text(song["meta"], t)
    return wrap_to_width(text, "F3", t.header_size, usable) if text else []


def tail_blocks(song, cfg, usable):
    """[(text, font, size, step, gray)]: the source report, then the caveats."""
    t, out = cfg.t, []
    ranges = section_ranges(song["sections"], song["bars"])
    for text, bold in chartformat.report_lines(song, ranges, t):
        for ln in wrap_to_width(text, "F2" if bold else "F3", t.report.size, usable):
            out.append((ln, "F2" if bold else "F3", t.report.size, t.report.size + 2.0, 0.25))
    return out + [(n, "F3", 7.0, 9.0, 0.4) for n in foot_blocks(song, usable)]


def foot_blocks(song, usable):
    out = []
    for title, body in song["caveats"]:
        out += wrap_to_width("%s: %s" % (title, " ".join(body)), "F3", 7.0, usable)
    return out


def paginate(song, cfg, w, h):
    usable = w - 2 * MARGIN
    avail = usable - gutter(cfg, song)
    lines = pack(plan_units(song, cfg, avail - 20), avail, cfg.t.section.size, cfg.t.section.time_size)
    top = h - MARGIN
    bottom = MARGIN + 26
    head = cfg.t.title_row.size + rule_drop(cfg, len(head_lines(song, cfg, usable))) + 9
    notes = tail_blocks(song, cfg, usable)
    pages, cur, y = [], [], top - head
    for ln in lines:
        lh = line_height(ln, song, cfg)
        if y - lh < bottom:
            pages.append(cur)
            cur, y = [], top
        cur.append((ln, y, lh))
        y -= lh
    pages.append(cur)
    need = 8 + sum(n[3] for n in notes)
    if notes and y - need < bottom:
        pages.append([])
        if need > top - bottom:      # longer than a page: never cut it
            raise SystemExit("chart2pdf: %s: the source report and caveats do not fit one page "
                             "(%d lines). Shorten them." % (song["meta"].get("title") or "song",
                                                            len(notes)))
    return pages, lines, notes


def draw_bar(pdf, song, cfg, num, x0, bw, ys, g):
    bar, slots = song["bars"][num], song["slots"]
    nat = slot_widths(bar, cfg)
    k = (bw - 6) / sum(nat)
    xs, x = [], x0 + 3
    for wd in nat:
        xs.append(x + wd * k / 2.0)
        x += wd * k
    fs, hi = cfg.fs, song["rows"][::-1]
    for i, sl in enumerate(bar):
        for st, (fret, art) in (sl or {}).items():
            y = ys[hi.index(st)]
            txt = str(fret)
            tw = len(txt) * UNIT * fs
            pdf._ops.append(b"1 g %.2f %.2f %.2f %.2f re f\n"
                            % (xs[i] - tw / 2 - 0.8, y - g * 0.46, tw + 1.6, g * 0.92))
            pdf.text(xs[i] - tw / 2, y - fs * 0.33, txt, "F1", fs)
            if art == "s":
                pdf.slide(xs[i] + tw / 2 + 0.5, y - 2.5, xs[i] + tw / 2 + 5.5, y + 2.5)
            elif art:
                pdf.text(xs[i] + tw / 2, y + fs * 0.1, art, "F3", fs * 0.6)
    if not cfg.rhythm:
        return
    cells = rhythm_cells(bar, slots)
    codes = [cells[3 * i] for i in range(slots)]
    base, end = ys[-1] - g * 0.5, ys[-1] - g * 1.4
    per = slots // 4
    groups = {}
    for i, c in enumerate(codes):
        if c in "638d42D":
            pdf.stem(xs[i], base, end, w=0.6)
        if c in SHORT:
            groups.setdefault(i // per, []).append((i, c))
    for notes in groups.values():
        if len(notes) == 1:
            i, c = notes[0]
            for q in range(SHORT[c]):
                pdf.flag(xs[i] + 0.3, end + 0.45 * g * q, g * 0.8)
            continue
        pdf.beam(xs[notes[0][0]] - 0.3, end, xs[notes[-1][0]] + 0.3, h=1.5)
        for j, (i, c) in enumerate(notes):
            if SHORT[c] < 2:
                continue
            nxt = notes[j + 1] if j + 1 < len(notes) else None
            if nxt and SHORT[nxt[1]] == 2:
                pdf.beam(xs[i] - 0.3, end + 2.3, xs[nxt[0]] + 0.3, h=1.5)
            elif not (j and SHORT[notes[j - 1][1]] == 2):
                pdf.beam(xs[i] - 0.3, end + 2.3, xs[i] + 3.5, h=1.5)


def draw_line(pdf, song, cfg, ln, y, lh, usable, last, x_left):
    g, t = gap(cfg), cfg.t
    ssz = t.section.size
    if ln[0]["kind"] == "ref":
        u = ln[0]
        lab, _ = fit_to_width(u["label"], "F2", ssz, usable * 0.6)
        pdf.text(MARGIN, y - 11, lab, "F2", ssz)
        x = MARGIN + string_width(lab, "F2", ssz) + 6
        if u["time"]:
            tm = t.section.time.format(t=u["time"])
            pdf.text(x, y - 11, tm, "F3", t.section.time_size, gray=0.4)
            x += string_width(tm, "F3", t.section.time_size) + 6
        pdf.text(x, y - 11, u["text"], "F4", 9.0, gray=0.3)
        return
    avail = usable - gutter(cfg, song)
    fixed = sum(18 for u in ln if u["reps"] > 1)
    sum_bars = sum(u["width"] for u in ln) - fixed
    f = 1.0 if last else max(1.0, min(1.4, (avail - fixed) / sum_bars))
    cy = y - 3
    if any(u["reps"] > 1 for u in ln):
        cy -= 10                              # the repeat counts sit on a row of their own, above everything
    count_y, lab_y = cy - 8, cy - 10
    if any(u["label"] for u in ln):
        cy -= 12
    num_y, cy = cy - t.bar_numbers.size, cy - t.bar_numbers.size - 2
    has_chord = any(song["chords"].get(b) for u in ln for b in u["bars"])
    if has_chord:
        cy -= 10
    chord_y = cy + 1
    rows = song["rows"][::-1]
    ys = [cy - 5 - g * i for i in range(len(rows))]
    pdf.rule(x_left, ys[0], x_left, ys[-1])
    for yy, row in zip(ys, rows):
        pdf.text(x_left - label_w(song, cfg) - 1.5,
                 yy - t.staff.label_size * 0.33, row_label(song["meta"], row), "F3", t.staff.label_size)
    x = x_left
    miss, est = chartplan.missing(song), set(song["report"].get("estimates") or [])
    for u in ln:
        reps = u["reps"] > 1
        x_start = x
        if reps:
            pdf.repeat_bar(x, ys[-1] - 0.5, ys[0] + 0.5, opening=True)
            x += 9
        for bi, num in enumerate(u["bars"]):
            bw = bar_width(num, song, cfg) * f
            for yy in ys:
                pdf.rule(x, yy, x + bw, gray=0.45)
            if bi == 0 and not reps:
                pdf.stem(x, ys[-1] - 0.5, ys[0] + 0.5, w=0.7)
            if bi == 0 and u["label"]:
                pdf.text(x + 1, lab_y, u["label"], "F2", ssz)
                if u["time"]:
                    pdf.text(x + 1 + string_width(u["label"], "F2", ssz) + 4, lab_y,
                             t.section.time.format(t=u["time"]), "F3", t.section.time_size, gray=0.4)
            pdf.text(x + 1.5, num_y, str(num), "F3", t.bar_numbers.size, gray=0.4)
            ch = song["chords"].get(num)
            if ch:
                pdf.text(x + 2, chord_y, ch, "F2", t.chords.size, gray=0.15)
            draw_bar(pdf, song, cfg, num, x, bw, ys, g)
            if num in miss:
                mk, ms = t.marks.missing, t.marks.size
                mw, my = string_width(mk, "F4", ms), (ys[0] + ys[-1]) / 2.0
                pdf._ops.append(b"1 g %.2f %.2f %.2f %.2f re f\n" % (x + bw / 2 - mw / 2 - 2, my - ms * 0.6, mw + 4, ms * 1.3))
                pdf.text(x + bw / 2 - mw / 2, my - ms * 0.33, mk, "F4", ms, gray=0.35)
            if num in est:
                pdf.approx(x + bw - t.marks.estimate_size, ys[0] + 5, t.marks.estimate_size * 0.8)
            lyr = song["lyrics"].get(num)
            if lyr:
                pdf.text(x + 2, ys[-1] - (1.4 * g + 3 if cfg.rhythm else 0) - 9, lyr, "F3", t.lyrics.size)
            x += bw
            if not (reps and bi == len(u["bars"]) - 1):
                pdf.stem(x, ys[-1] - 0.5, ys[0] + 0.5, w=0.7)
        if reps:
            x += 9
            pdf.repeat_bar(x, ys[-1] - 0.5, ys[0] + 0.5, opening=False)
            lbl = t.section.repeat.format(n=u["reps"])
            pdf.text(x - 1.5 - string_width(lbl, "F2", 9.0) / 2, count_y, lbl, "F2", 9.0)
    clef, step = 7.5, (ys[0] - ys[-1]) / 3.0
    for k, ch in enumerate("TAB" if t.staff.clef else ""):
        pdf.text(MARGIN + 1.5, ys[0] - (k + 0.5) * step - clef * 0.33, ch, "F2", clef)


def render(song, paper, refs_only=False, template=None, expand=False):
    w, h = PAPERS[paper]
    usable = w - 2 * MARGIN
    t = chartformat.load(template)
    name = song["meta"].get("title") or "song"
    chartformat.check_song(song, name)
    if expand and refs_only:
        raise SystemExit("chart2pdf: --expand-sections and --collapse-sections contradict each other")
    rungs = ladder(t, expand)
    title, artist = chartformat.title_parts(song["meta"], t)
    cfg = pages = lines = notes = None
    cands = [c for c in rungs if c.secref or not refs_only]
    if not cands:
        raise SystemExit("chart2pdf: template %s has no secref rung for --collapse-sections"
                         % (template or chartformat.DEFAULT))
    for cand in cands:
        pages, lines, notes = paginate(song, cand, w, h)
        if len(pages) <= min(MAX_PAGES, cand.pages):
            cfg = cand
            break
    if cfg is None:
        raise SystemExit("chart2pdf: %s does not fit %d pages at %.0f pt tab digits "
                         "(needs %d). Cut bars or split the song."
                         % (name, MAX_PAGES, rungs[-1].fs, len(pages)))
    pdf = PDF(w, h)
    last_line = lines[-1]
    for pi, pg in enumerate(pages):
        pdf.new_page()
        if pi == 0:
            tr = t.title_row
            tt, ts = fit_to_width(title, "F2", tr.size, usable * 0.62, min_size=11.0)
            tx = h - MARGIN - ts
            pdf.text(MARGIN, tx, tt, "F2", ts)
            a, _ = fit_to_width(artist, "F3", tr.right_size, usable - string_width(tt, "F2", ts) - 14)
            pdf.text(w - MARGIN - string_width(a, "F3", tr.right_size), tx, a, "F3", tr.right_size, gray=0.25)
            hl = head_lines(song, cfg, usable)
            for k, hb in enumerate(hl):
                pdf.text(MARGIN, tx - t.header_size - 5 - head_step(cfg) * k, hb, "F3", t.header_size, gray=0.35)
            pdf.rule(MARGIN, tx - rule_drop(cfg, len(hl)), w - MARGIN)
        for ln, y, lh in pg:
            draw_line(pdf, song, cfg, ln, y, lh, usable, ln is last_line, MARGIN + gutter(cfg, song))
        if pi == len(pages) - 1 and notes:
            yy = (pg[-1][1] - pg[-1][2]) if pg else h - MARGIN
            yy -= 6
            for txt, font, size, step, gr in notes:
                yy -= step
                pdf.text(MARGIN, yy, txt, font, size, gray=gr)
    pdf.flush()
    total = len(pdf.pages)
    art = song["meta"].get("artist", "")
    label = "%s — %s" % (title, art) if art else title
    for idx, (ops, imgs) in enumerate(zip(pdf.pages, pdf.page_images), start=1):
        pdf._ops, pdf._imgs = ops, imgs
        pn = "%d / %d" % (idx, total)
        pn_w = string_width(pn, "F3", FOOTER_SIZE)
        lab, _ = fit_to_width(label, "F3", FOOTER_SIZE, usable - pn_w - 18)
        pdf.text(MARGIN, MARGIN, lab, "F3", FOOTER_SIZE, gray=0.45)
        pdf.text(w - MARGIN - pn_w, MARGIN, pn, "F3", FOOTER_SIZE, gray=0.45)
    pdf._ops, pdf._imgs = [], set()
    stats = {"pages": total, "tab_font_pt": cfg.fs, "lines": len(lines),
             "section_refs": sum(1 for ln in lines if ln[0]["kind"] == "ref")}
    return pdf.build(title, art), stats


def main(argv=None):
    ap = argparse.ArgumentParser(description="Song file -> compact chart PDF.")
    ap.add_argument("song", help="the <slug>.py song file")
    ap.add_argument("-o", "--out", required=True)
    ap.add_argument("--paper", choices=sorted(PAPERS), default="letter")
    ap.add_argument("--collapse-sections", action="store_true",
                    help="require the rungs that reduce a repeated section to a reference line (the default)")
    ap.add_argument("--expand-sections", action="store_true",
                    help="keep a repeated section drawn out instead of reducing it to a reference line")
    ap.add_argument("--template", default=None, help="the chart format file (default: the skill's)")
    ap.add_argument("--allow-lossy", action="store_true",
                    help="write the PDF even if non-Latin text had to become '?'")
    args = ap.parse_args(argv)
    data, stats = render(read_song(args.song), args.paper, args.collapse_sections, args.template, args.expand_sections)
    for wmsg in _WARNINGS:
        print("warning: %s" % wmsg, file=sys.stderr)
    if not args.allow_lossy and any(m.startswith("lossy:") for m in _WARNINGS):
        print("refused: non-Latin text would print as '?'. Install Pillow "
              "(python3 -m venv v && v/bin/pip install pillow) or pass --allow-lossy.",
              file=sys.stderr)
        return 2
    with open(args.out, "wb") as fh:
        fh.write(data)
    print("wrote %s  (%s bytes)  %s" % (args.out, format(len(data), ","),
                                       "  ".join("%s=%s" % kv for kv in stats.items())))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
