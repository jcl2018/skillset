#!/usr/bin/env python3
"""Render a plain-text bass-tab source into a print-ready PDF.

Zero third-party dependencies for the core: the PDF is written by hand using the
base-14 fonts (Courier for the staves, Helvetica for headings), so tab lines stay
crisp vector text at any zoom and the file stays small.

Non-Latin-1 text (a CJK song title, say) cannot be expressed in a base-14 font, so
those runs — and ONLY those runs — are rasterized with Pillow using a system font
that covers the glyphs and placed as an image. The tab body itself is ASCII by
nature, so it is always vector.

Input grammar (UTF-8 text file)
-------------------------------
  key: value            leading metadata lines (title/artist/tuning/tempo/key/...)
  [Section name]        a bold section heading
  > free prose          an italic annotation line
  anything else         verbatim monospace (the tab staves), spacing preserved
  blank line            block separator + vertical gap

A run of consecutive monospace lines is one block and is never split across a page
break if it fits on a page by itself, so a 4-string stave stays whole.

Usage
-----
  python3 tab2pdf.py song.tab -o song.pdf [--paper a4|letter] [--check]
"""

import argparse
import re
import sys

from pdfdraw import PDF
from pdfkit import (
    _WARNINGS, COURIER_ADVANCE, FOOTER_GAP, FOOTER_SIZE, MARGIN, NOTE_SIZE, PAPERS,
    SECTION_BREAK_FRAC, SECTION_SIZE, TAB_SIZE_MAX, TAB_SIZE_MIN, TITLE_SIZE, ARTIST_SIZE,
    META_SIZE, Block, Song, fit_to_width, parse_source, string_width, wrap_to_width,
)


from tabdraw import (
    META_ORDER, RHYTHM_BAND, TAB_ROW_RE, draw_rhythm, draw_tab_row, strip_repeats,
)


TAB_CHARS_MAX = 77          # the template's line: 8 slots x 3 bars, + the "E|"


def fit_tab_size(song: Song, usable: float) -> tuple[float, int]:
    """The PINNED tab size, plus the longest line found.

    This used to size the font to fit the content, which meant every song got
    its own scale: a 16-slot song shrank to 8.5pt and a heavily-collapsed one
    grew to the 12pt cap, so two sheets printed side by side did not match. The
    size is now DERIVED from the template's fixed maximum line (77 chars) and is
    the same for every sheet, whatever it contains.

    A song whose lines exceed that maximum is REFUSED rather than quietly
    shrunk. Silent shrinking is what produced the drift; the fix for an over-long
    line is fewer bars per system, which is the author's call to make.
    """
    longest = 0
    for blk in song.blocks:
        for ln in blk.lines:
            if ln.kind == "mono":
                longest = max(longest, len(ln.text))
    size = usable / (COURIER_ADVANCE * TAB_CHARS_MAX)
    if longest > TAB_CHARS_MAX:
        raise SystemExit(
            "tab2pdf: longest line is %d chars, over the template maximum of %d.\n"
            "         Re-render with fewer bars per system (tabgen --bars N).\n"
            "         Shrinking the font instead would make this sheet a "
            "different scale from every other one."
            % (longest, TAB_CHARS_MAX))
    return size, longest


def render(song: Song, paper: str, sec_frac: float = SECTION_BREAK_FRAC) -> tuple[bytes, dict]:
    w, h = PAPERS[paper]
    pdf = PDF(w, h)
    usable = w - 2 * MARGIN
    tab_size, longest = fit_tab_size(song, usable)
    mono_leading = tab_size * 0.98   # tighter: the stave is ruled, not hyphens
    title = song.meta.get("title", "Bass tab")
    artist = song.meta.get("artist", "")

    pdf.new_page()
    y = h - MARGIN

    # ---- title block (page 1). Every proportional string is MEASURED: a title
    # that overruns used to be silently clipped at the page edge.
    t_text, t_size = fit_to_width(title, "F2", TITLE_SIZE, usable, min_size=12.0)
    pdf.text(MARGIN, y - t_size, t_text, "F2", t_size)
    y -= t_size + 6
    if artist:
        for aline in wrap_to_width(artist, "F3", ARTIST_SIZE, usable):
            pdf.text(MARGIN, y - ARTIST_SIZE, aline, "F3", ARTIST_SIZE, gray=0.25)
            y -= ARTIST_SIZE + 4
        y -= 2
    meta_bits = [(k, song.meta[k]) for k in META_ORDER
                 if k in song.meta and song.meta[k] and k != "artist"]
    for k in sorted(song.meta):
        if k not in META_ORDER and k != "title" and song.meta[k]:
            meta_bits.append((k, song.meta[k]))
    if meta_bits:
        y -= 2
        pdf.rule(MARGIN, y, w - MARGIN)
        y -= META_SIZE + 5
        sep = "   \u00b7   "
        line, lines = "", []
        for k, v in meta_bits:
            bit = f"{k}: {v}"
            trial = f"{line}{sep}{bit}" if line else bit
            if line and string_width(trial, "F3", META_SIZE) > usable:
                lines.append(line)
                line = bit
            else:
                line = trial
        if line:
            lines.append(line)
        for ln in lines:
            # A single metadata value can still be longer than the page on its own.
            for piece in wrap_to_width(ln, "F3", META_SIZE, usable):
                pdf.text(MARGIN, y, piece, "F3", META_SIZE, gray=0.35)
                y -= META_SIZE + 3
        y -= 3
        pdf.rule(MARGIN, y, w - MARGIN)
        y -= 12

    bottom = MARGIN + FOOTER_GAP

    def note_pieces(text: str) -> list[str]:
        return wrap_to_width(text, "F4", NOTE_SIZE, usable)

    def block_height(blk: Block) -> float:
        tot = 0.0
        for ln in blk.lines:
            if ln.kind == "section":
                tot += SECTION_SIZE + 4
            elif ln.kind == "note":
                # Height must count the WRAPPED lines, or pagination lies.
                tot += len(note_pieces(ln.text)) * (NOTE_SIZE + 2)
            elif ln.text.startswith("R|"):
                tot += RHYTHM_BAND
            else:
                tot += mono_leading
        return tot

    blocks = song.blocks
    pending_repeats: list = []
    repeat_carry = 0          # bars of an open repeat still to come on later staves
    for bi, blk in enumerate(blocks):
        bh = block_height(blk)
        need = bh
        # A heading block introduces the block AFTER it - parse_source split them
        # at the blank line between. Reserving only the heading's own height lets
        # it land alone at the page foot with its stave overleaf, so reserve both.
        if any(ln.kind == "section" for ln in blk.lines) and bi + 1 < len(blocks):
            # Reserve the WHOLE next block, not a slice of it: a stave is six
            # lines, so reserving four still let the stave break to the next page
            # and stranded the heading anyway. If the pair genuinely cannot fit on
            # one page, the guard below declines the break rather than looping.
            need = bh + block_height(blocks[bi + 1])
        starts_section = any(ln.kind == "section" for ln in blk.lines)
        column = (h - MARGIN) - bottom
        # A page turn in the middle of a phrase costs the player the phrase. If a
        # new section is starting and less than SECTION_BREAK_FRAC of the column
        # is left, turn the page HERE, so the turn lands on a musical seam.
        if starts_section and y - bottom < column * sec_frac:
            pdf.new_page()
            y = h - MARGIN
        elif y - need < bottom and need <= column:
            pdf.new_page()
            y = h - MARGIN
        tab_run = 0                 # consecutive tab rows; the 4th closes the stave
        held_rhythm = None          # the R| row, drawn under the stave once it closes
        drew_rhythm = False         # whether this stave's band is already below `y`
        for ln in blk.lines:
            tab_run = tab_run + 1 if TAB_ROW_RE.match(ln.text) else 0
            if ln.kind == "section":
                if y - (SECTION_SIZE + 4) < bottom:
                    pdf.new_page()
                    y = h - MARGIN
                y -= SECTION_SIZE + 2
                head, _ = fit_to_width(ln.text, "F2", SECTION_SIZE, usable)
                pdf.text(MARGIN, y, head, "F2", SECTION_SIZE)
                y -= 6
            elif ln.kind == "note":
                for piece in note_pieces(ln.text):
                    if y - (NOTE_SIZE + 4) < bottom:
                        pdf.new_page()
                        y = h - MARGIN
                    y -= NOTE_SIZE + 1
                    pdf.text(MARGIN, y, piece, "F4", NOTE_SIZE, gray=0.3)
                    y -= 3
            elif ln.text.startswith("R|"):
                # Held back: the text tab prints the rhythm row above the stave,
                # Guitar Pro draws it below. Drawn once the 4th tab row lands.
                held_rhythm = ln.text
            else:
                if y - mono_leading < bottom:
                    pdf.new_page()
                    y = h - MARGIN
                y -= mono_leading
                if TAB_ROW_RE.match(ln.text):
                    draw_tab_row(pdf, ln.text, MARGIN, y,
                                 tab_size * COURIER_ADVANCE, tab_size)
                    if tab_run == 1:
                        # Guitar Pro's clef: T, A, B stacked down the stave's
                        # left edge, one letter per gap, in place of string names.
                        clef = tab_size * 0.62
                        for k, ch in enumerate("TAB"):
                            pdf.text(MARGIN - 0.2, y + tab_size * 0.30 - clef * 0.78
                                     - k * mono_leading * 0.98 - 2.2, ch, "F2", clef)
                    if tab_run == 4 and held_rhythm is not None:
                        if y - RHYTHM_BAND < bottom:
                            pdf.new_page()
                            y = h - MARGIN
                        # Stems start ON the bottom stave line, as Guitar Pro
                        # draws them: the line the 4th row sits on is its
                        # `mid`, mirrored from draw_tab_row.
                        line_y = y + tab_size * 0.30
                        y -= RHYTHM_BAND
                        draw_rhythm(pdf, held_rhythm, MARGIN, line_y,
                                    tab_size * COURIER_ADVANCE,
                                    mono_leading, line_y + mono_leading * 1.5)
                        held_rhythm = None
                        drew_rhythm = True
                    if tab_run == 4 and (pending_repeats or repeat_carry):
                        # The 4th tab row closes the stave, so its extent is finally
                        # known: three leadings up to the top row. Counted, not
                        # matched on "E|", because a drop-D sheet labels it "D". Bar boundaries
                        # come from this row's OWN separators, so the bracket
                        # lands on real barlines whatever the slot count is.
                        adv = tab_size * COURIER_ADVANCE
                        stave_y = y + (RHYTHM_BAND if drew_rhythm else 0)
                        y0 = stave_y + tab_size * 0.30 - 0.6        # the bottom stave line
                        y1 = stave_y + mono_leading * 3 + tab_size * 0.30 + 0.6   # the top one
                        seps = [i for i, ch in enumerate(ln.text) if ch == "|"]
                        # A figure longer than one stave closes on a LATER stave,
                        # after its last bar. Closing it at this stave's end drew
                        # a 4-bar repeat around its first bar alone whenever the
                        # sheet prints one bar per line.
                        if repeat_carry:
                            if repeat_carry <= len(seps) - 1:
                                pdf.repeat_bar(MARGIN + seps[repeat_carry] * adv, y0, y1, opening=False)
                                repeat_carry = 0
                            else:
                                repeat_carry -= len(seps) - 1
                        for col, n, span in pending_repeats:
                            before = [x for x in seps if x <= col] or [1]
                            start = before[-1]
                            after = [x for x in seps if x > start]
                            xa = MARGIN + start * adv
                            pdf.repeat_bar(xa, y0, y1, opening=True)
                            if span <= len(after):
                                pdf.repeat_bar(MARGIN + after[span - 1] * adv, y0, y1, opening=False)
                            else:
                                repeat_carry = span - len(after)
                            lbl = "%dx" % n
                            # clear of the string letters to its left and of
                            # the notehead row above it
                            pdf.text(xa + 7.0, y1 - tab_size * 0.74, lbl, "F1", tab_size * 0.66)
                        pending_repeats = []
                else:
                    txt, pending_repeats = strip_repeats(ln.text)
                    pdf.text(MARGIN, y, txt, "F1", tab_size)
        y -= mono_leading * 0.18

    # ---- footers
    total = len(pdf.pages) + (1 if pdf._ops else 0)
    pdf.flush()
    label = f"{title} — {artist}" if artist else title
    for idx, (ops, imgs) in enumerate(zip(pdf.pages, pdf.page_images), start=1):
        pdf._ops, pdf._imgs = ops, imgs
        pdf.rule(MARGIN, MARGIN + FOOTER_GAP - 10, w - MARGIN, gray=0.85)
        pn = f"{idx} / {total}"
        pn_w = string_width(pn, "F3", FOOTER_SIZE)
        lab, _ = fit_to_width(label, "F3", FOOTER_SIZE, usable - pn_w - 18)
        pdf.text(MARGIN, MARGIN + 4, lab, "F3", FOOTER_SIZE, gray=0.45)
        pdf.text(w - MARGIN - pn_w, MARGIN + 4, pn, "F3", FOOTER_SIZE, gray=0.45)
    pdf._ops, pdf._imgs = [], set()

    stats = {
        "pages": total,
        "tab_font_pt": round(tab_size, 2),
        "longest_line": longest,
        "blocks": len(song.blocks),
        "mono_lines": sum(1 for b in song.blocks for l in b.lines if l.kind == "mono"),
        "sections": sum(1 for b in song.blocks for l in b.lines if l.kind == "section"),
        "rasterized_runs": len(pdf.raster.items()),
    }
    return pdf.build(title, artist), stats


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Plain-text bass tab -> PDF.")
    ap.add_argument("source", help="the .tab source file")
    ap.add_argument("-o", "--out", help="output .pdf (default: alongside the source)")
    ap.add_argument("--paper", choices=sorted(PAPERS), default="a4")
    ap.add_argument("--section-break-frac", type=float, default=SECTION_BREAK_FRAC,
                    help="start a section on a fresh page when less than this "
                         "fraction of the column is left (0 disables)")
    ap.add_argument("--check", action="store_true",
                    help="parse + report, write nothing")
    args = ap.parse_args(argv)

    with open(args.source, "r", encoding="utf-8") as fh:
        song = parse_source(fh.read())

    if not song.blocks:
        print("refused: no tab content found in %s" % args.source, file=sys.stderr)
        return 2

    data, stats = render(song, args.paper, args.section_break_frac)
    if stats["tab_font_pt"] <= TAB_SIZE_MIN + 0.01 and stats["longest_line"]:
        print("warning: longest tab line is %d chars — it is being squeezed to the "
              "%.1fpt floor. Split the measures for a readable print."
              % (stats["longest_line"], stats["tab_font_pt"]), file=sys.stderr)

    for wmsg in _WARNINGS:
        print("warning: %s" % wmsg, file=sys.stderr)
    report = "  ".join(f"{k}={v}" for k, v in stats.items())
    if args.check:
        print(f"OK (check, nothing written)  {report}")
        return 0

    out = args.out or re.sub(r"\.tab$", "", args.source) + ".pdf"
    with open(out, "wb") as fh:
        fh.write(data)
    print(f"wrote {out}  ({len(data):,} bytes)  {report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

