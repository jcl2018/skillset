#!/usr/bin/env python3
"""Render a song's structured data into an aligned ASCII bass tab.

GENERAL - it knows nothing about any particular song. A song supplies a data
module (META / BARS / SECTIONS / CHORDS); this turns it into the .tab that
tab2pdf.py renders. Repeated figures are encoded ONCE in the data, so a
correction to one reaches every place it is played.

Each system carries, above the staves:
    section name + bar range + a timestamp computed from the tempo
    the chord under each bar
    the bar number
which is what lets you see where you are in the song while playing it.
"""

from __future__ import annotations

import importlib.util
import sys

from tabcheck import verification_lines
from tabcore import (
    SLOT_W, SLOTS, STRINGS, bar_note, collapse_runs, open_pitches, render_slot,
    rhythm_cells, row_label, section_ranges, timestamp,
)


def load_song(path):
    spec = importlib.util.spec_from_file_location("song", path)
    m = importlib.util.module_from_spec(spec)
    sys.modules["song"] = m
    spec.loader.exec_module(m)
    return m


def identity_sentence(start, other, ranges, bars):
    """How this section relates to an earlier one, DERIVED FROM THE BARS.

    Tail-aligned, so a section carrying an extra lead-in bar still matches the
    block it repeats. Any difference is named. Parameterised rather than closing
    over module globals, which is what lets one engine serve every song.
    """
    a1, b1 = ranges[start]
    a2, b2 = ranges[other]
    n = min(b1 - a1 + 1, b2 - a2 + 1)
    lo1, lo2 = b1 - n + 1, b2 - n + 1
    diff = [lo1 + i for i in range(n) if bars[lo1 + i] != bars[lo2 + i]]
    where = "bars %d-%d" % (lo2, b2)
    if not diff:
        return "Note-for-note the same as %s." % where
    if len(diff) == 1:
        return "The same as %s, except bar %d." % (where, diff[0])
    return "The same as %s, except bars %s and %d." % (
        where, ", ".join(str(d) for d in diff[:-1]), diff[-1])


def repeat_sentence(start, ranges, sections, bars):
    """Where else this block is played. Derived, so it cannot over-claim."""
    later = [k for k, v in sections.items() if v.get("same_as") == start]
    if not later:
        return None
    parts = []
    for k in sorted(later):
        a, b = ranges[k]
        n = min(b - a + 1, ranges[start][1] - ranges[start][0] + 1)
        lo1, lo2 = b - n + 1, ranges[start][1] - n + 1
        d = [lo1 + i for i in range(n) if bars[lo1 + i] != bars[lo2 + i]]
        note = "" if not d else (" (bar %d differs)" % d[0] if len(d) == 1
                                 else " (bars %s differ)" % ", ".join(str(x) for x in d))
        parts.append("%d-%d%s" % (lo1, b, note))
    return "Played again at bars %s." % ", ".join(parts)


def build(song, bars_per_system=3, cut="full"):
    BARS, SECTIONS = song.BARS, song.SECTIONS
    opens = open_pitches(song.META)
    CHORDS = getattr(song, "CHORDS", None) or {n: bar_note(b, opens) for n, b in song.BARS.items()}
    LYRICS = getattr(song, "LYRICS", {})          # the user's row; never written here
    M, tempo = song.META, song.META.get("tempo")
    compact = cut == "compact"

    L = []
    for k in ("title", "artist", "key", "tempo", "time", "tuning", "source", "legend"):
        v = M.get(k) or ("; ".join(M["sources"]) if k == "source" and M.get("sources") else "")
        if v:
            L.append("%s: %s" % (k, "%s BPM" % v if k == "tempo" else v))
    L.append("")
    if not compact and getattr(song, "HEADER", None):
        L.append("[How to read this]")
        for h in song.HEADER:
            L.append("> " + h)
        L.append("")

    ranges = section_ranges(SECTIONS, BARS)
    slots = int(M.get("slots", SLOTS))
    cw = SLOT_W * slots + 1
    # the ruler is DERIVED from the slot count, never a second hard-coded list -
    # a ruler that disagreed with the grid would mislabel every beat on the page
    _sub = {2: ("", "&"), 4: ("", "e", "&", "a")}.get(slots // 4, ("",) * (slots // 4))
    ruler = "".join((str(i // (slots // 4) + 1) if i % (slots // 4) == 0
                     else _sub[i % (slots // 4)]).ljust(SLOT_W) for i in range(slots))

    for start in sorted(SECTIONS):
        a, b = ranges[start]
        sec = SECTIONS[start]
        ts = timestamp(a, tempo)
        L.append("[%s  -  bars %d-%d%s]" % (sec["name"], a, b,
                                            "   .  " + ts if ts else ""))
        if not compact:
            notes = list(sec.get("notes") or [])
            if sec.get("same_as"):
                notes.insert(0, identity_sentence(start, sec["same_as"], ranges, BARS))
            else:
                rs = repeat_sentence(start, ranges, SECTIONS, BARS)
                if rs:
                    notes.append(rs)
            for n in notes:
                L.append("> " + n)
        L.append("")

        runs = collapse_runs(list(range(a, b + 1)), BARS, LYRICS) if compact \
               else [[n, n, 1] for n in range(a, b + 1)]
        # A run of period p prints p bar COLUMNS; the label rides the first one,
        # so the figure is shown once and the repeat count is stated beside it.
        cols = []
        for lo, hi, p in runs:
            reps = (hi - lo + 1) // p
            for k in range(p):
                if reps == 1:
                    lab = str(lo + k)
                elif k == 0:
                    lab = "%d-%d  x%d" % (lo, hi, reps)
                else:
                    lab = ""
                cols.append((lo + k, lab))
        for i in range(0, len(cols), bars_per_system):
            chunk = cols[i:i + bars_per_system]
            crow = ("  " + "".join((CHORDS.get(c[0], "") or "").ljust(cw) for c in chunk)).rstrip()
            if crow.strip():
                L.append(crow)
            L.append(("  " + "".join(c[1].ljust(cw) for c in chunk)).rstrip())
            if not compact:
                L.append(("  " + " ".join([ruler] * len(chunk))).rstrip())
            L.append("R|" + "".join(rhythm_cells(BARS[c[0]], slots) + "|" for c in chunk))
            for st in STRINGS:
                L.append(row_label(M, st) + "|" + "".join(
                    "".join(render_slot(sl, st) for sl in BARS[c[0]]) + "|" for c in chunk))
            lrow = ("  " + "".join((LYRICS.get(c[0], "") or "").ljust(cw) for c in chunk)).rstrip()
            if lrow.strip():
                L.append(lrow)
            L.append("")

    def emit(blocks):
        for title, body in blocks or []:
            L.append("[%s]" % title)
            for line in body:
                L.append("> " + line)
            L.append("")

    if not compact:
        emit(getattr(song, "FOOTER", []))

    # CAVEATS print in EVERY cut, including compact. A footer is prose and the
    # compact cut exists to drop prose; a caveat records what the sheet does not
    # know, and a sheet that stays silent about that in the one cut people
    # actually play from is worse than no sheet. Trimming this would re-open the
    # exact failure it exists to close.
    emit(getattr(song, "CAVEATS", []))

    # WHAT WAS CHECKED, printed on the sheet itself. A claim that lives only in
    # a commit message is a claim the reader cannot see; this puts the check and
    # its result in the reader's hands.
    _w = sorted({len(l) for l in L if l[:2] in ("G|", "D|", "A|", "E|")})
    emit([("Checked", verification_lines(song, slots, bars_per_system, _w, compact))])
    return "\n".join(L).rstrip("\n") + "\n"


def main(argv=None):
    a = argv or sys.argv[1:]
    if len(a) < 2:
        print("usage: tabgen.py <song.py> <out.tab> [--bars N]", file=sys.stderr)
        return 2
    n = int(a[a.index("--bars") + 1]) if "--bars" in a else 3
    cut = a[a.index("--cut") + 1] if "--cut" in a else "full"
    song = load_song(a[0])
    meta, name = song.META, song.META.get("title", a[0])
    if meta.get("strings", 4) != 4:
        print("tabgen: %s is %s-string; render it with chart2pdf.py" % (name, meta.get("strings")),
              file=sys.stderr)
        return 2
    if meta.get("source") and meta.get("sources"):
        print("%s sets both source and sources; keep one" % name, file=sys.stderr)
        return 2
    text = build(song, n, cut)
    open(a[1], "w", encoding="utf-8").write(text)
    want = int(song.META.get("slots", SLOTS))
    bad = [k for k, v in song.BARS.items() if len(v) != want]
    print("bars=%d range=%d-%d malformed=%s  widths=%s"
          % (len(song.BARS), min(song.BARS), max(song.BARS), bad or "none",
             sorted({len(l) for l in text.split("\n") if l[:2] in ("G|", "D|", "A|", "E|")})))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
