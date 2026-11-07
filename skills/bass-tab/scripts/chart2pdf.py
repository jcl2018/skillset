#!/usr/bin/env python3
"""Render a song file straight to a compact play-along chart PDF (1-2 pages).

    python3 chart2pdf.py <slug>/<slug>.py -o <slug>/<slug>.pdf [--paper letter|a4]

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
from tabcore import SLOTS, STRINGS, rhythm_cells
from tabgen import load_song
from chartplan import LADDER, UNIT, bar_width, pack, plan_units, slot_widths

MAX_PAGES = 2
CLEF = 11.0                      # room left of the stave for the T A B clef
SHORT = {"8": 1, "3": 1, "6": 2}


def read_song(path):
    m = load_song(path)
    meta = m.META
    return {"meta": meta, "bars": m.BARS, "sections": m.SECTIONS,
            "chords": getattr(m, "CHORDS", None) or {}, "lyrics": getattr(m, "LYRICS", {}) or {},
            "caveats": getattr(m, "CAVEATS", []), "slots": int(meta.get("slots", SLOTS))}


def line_height(line, song, cfg):
    g = cfg.fs * 1.05
    if line[0]["kind"] == "ref":
        return 16.0
    bars = [b for u in line for b in u["bars"]]
    h = 3 + 3 * g + 5
    if any(u["label"] for u in line):
        h += 12
    if any(song["chords"].get(b) for b in bars):
        h += 10
    if cfg.rhythm:
        h += 1.4 * g + 3
    if any(song["lyrics"].get(b) for b in bars):
        h += 11
    return h + 4


def header_lines(song):
    meta = song["meta"]
    bits = ["%s: %s" % (k, "%s BPM" % meta[k] if k == "tempo" else meta[k])
            for k in ("key", "tempo", "time", "tuning") if meta.get(k)]
    return bits


def foot_blocks(song, usable):
    out = []
    for title, body in song["caveats"]:
        out += wrap_to_width("%s: %s" % (title, " ".join(body)), "F3", 7.0, usable)
    return out


def paginate(song, cfg, w, h):
    usable = w - 2 * MARGIN
    avail = usable - CLEF
    lines = pack(plan_units(song, cfg, avail - 20), avail)
    top = h - MARGIN
    bottom = MARGIN + 26
    head = 26 + (12 if header_lines(song) else 0) + 8
    notes = foot_blocks(song, usable)
    pages, cur, y = [], [], top - head
    for ln in lines:
        lh = line_height(ln, song, cfg)
        if y - lh < bottom:
            pages.append(cur)
            cur, y = [], top
        cur.append((ln, y, lh))
        y -= lh
    pages.append(cur)
    if y - 10 * len(notes) < bottom and notes:
        pages.append([])
    return pages, lines, notes


def draw_bar(pdf, song, cfg, num, x0, bw, ys, g):
    bar, slots = song["bars"][num], song["slots"]
    nat = slot_widths(bar, cfg)
    k = (bw - 6) / sum(nat)
    xs, x = [], x0 + 3
    for wd in nat:
        xs.append(x + wd * k / 2.0)
        x += wd * k
    fs = cfg.fs
    for i, sl in enumerate(bar):
        for st, (fret, art) in (sl or {}).items():
            y = ys[STRINGS.index(st)]
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
    base, end = ys[3] - g * 0.5, ys[3] - g * 1.4
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
    g = cfg.fs * 1.05
    if ln[0]["kind"] == "ref":
        u = ln[0]
        lab, _ = fit_to_width(u["label"], "F2", 10.0, usable * 0.6)
        pdf.text(MARGIN, y - 11, lab, "F2", 10.0)
        pdf.text(MARGIN + string_width(lab, "F2", 10.0) + 6, y - 11, u["text"], "F4", 9.0, gray=0.3)
        return
    avail = usable - CLEF
    fixed = sum(18 for u in ln if u["reps"] > 1)
    sum_bars = sum(u["width"] for u in ln) - fixed
    f = 1.0 if last else max(1.0, min(1.4, (avail - fixed) / sum_bars))
    cy = y - 3
    if any(u["label"] for u in ln):
        cy -= 12
    lab_y = y - 3 - 10
    has_chord = any(song["chords"].get(b) for u in ln for b in u["bars"])
    if has_chord:
        cy -= 10
    chord_y = cy + 1
    ys = [cy - 5 - g * i for i in range(4)]
    pdf.rule(x_left, ys[0], x_left, ys[3])
    x = x_left
    for u in ln:
        reps = u["reps"] > 1
        x_start = x
        if reps:
            pdf.repeat_bar(x, ys[3] - 0.5, ys[0] + 0.5, opening=True)
            x += 9
        for bi, num in enumerate(u["bars"]):
            bw = bar_width(num, song, cfg) * f
            for yy in ys:
                pdf.rule(x, yy, x + bw, gray=0.45)
            if bi == 0 and not reps:
                pdf.stem(x, ys[3] - 0.5, ys[0] + 0.5, w=0.7)
            if bi == 0 and u["label"]:
                pdf.text(x + 1, lab_y, u["label"], "F2", 10.0)
            ch = song["chords"].get(num)
            if ch:
                pdf.text(x + 2, chord_y, ch, "F2", 9.0, gray=0.15)
            draw_bar(pdf, song, cfg, num, x, bw, ys, g)
            lyr = song["lyrics"].get(num)
            if lyr:
                pdf.text(x + 2, ys[3] - (1.4 * g + 3 if cfg.rhythm else 0) - 9, lyr, "F3", 8.5)
            x += bw
            if not (reps and bi == len(u["bars"]) - 1):
                pdf.stem(x, ys[3] - 0.5, ys[0] + 0.5, w=0.7)
        if reps:
            x += 9
            pdf.repeat_bar(x, ys[3] - 0.5, ys[0] + 0.5, opening=False)
            lbl = "x%d" % u["reps"]
            pdf.text(x - string_width(lbl, "F2", 9.0), ys[0] + 3.5, lbl, "F2", 9.0)
    clef = 7.5
    for k, ch in enumerate("TAB"):
        pdf.text(MARGIN + 1.5, ys[0] - 3 - k * (g * 0.95) - clef * 0.3 + g * 0.35, ch, "F2", clef)


def render(song, paper, refs_only=False):
    w, h = PAPERS[paper]
    usable = w - 2 * MARGIN
    title = song["meta"].get("title", "Bass tab")
    cfg = pages = lines = notes = None
    for cand in [c for c in LADDER if c.secref or not refs_only]:
        pages, lines, notes = paginate(song, cand, w, h)
        if len(pages) <= MAX_PAGES:
            cfg = cand
            break
    if cfg is None:
        raise SystemExit("chart2pdf: %s does not fit %d pages at %.0f pt tab digits "
                         "(needs %d). Cut bars or split the song."
                         % (title, MAX_PAGES, LADDER[-1].fs, len(pages)))
    pdf = PDF(w, h)
    artist = song["meta"].get("artist", "")
    last_line = lines[-1]
    for pi, pg in enumerate(pages):
        pdf.new_page()
        if pi == 0:
            t, ts = fit_to_width(title, "F2", 17.0, usable * 0.62, min_size=11.0)
            tx = h - MARGIN - ts
            pdf.text(MARGIN, tx, t, "F2", ts)
            if artist:
                a, _ = fit_to_width(artist, "F3", 10.0, usable - string_width(t, "F2", ts) - 14)
                pdf.text(w - MARGIN - string_width(a, "F3", 10.0), tx, a, "F3", 10.0, gray=0.25)
            hb = "   ·   ".join(header_lines(song))
            if hb:
                hb, _ = fit_to_width(hb, "F3", 8.0, usable)
                pdf.text(MARGIN, tx - 13, hb, "F3", 8.0, gray=0.35)
            pdf.rule(MARGIN, tx - 19, w - MARGIN)
        for ln, y, lh in pg:
            draw_line(pdf, song, cfg, ln, y, lh, usable, ln is last_line, MARGIN + CLEF)
        if pi == len(pages) - 1 and notes:
            yy = (pg[-1][1] - pg[-1][2]) if pg else h - MARGIN
            for n in notes:
                yy -= 9
                pdf.text(MARGIN, yy, n, "F3", 7.0, gray=0.4)
    pdf.flush()
    total = len(pdf.pages)
    label = "%s — %s" % (title, artist) if artist else title
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
    return pdf.build(title, artist), stats


def main(argv=None):
    ap = argparse.ArgumentParser(description="Song file -> compact chart PDF.")
    ap.add_argument("song", help="the <slug>.py song file")
    ap.add_argument("-o", "--out", required=True)
    ap.add_argument("--paper", choices=sorted(PAPERS), default="letter")
    ap.add_argument("--collapse-sections", action="store_true",
                    help="start at the rung that reduces a repeated section to a reference line")
    ap.add_argument("--allow-lossy", action="store_true",
                    help="write the PDF even if non-Latin text had to become '?'")
    args = ap.parse_args(argv)
    data, stats = render(read_song(args.song), args.paper, args.collapse_sections)
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
