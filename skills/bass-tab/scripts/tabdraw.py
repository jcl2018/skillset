"""Stave, repeat-label and rhythm drawing helpers for tab2pdf."""

from __future__ import annotations

import re

from pdfdraw import PDF


META_ORDER = ["artist", "album", "tuning", "capo", "key", "tempo", "time",
              "difficulty", "source", "transcribed", "notes"]


RHYTHM_BAND = 36.0     # the rhythm band under a stave: digit clearance + a 2.2-gap stem + the flag's sweep
_HOLLOW = {"2", "D", "1"}
_DOTTED = {"d", "D", "3"}
_SHORT = {"8": 1, "3": 1, "6": 2}     # notes shorter than a beat, and how many beams/flags each takes


TAB_ROW_RE = re.compile(r"^[GDAE]\|")


_REPEAT_RE = re.compile(r"(\d+)-(\d+)\s+(x(\d+))")


def strip_repeats(row: str):
    """Pull the `xN` repeat labels out of a bar-number row.

    Returns the row with the count blanked (column positions preserved, because
    every other row aligns to those columns) and, per run, the column it sits
    at, the repeat count, and how many BARS the repeated figure spans. The span
    is derived from the label's own bar range - a run reading `2-9  x4` repeats
    a 2-bar figure - so the bracket can be drawn around the whole figure rather
    than around its first bar.
    """
    found, out = [], list(row)
    for m in _REPEAT_RE.finditer(row):
        lo, hi, reps = int(m.group(1)), int(m.group(2)), int(m.group(4))
        span = max(1, (hi - lo + 1) // max(1, reps))
        found.append((m.start(3), reps, span))
        for k in range(m.start(3), m.end(3)):
            out[k] = " "
    return "".join(out).rstrip(), found


def draw_tab_row(pdf, row, x0, baseline, adv, size):
    """Draw one string of the tab as a REAL RULED LINE, not a row of hyphens.

    A tab stave is a line with numbers sitting on it. Rendering that as ASCII
    dashes was a transcription of the plain-text file rather than of the thing
    the file represents - it reads as dotted, and at small sizes the hyphens
    blur into the digits. So the dashes are never drawn: each RUN of them
    becomes one horizontal rule, every "|" becomes a vertical rule tall enough
    to meet its neighbours in the rows above and below (so barlines close up
    into one continuous line across the stave), and only the real glyphs - fret
    numbers and their articulations - are drawn as text.

    x is still derived from the CHARACTER INDEX times the monospace advance, so
    the column grid is byte-for-byte the one the .tab file defines. The picture
    changes; the alignment does not.
    """
    mid = baseline + size * 0.30          # the line passes through the digits
    top = baseline + size * 0.70
    bot = baseline - size * 0.40          # meets the next row's `top`
    # A slide is DRAWN, not spelled. "7s" printed the letter s in a column of its
    # own, which reads as a fret number to the eye; the source draws a line from
    # the note you leave to the note you land on. So the s is suppressed and a
    # diagonal is drawn to the next fret on this same string.
    slides = []
    for i, c in enumerate(row):
        if c == "s" and i and row[i - 1].isdigit():
            j = i + 1
            while j < len(row) and row[j] in "-|":
                j += 1
            if j < len(row) and row[j].isdigit():
                slides.append((i, j))          # slide INTO the landing note
            else:
                # A slide off the last bar of a system has no landing note on
                # this row - the note it reaches is on the next line. Drawing
                # nothing would silently lose the articulation, so draw the
                # outgoing stroke to where the row ends.
                slides.append((i, min(i + 2, len(row) - 1)))

    skip = {i for i, _ in slides}
    skip.add(0)                       # the string letter: Guitar Pro prints a TAB clef instead
    i, n = 0, len(row)
    while i < n:
        c = row[i]
        if i == 0:
            i += 1
            continue
        if c == "-" or i in skip:
            j = i
            while j < n and (row[j] == "-" or j in skip):
                j += 1
            pdf.rule(x0 + i * adv, mid, x0 + j * adv, gray=0.45)
            i = j
            continue
        if c == "|":
            pdf.stem(x0 + (i + 0.5) * adv, bot, top, w=0.6)
        elif c != " ":
            pdf.text(x0 + i * adv, baseline, c, "F1", size)
        i += 1

    for a, b in slides:
        pdf.slide(x0 + (a - 0.15) * adv, mid - size * 0.16,
                  x0 + (b + 0.15) * adv, mid + size * 0.16)


def draw_rhythm(pdf: "PDF", row: str, x0: float, baseline: float, adv: float,
                g: float, mid_y: float) -> None:
    """Draw the R| row the way Guitar Pro draws a tab's rhythm.

    Stems hang DOWN from under each fret number, 2.2 stave gaps long; an eighth
    takes a curved flag or shares a beam with its beat-mates, a sixteenth two
    beams; a half shows a small hollow head, a whole no stem at all. Rests are
    drawn ON the stave: a quarter rest as the zigzag and an eighth as the
    dot-and-stroke, centred on the middle of the stave at `mid_y`.

    x is derived from the CHARACTER INDEX and the monospace advance, which is
    why a stem lands exactly under its own fret number - the two cannot drift.
    `baseline` is the bottom stave line, where the stems start.
    """
    heads = [(i, c) for i, c in enumerate(row) if c in "638d42D1"]
    stem_top = baseline - 0.95 * g           # clear of the digit sitting on the line
    stem_end = stem_top - 2.2 * g
    sw = 0.07 * g                              # stem width: 3 of 44 px on the reference
    for i, c in heads:
        cx = x0 + (i + 0.5) * adv
        if c in _HOLLOW:
            pdf.notehead(cx, stem_end - 0.22 * g, 0.30 * g, 0.22 * g, filled=False)
        if c != "1":
            pdf.stem(cx, stem_top, stem_end, w=sw)
        if c in _DOTTED:
            pdf.dot(cx + 0.35 * g, stem_end + 0.25 * g, 0.11 * g)
    for i, c in enumerate(row):
        if i == 0:
            continue                             # the "R" of "R|" is the row label
        cx = x0 + (i + 0.5) * adv
        if c == "R":
            pdf.quarter_rest(cx, mid_y, g)
        elif c == "r":
            pdf.eighth_rest(cx, mid_y, g)

    # Notes shorter than a beat are grouped BY BEAT, the way printed music
    # groups them: two or more in one beat share a beam, a sixteenth adds a
    # second beam, and one alone in its beat takes a flag.
    seps = [k for k, ch in enumerate(row) if ch == "|"]
    beat_of = {}
    for a, b in zip(seps, seps[1:]):
        width = (b - a - 1) / 4.0
        for i, c in heads:
            if a < i < b and c in _SHORT and width > 0:
                beat_of[i] = (a, int((i - a - 1) // width))
    groups: dict = {}
    for i, c in heads:
        if i in beat_of:
            groups.setdefault(beat_of[i], []).append((i, c))
    stem_x = lambda i: x0 + (i + 0.5) * adv
    bh = 0.39 * g                              # beam thickness: 17 of 44 px on the reference
    y1, y2 = stem_end, stem_end + bh + 0.22 * g
    for notes in groups.values():
        if len(notes) == 1:
            i, c = notes[0]
            for k in range(_SHORT[c]):
                pdf.flag(stem_x(i) + sw / 2.0, stem_end + 0.5 * g * k, g)
            continue
        pdf.beam(stem_x(notes[0][0]) - sw / 2.0, y1, stem_x(notes[-1][0]) + sw / 2.0, h=bh)
        for j, (i, c) in enumerate(notes):
            if _SHORT[c] < 2:
                continue
            nxt = notes[j + 1] if j + 1 < len(notes) else None
            prv = notes[j - 1] if j else None
            if nxt and _SHORT[nxt[1]] == 2:
                pdf.beam(stem_x(i) - sw / 2.0, y2, stem_x(nxt[0]) + sw / 2.0, h=bh)
            elif not (prv and _SHORT[prv[1]] == 2):
                stub = 0.5 * g
                if prv:
                    pdf.beam(stem_x(i) - stub, y2, stem_x(i) + sw / 2.0, h=bh)
                else:
                    pdf.beam(stem_x(i) - sw / 2.0, y2, stem_x(i) + stub, h=bh)
