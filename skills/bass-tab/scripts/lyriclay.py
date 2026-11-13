"""The lyric band under a stave, for chart2pdf: where it sits and how a long lyric fits its bar.

GENERAL - knows no song. A lyric is drawn in a band under the lowest string and under the rhythm row, never on a
string or a digit. One that is wider than its bar first widens the bar (chartplan.natural, up to LYRIC_CAP of
the line), then wraps onto a second lyric line, then shrinks to the template's lyrics.min_size, and only then is cut.
"""

from __future__ import annotations

from pdfkit import fit_to_width, string_width, wrap_to_width

LYRIC_CAP = 0.5        # a bar widens for its lyric up to this share of the line
STEP = 1.2             # lyric line pitch, in em
MAX_LINES = 2


def fit(lyr, bw, t):
    """(lines, size) for LYR in a bar BW wide: one line, else wrapped to two, shrinking to the minimum."""
    room, size = bw - 4.0, t.lyrics.size
    while True:
        if string_width(lyr, "F3", size) <= room:
            return [lyr], size
        lines = wrap_to_width(lyr, "F3", size, room)
        if len(lines) <= MAX_LINES:
            return lines, size
        if size - 0.5 < t.lyrics.min_size:
            break
        size -= 0.5
    size = t.lyrics.min_size
    lines = wrap_to_width(lyr, "F3", size, room)
    last, _ = fit_to_width(" ".join(lines[MAX_LINES - 1:]), "F3", size, room)
    return lines[:MAX_LINES - 1] + [last], size


def clear(g, rhythm):
    """Gap from the lowest string line to the top of the lyric band: past the digits, or past the rhythm row."""
    return 1.4 * g + 3 if rhythm else 0.5 * g + 2


def height(line, song, cfg, g, bar_width):
    """Room a stave line reserves under its lowest string for the rhythm gap and its lyric lines."""
    n, size = 0, cfg.t.lyrics.size
    for b in (b for u in line for b in u["bars"]):
        lyr = song["lyrics"].get(b)
        if lyr:
            n = max(n, len(fit(lyr, bar_width(b, song, cfg), cfg.t)[0]))
    return 0.0 if not n else (0.0 if cfg.rhythm else clear(g, False)) + n * size * STEP


def draw(pdf, lyr, x, bw, y_low, g, cfg):
    """Draw LYR in the bar at X (width BW) whose lowest string is at Y_LOW."""
    lines, size = fit(lyr, bw, cfg.t)
    top = y_low - clear(g, cfg.rhythm)
    for k, ln in enumerate(lines):
        pdf.text(x + 2, top - 0.95 * size - k * size * STEP, ln, "F3", size)
