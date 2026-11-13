"""Chart layout for chart2pdf: what goes on which line, from a song's data alone.

GENERAL - knows nothing about any particular song. A song file supplies
META / BARS / SECTIONS / CHORDS / LYRICS; this turns it into lines of bars with
section labels, collapsed repeats, chord names and per-bar lyrics.
"""

from __future__ import annotations

from tabcore import section_ranges, timestamp
from pdfkit import string_width

UNIT = 0.6                     # Courier digit advance, in em


class Cfg:
    """One rung of the fitting ladder. Spacing and repeats go first, the font last."""

    def __init__(self, fs, pad, secref, maxp, rhythm, t=None, pages=2):
        self.fs, self.pad, self.secref, self.maxp, self.rhythm, self.t = fs, pad, secref, maxp, rhythm, t
        self.pages = pages          # a rung bigger than the base size only counts if it fits this many


def ladder(t, expand=False):
    """The fitting ladder from a template; rungs under 9 pt were dropped by the loader.
    expand keeps a repeated section drawn out instead of reducing it to a reference line."""
    return [Cfg(r.fs, r.pad, r.secref and not expand, r.maxp, r.rhythm, t, getattr(r, "pages", 2))
            for r in t.ladder]


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
    """Natural width: the slots, widened if the chord or lyric over/under it is wider.
    A missing bar gets the width of the widest bar the song does have, never less."""
    c = plan_ctx(song, cfg)
    w = natural(num, song, cfg)
    return max(w, c["wide"]) if num in c["miss"] else w


def plan_ctx(song, cfg):
    """The missing and estimated bar sets and the widest non-missing bar, built once per song and rung."""
    c = getattr(cfg, "_ctx", None)
    if c is None or c["song"] is not song:
        c = cfg._ctx = {"song": song, "miss": missing(song), "est": estimates(song), "wide": 0.0}
        c["wide"] = max([natural(n, song, cfg) for n in song["bars"] if n not in c["miss"]] or [0.0])
    return c


def natural(num, song, cfg):
    w = sum(slot_widths(song["bars"][num], cfg)) + 6
    need = string_width(str(num), "F3", cfg.t.bar_numbers.size) + 3
    lyr = song["lyrics"].get(num) or ""
    if lyr:
        need = max(need, string_width(lyr, "F3", cfg.t.lyrics.size) + 4)
    ch = song["chords"].get(num) or ""
    room = sign_room(song, num, cfg)
    if ch or room:
        need = max(need, (string_width(ch, "F2", cfg.t.chords.size) + 4 if ch else 0.0) + room)
    return max(w, need)


def sign_room(song, num, cfg):
    """Width kept clear at the right of an estimated bar for its sign, so it never meets a chord name."""
    return cfg.t.marks.estimate_room if num in plan_ctx(song, cfg)["est"] else 0.0


def missing(song):
    """REPORT["missing"] bars: empty because the source lacks them, never a repeat or a reference."""
    return set((song.get("report") or {}).get("missing") or [])


def plain(song, n):
    """A missing bar that may join a run: no notes, no chord name, no lyric."""
    return not song["chords"].get(n) and not song["lyrics"].get(n) \
        and not any(song["bars"][n])


def missing_runs(song, a, b, miss):
    """Maximal (lo, hi) runs, hi > lo, of plain missing bars within a..b. One linear pass; a run
    never crosses a section start because the caller passes one section's range."""
    runs, lo = [], None
    for n in range(a, b + 2):
        if n <= b and n in miss and plain(song, n):
            lo = n if lo is None else lo
        else:
            if lo is not None and n - 1 > lo:
                runs.append((lo, n - 1))
            lo = None
    return runs


def estimates(song):
    """REPORT["estimates"] bars: guessed, so each keeps its own sign and is never folded away."""
    return set((song.get("report") or {}).get("estimates") or [])


def unfoldable(song):
    """The never-fold set: missing and estimated bars. Built once per planning pass."""
    return missing(song) | estimates(song)


class Fold:
    """What decides whether bars may fold: the never-fold set and each bar's effective chord
    (the last label in force, carried forward; "" before the first label)."""

    def __init__(self, song):
        self.unf, self.eff, cur = unfoldable(song), {}, ""
        for n in sorted(song["bars"]):
            cur = song["chords"].get(n) or cur
            self.eff[n] = cur


def base_ok(fold, bars):
    return not any(b in fold.unf for b in bars)


def rep_ok(fold, bars):
    return not any(b in fold.unf for b in bars)


def sec_target_ok(fold, a, b):
    return not any(x in fold.unf for x in range(a, b + 1))


def sec_new_ok(fold, a, b):
    return not any(x in fold.unf for x in range(a, b + 1))


def fig_chords_agree(fold, base, rep):
    return all(fold.eff.get(x, "") == fold.eff.get(y, "") for x, y in zip(base, rep))


def sec_chords_agree(fold, a, a2, n):
    return all(fold.eff.get(a + k, "") == fold.eff.get(a2 + k, "") for k in range(n))


def sections_identical(song, a, b, a2, b2, fold=None):
    fold = fold or Fold(song)
    if b - a != b2 - a2 or not sec_target_ok(fold, a, b) or not sec_new_ok(fold, a2, b2) \
            or not sec_chords_agree(fold, a, a2, b - a + 1):
        return False
    return all(song["bars"][a + k] == song["bars"][a2 + k]
               and (song["lyrics"].get(a + k) or "") == (song["lyrics"].get(a2 + k) or "")
               for k in range(b - a + 1))


def collapse(nums, song, cfg, starts, limit, fold=None):
    """[lo, period, reps] runs. A repeat never swallows a section start, never holds a missing or
    estimated bar, and a figure wider than a line is not collapsed. Notes, lyrics and the chord
    in force must match as well."""
    bars, lyr, out, i, n = song["bars"], song["lyrics"], [], 0, len(nums)
    fold = fold or Fold(song)
    while i < n:
        best = (1, 1)
        for p in range(1, cfg.maxp + 1):
            if i + p > n:
                break
            if any(nums[i + k] in starts for k in range(1, p)):
                break
            if sum(bar_width(nums[i + k], song, cfg) for k in range(p)) > limit:
                break
            reps, fig = 1, nums[i:i + p]
            while base_ok(fold, fig) and i + (reps + 1) * p <= n:
                j = i + reps * p
                cp = nums[j:j + p]
                if any(x in starts for x in cp) or not rep_ok(fold, cp) \
                        or not fig_chords_agree(fold, fig, cp) \
                        or any(bars[x] != bars[y] or (lyr.get(x) or "") != (lyr.get(y) or "")
                               for x, y in zip(cp, fig)):
                    break
                reps += 1
            if reps > 1 and reps * p > best[0] * best[1]:
                best = (p, reps)
        p, reps = best
        out.append([nums[i], p, reps])
        i += p * reps
    return out


def start_time(song, bar):
    """The section's start in the recording, from the tempo; "" when the song has no tempo."""
    try:
        tempo = float(song["meta"].get("tempo") or 0)
        return timestamp(bar, tempo) if 1 <= tempo < float("inf") else ""
    except (TypeError, ValueError, OverflowError):
        return ""


def shown_time(song, bar, cfg):
    """The start time as the chart prints it (the template's wording around it), or "" with no tempo."""
    tm = start_time(song, bar)
    return cfg.t.section.time.format(t=tm) if tm else ""


def plan_units(song, cfg, limit):
    """Ordered units: a one-line reference to an earlier identical section, or a run of bars."""
    ranges = section_ranges(song["sections"], song["bars"])
    starts = set(song["sections"])
    units, seen, fold = [], [], Fold(song)
    for s in sorted(song["sections"]):
        a, b = ranges[s]
        name = song["sections"][s]["name"]
        ref = next((t for t in seen if sections_identical(song, *ranges[t], a, b, fold)), None) \
            if cfg.secref and b > a else None
        if ref is not None:
            units.append({"kind": "ref", "label": name, "time": shown_time(song, a, cfg), "sec": s,
                          "text": cfg.t.section.ref.format(other=song["sections"][ref]["name"],
                                                           a=ranges[ref][0], b=ranges[ref][1])})
        else:
            miss, pos = missing(song), a
            parts = []
            for lo, hi in missing_runs(song, a, b, miss):
                parts += [("bars", pos, lo - 1), ("gap", lo, hi)]
                pos = hi + 1
            parts.append(("bars", pos, b))
            for k, (kind, x, y) in enumerate(parts):
                if y < x:
                    continue
                if kind == "gap":
                    units.append({"kind": "gap", "bars": list(range(x, y + 1)), "reps": 1,
                                  "label": name if x == a else None, "sec": s,
                                  "time": shown_time(song, a, cfg) if x == a else "",
                                  "text": cfg.t.marks.missing_run.format(a=x, b=y), "width": limit})
                    continue
                for lo, p, reps in collapse(list(range(x, y + 1)), song, cfg, starts, limit, fold):
                    units.append({"kind": "bars", "bars": list(range(lo, lo + p)), "reps": reps,
                                  "label": name if lo == a else None, "sec": s, "after_gap": x != a,
                                  "before_gap": k + 1 < len(parts),
                                  "time": shown_time(song, a, cfg) if lo == a else "",
                                  "width": sum(bar_width(z, song, cfg) for z in range(lo, lo + p))
                                  + (18 if reps > 1 else 0)})
        seen.append(s)
    return units


def continues(g):
    """A group that follows a run in its own section is that section's tail."""
    return g[0].get("after_gap", False)


def pack(units, avail, lab_size=10.0, time_size=8.0):
    """Greedy lines, one section at a time. A section starts a new line unless the line already
    holds only whole sections and this one fits whole beside them, so the last bars of one
    section never share a line with the start of the next. A label never runs into the previous one."""
    lines, cur, x, label_end, tail = [], [], 0.0, -1.0, False
    groups = []
    for u in units:
        if groups and groups[-1][0].get("sec") == u.get("sec") and u["kind"] == "bars" == groups[-1][0]["kind"]:
            groups[-1].append(u)
        else:
            groups.append([u])
    for g in groups:
        if g[0]["kind"] in ("ref", "gap"):
            if cur:
                lines.append(cur)
            lines.append(g)
            cur, x, label_end, tail = [], 0.0, -1.0, False
            continue
        whole = not g[0].get("before_gap", False)     # bars that run into a run are not a whole section
        if cur and (tail or not whole or x + sum(u["width"] for u in g) > avail or x < label_end):
            lines.append(cur)
            cur, x, label_end, tail = [], 0.0, -1.0, False
        for u in g:
            if cur and x + u["width"] > avail:
                lines.append(cur)
                cur, x, label_end, tail = [], 0.0, -1.0, True
            cur.append(u)
            if u["label"]:
                label_end = x + string_width(u["label"], "F2", lab_size) + 6 + (
                    string_width(u["time"], "F3", time_size) + 4 if u["time"] else 0)
            x += u["width"]
        if continues(g):
            tail = True
    if cur:
        lines.append(cur)
    return lines
