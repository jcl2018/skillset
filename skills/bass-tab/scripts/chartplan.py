"""Chart layout for chart2pdf: what goes on which line, from a song's data alone.

GENERAL - knows nothing about any particular song. A song file supplies
META / BARS / SECTIONS / CHORDS / LYRICS; this turns it into lines of bars with
section labels, collapsed repeats, chord names and per-bar lyrics.
"""

from __future__ import annotations

from tabcore import section_ranges
from pdfkit import string_width

UNIT = 0.6                     # Courier digit advance, in em


class Cfg:
    """One rung of the fitting ladder. Spacing and repeats go first, the font last."""

    def __init__(self, fs, pad, secref, maxp, rhythm, t=None):
        self.fs, self.pad, self.secref, self.maxp, self.rhythm, self.t = fs, pad, secref, maxp, rhythm, t


def ladder(t):
    """The fitting ladder from a template; rungs under 9 pt were dropped by the loader."""
    return [Cfg(r.fs, r.pad, r.secref, r.maxp, r.rhythm, t) for r in t.ladder]


def slot_widths(bar, cfg):
    out = []
    for sl in bar:
        if sl:
            chars = max(len(str(f)) for f, _a in sl.values())
            out.append(chars * UNIT * cfg.fs + 2.5 * cfg.pad)
        else:
            out.append(2.2 * cfg.pad)
    return out


def bar_width(num, song, cfg):
    """Natural width: the slots, widened if the chord or lyric over/under it is wider."""
    w = sum(slot_widths(song["bars"][num], cfg)) + 6
    need = 0.0
    lyr = song["lyrics"].get(num) or ""
    if lyr:
        need = string_width(lyr, "F3", cfg.t.lyrics.size) + 4
    ch = song["chords"].get(num) or ""
    if ch:
        need = max(need, string_width(ch, "F2", cfg.t.chords.size) + 4)
    return max(w, need)


def sections_identical(song, a, b, a2, b2):
    if b - a != b2 - a2:
        return False
    return all(song["bars"][a + k] == song["bars"][a2 + k]
               and (song["lyrics"].get(a + k) or "") == (song["lyrics"].get(a2 + k) or "")
               for k in range(b - a + 1))


def collapse(nums, song, cfg, starts, limit):
    """[lo, period, reps] runs. A repeat never swallows a section start, and a
    figure wider than a line is not collapsed. Lyrics must match as well as notes."""
    bars, lyr, out, i, n = song["bars"], song["lyrics"], [], 0, len(nums)
    while i < n:
        best = (1, 1)
        for p in range(1, cfg.maxp + 1):
            if i + p > n:
                break
            if any(nums[i + k] in starts for k in range(1, p)):
                break
            if sum(bar_width(nums[i + k], song, cfg) for k in range(p)) > limit:
                break
            reps = 1
            while i + (reps + 1) * p <= n:
                j = i + reps * p
                if any(nums[j + k] in starts or bars[nums[j + k]] != bars[nums[i + k]]
                       or (lyr.get(nums[j + k]) or "") != (lyr.get(nums[i + k]) or "")
                       for k in range(p)):
                    break
                reps += 1
            if reps > 1 and reps * p > best[0] * best[1]:
                best = (p, reps)
        p, reps = best
        out.append([nums[i], p, reps])
        i += p * reps
    return out


def plan_units(song, cfg, limit):
    """Ordered units: a one-line reference to an earlier identical section, or a run of bars."""
    ranges = section_ranges(song["sections"], song["bars"])
    starts = set(song["sections"])
    units, seen = [], []
    for s in sorted(song["sections"]):
        a, b = ranges[s]
        name = song["sections"][s]["name"]
        ref = next((t for t in seen if sections_identical(song, *ranges[t], a, b)), None) \
            if cfg.secref and b > a else None
        if ref is not None:
            units.append({"kind": "ref", "label": name,
                          "text": cfg.t.section.ref.format(other=song["sections"][ref]["name"],
                                                           a=ranges[ref][0], b=ranges[ref][1])})
        else:
            for k, (lo, p, reps) in enumerate(collapse(list(range(a, b + 1)), song, cfg, starts, limit)):
                units.append({"kind": "bars", "bars": list(range(lo, lo + p)), "reps": reps,
                              "label": name if lo == a else None,
                              "width": sum(bar_width(x, song, cfg) for x in range(lo, lo + p))
                              + (18 if reps > 1 else 0)})
        seen.append(s)
    return units


def pack(units, avail, lab_size=10.0):
    """Greedy lines. A label that would run into the previous label starts a new line."""
    lines, cur, x, label_end = [], [], 0.0, -1.0
    for u in units:
        if u["kind"] == "ref":
            if cur:
                lines.append(cur)
            lines.append([u])
            cur, x, label_end = [], 0.0, -1.0
            continue
        lab_w = string_width(u["label"], "F2", lab_size) + 6 if u["label"] else 0
        if cur and (x + u["width"] > avail or (u["label"] and x < label_end)):
            lines.append(cur)
            cur, x, label_end = [], 0.0, -1.0
        cur.append(u)
        if u["label"]:
            label_end = x + lab_w
        x += u["width"]
    if cur:
        lines.append(cur)
    return lines
