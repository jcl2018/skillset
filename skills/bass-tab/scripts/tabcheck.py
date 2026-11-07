"""The sheet's printed 'Checked' block: bars, repeats, marks, scale and key."""

from __future__ import annotations

import re

from tabcore import _NAMES, collapse_runs, open_pitches, section_ranges


MARK_VOCAB = {"h", "p", "s", "~"}


_MAJ = [0, 2, 4, 5, 7, 9, 11]


_MIN = [0, 2, 3, 5, 7, 8, 10]


def key_report(song):
    """Which notes fall outside the declared key, and how often.

    The signal is NOT "an out-of-key note exists" - a chromatic passing tone is
    ordinary in a bass line and flagging it teaches the reader to ignore this
    line. The signal is an out-of-key note that REPEATS, because a mis-assigned
    string produces the SAME wrong note in every bar the figure plays - which is
    exactly how nine bars of C# hid in a B-major song while agreeing perfectly
    with themselves.

    It REPORTS, it does not judge. A repeated off-key note is just as likely to
    be deliberate: a riff that leans on a flat five repeats its A#
    23 times and is entirely correct. Telling those apart needs an ear, so this
    hands the reader the fact and stops.

    Returns None when no key is declared - a check that cannot run says so.
    """
    raw = (song.META.get("key") or "").strip()
    if not raw:
        return None
    m = re.match(r"\s*([A-G][#b]?)\s*(major|minor|maj|min)?", raw, re.I)
    if not m:
        return None
    tonic = m.group(1).replace("b", "")
    if tonic not in _NAMES:
        return None
    minor = bool(m.group(2)) and m.group(2).lower().startswith("min")
    root = _NAMES.index(tonic)
    scale = {(root + i) % 12 for i in (_MIN if minor else _MAJ)}

    opens = open_pitches(song.META)
    off = {}
    for n, bar in sorted(song.BARS.items()):
        for slot in bar:
            if not slot:
                continue
            for st, (fret, _a) in slot.items():
                if not isinstance(fret, int) or st not in opens:
                    continue
                pc = (opens[st] + fret) % 12
                if pc not in scale:
                    off.setdefault(_NAMES[pc], []).append(n)
    return raw, off


def printed_runs(song):
    """The runs the PAGE prints, section by section - not a song-wide ideal.

    build() collapses INSIDE each section, so a repeating figure that straddles
    a section start is split and prints more columns than a song-wide collapse
    would. Computing the count the other way made the sheet state a number that
    was off by one here and off by two on the reference sheet: a Checked block
    whose own arithmetic is wrong is worse than no Checked block.

    This mirrors the renderer instead of counting what the renderer emitted -
    counting the output would make the check self-fulfilling.
    """
    BARS = song.BARS
    ranges = section_ranges(song.SECTIONS, BARS)
    lyr = getattr(song, "LYRICS", {})
    runs = []
    for start in sorted(song.SECTIONS):
        a, b = ranges[start]
        runs += collapse_runs(list(range(a, b + 1)), BARS, lyr)
    return runs


def verification_lines(song, slots, bars_per_system, widths=None, compact=True):
    """What was CHECKED about this sheet, as lines. A pure function of the song.

    Lives here, not in the verifier, so the sheet and the command cannot drift
    into disagreeing about the same facts. Deterministic on purpose - no clock,
    no render stats - because the .tab has to stay byte-stable.

    `compact` is which CUT this sheet is, and the repeats line reports what that
    cut actually prints. It used to report the collapse unconditionally, so a
    full-cut sheet - which collapses nothing - carried a line claiming a
    collapse it did not have. That is how a sheet with none of the reference
    sheet's repeat notation passed its own check.
    """
    BARS = song.BARS
    out = []
    bad = [k for k, v in BARS.items() if len(v) != slots]
    gap = [n for n in range(min(BARS), max(BARS) + 1) if n not in BARS]
    out.append("bars      %d encoded (%d-%d), all %d slots%s%s"
               % (len(BARS), min(BARS), max(BARS), slots,
                  "" if not bad else "  MALFORMED %s" % bad[:4],
                  "" if not gap else "  MISSING %s" % gap[:4]))

    runs = printed_runs(song)
    covered = [n for lo, hi, _ in runs for n in range(lo, hi + 1)]
    exact = covered == sorted(BARS)
    real = all(BARS[lo + r * p + k] == BARS[lo + k]
               for lo, hi, p in runs for r in range(1, (hi - lo + 1) // p)
               for k in range(p))
    if compact:
        out.append("repeats   compact cut; %d of %d bar columns printed; "
                   "partition %s; every repeat %s"
                   % (sum(p for _, _, p in runs), len(BARS),
                      "exact" if exact else "BROKEN",
                      "verified equal" if real else "NOT equal"))
    else:
        out.append("repeats   FULL cut; all %d bars printed individually, no "
                   "figure collapsed - the reference sheet uses the compact cut"
                   % len(BARS))

    used = sorted({a for b in BARS.values() for sl in b if sl
                   for _st, (_f, a) in sl.items() if a})
    stray = [m for m in used if m not in MARK_VOCAB]
    out.append("marks     %s%s" % (" ".join(used) or "none",
                                   "  STRAY %s" % stray if stray else
                                   " - all in the template vocabulary"))

    if widths:
        w = sorted(set(widths))
        out.append("scale     stave lines %s chars, %d bars/system%s"
                   % ("/".join(str(v) for v in w), bars_per_system,
                      ", within the 100-char bound" if max(w) <= 100
                      else ", OVER the 100-char bound"))

    kr = key_report(song)
    if kr is None:
        out.append("key       not checked - no key declared in META")
    else:
        raw, off = kr
        if not off:
            out.append("key       %s; every note diatonic" % raw)
        else:
            parts = []
            for note, bars_ in sorted(off.items(), key=lambda kv: -len(kv[1])):
                uniq = sorted(set(bars_))
                parts.append("%s in %d bar(s) %s%s"
                             % (note, len(uniq), uniq[:4],
                                "" if len(uniq) <= 4 else "..."))
            worst = max(len(set(b)) for b in off.values())
            out.append("key       %s; OFF-KEY: %s%s"
                       % (raw, "; ".join(parts),
                          "  - a single bar reads as a passing tone" if worst == 1
                          else "  - worth a look: a repeated off-key note is EITHER a"
                               " deliberate blues/chromatic tone or a wrong string"))
    return out
