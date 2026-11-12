"""The chart's one format template: loader, header block and source report text.

GENERAL - the layout lives in templates/chart-format.json; this reads it, checks
it, and turns a song's fields into the header and report lines it asks for.
Code keeps the fitting algorithm and the BAS-3 limits; the template cannot loosen them.
"""

from __future__ import annotations

import json
import math
import os
import string
from types import SimpleNamespace

from tabcore import open_pitches

DEFAULT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "templates",
                       "chart-format.json")
MIN_FS = 9.0                     # tab digits are never smaller (BAS-3)
REQUIRED = ["missing_text", "title_row.left", "title_row.right", "title_row.size",
            "title_row.right_size", "header", "header_size", "report.heading", "report.size",
            "report.parts", "report.none_text", "section.size", "section.repeat",
            "section.ref", "section.time", "section.time_size", "section.count_gap", "bar_numbers.size", "marks.missing",
            "marks.size", "marks.estimate_size", "marks.estimate_room", "staff.label_size", "staff.gap", "staff.clef", "chords.size",
            "lyrics.size", "ladder"]
SIZES = ["title_row.size", "title_row.right_size", "header_size", "report.size", "section.size", "section.time_size", "section.count_gap",
         "bar_numbers.size", "marks.size", "marks.estimate_size", "marks.estimate_room", "staff.label_size", "staff.gap", "chords.size", "lyrics.size"]


def _bad(path, why):
    raise SystemExit("chart2pdf: template %s %s" % (path, why))


def _ns(x):
    if isinstance(x, dict):
        return SimpleNamespace(**{k: _ns(v) for k, v in x.items()})
    return [_ns(v) for v in x] if isinstance(x, list) else x


def _num(v, low=None):
    """A finite number above 0 (or at least LOW when given); anything else is a bad value."""
    if isinstance(v, bool):
        raise ValueError(v)
    v = float(v)
    if not math.isfinite(v) or (v < low if low is not None else v <= 0):
        raise ValueError(v)
    return v


def _fields(fmt, allowed):
    """Only bare {name} placeholders from ALLOWED: no format spec, conversion or attribute."""
    for _, name, spec, conv in string.Formatter().parse(fmt):
        if name is not None and (name not in allowed or spec or conv):
            raise ValueError(name)


def load(path=None):
    path = path or DEFAULT
    try:
        with open(path, encoding="utf-8") as fh:
            raw = json.load(fh)
    except OSError:
        _bad(path, "cannot be read")
    except ValueError:
        _bad(path, "is not valid JSON")
    for key in REQUIRED:
        cur = raw
        for part in key.split("."):
            if not isinstance(cur, dict) or part not in cur:
                _bad(path, "is missing key '%s'" % key)
            cur = cur[part]
    try:
        for r in raw["ladder"]:
            r["fs"], r["pad"] = _num(r["fs"]), _num(r["pad"], 0.0)
            r["pages"] = r.get("pages", 2)
            if isinstance(r["pages"], bool) or r["pages"] not in (1, 2):
                raise ValueError("ladder")
            if isinstance(r["maxp"], bool) or not isinstance(r["maxp"], int) or r["maxp"] < 1 or \
                    not all(isinstance(r[k], bool) for k in ("secref", "rhythm")):
                raise ValueError("ladder")
        # The code keeps the fitting order: bigger digits first, the template's order within a size.
        raw["ladder"] = sorted((r for r in raw["ladder"] if r["fs"] >= MIN_FS), key=lambda r: -r["fs"])
        for key in SIZES:
            *up, last = key.split(".")
            cur = raw
            for part in up:
                cur = cur[part]
            cur[last] = _num(cur[last])
        if raw["marks"]["estimate_room"] < raw["marks"]["estimate_size"]:
            raise ValueError("estimate_room")       # the sign must fit the room kept for it
        texts = [raw["title_row"]["left"], raw["title_row"]["right"], raw["missing_text"],
                 raw["report"]["heading"], raw["report"]["none_text"]]
        texts += [h[k] for h in raw["header"] for k in ("field", "label")]
        texts.append(raw["marks"]["missing"])
        texts += [p[k] for p in raw["report"]["parts"] for k in ("key", "label")]
        if not all(isinstance(x, str) for x in texts):
            raise ValueError("text")
        _fields(raw["section"]["repeat"], {"n"})
        _fields(raw["section"]["ref"], {"other", "a", "b"})
        _fields(raw["section"]["time"], {"t"})
    except (KeyError, IndexError, ValueError, TypeError):
        _bad(path, "has a bad value (a ladder rung, a size, a placeholder or a field entry)")
    if not raw["ladder"]:
        _bad(path, "has no ladder rung at %.0f pt or more" % MIN_FS)
    if any(p["key"] not in ("missing", "estimates", "sections") for p in raw["report"]["parts"]):
        _bad(path, "report parts must be missing, estimates, sections")
    return _ns(raw)


def sources(meta):
    """META sources (or source) as a list of strings; a plain string is one source."""
    v = meta.get("sources") or meta.get("source") or []
    return [str(s) for s in v] if isinstance(v, (list, tuple)) else [str(v)]


def _val(meta, field):
    """The field's text, or "" when the song has no value for it."""
    v = "; ".join(sources(meta)) if field == "sources" else meta.get(field)
    return str(v) if v not in (None, "", []) else ""


def title_parts(meta, t):
    left, right = (str(meta.get(k)) if meta.get(k) else "" for k in (t.title_row.left, t.title_row.right))
    return [left or t.missing_text, right]      # no artist: the right side is left out


def header_text(meta, t):
    return "   ·   ".join("%s: %s" % (h.label, _val(meta, h.field))
                         for h in t.header if _val(meta, h.field))     # a field with no value is left out


def check_song(song, name):
    """Refuse a song whose own fields contradict each other (one line, naming it)."""
    meta, rep = song["meta"], song["report"]
    if meta.get("source") and meta.get("sources"):
        raise SystemExit("%s sets both source and sources; keep one" % name)
    rows = song["rows"]
    if not song["bars"]:
        raise SystemExit("%s: BARS is empty" % name)
    if len(rows) == 4 and "B" in (meta.get("open") or {}):
        raise SystemExit("%s: META open names a B string, but the song is 4-string" % name)
    try:
        open_pitches(meta)
    except ValueError as e:
        raise SystemExit("%s: %s" % (name, e))
    for n, bar in song["bars"].items():
        for slot in bar:
            for st in (slot or {}):
                if st not in rows:
                    raise SystemExit("%s: bar %s uses string %s, which a %d-string bass lacks"
                                     % (name, n, st, len(rows)))
    if not isinstance(rep, dict) or set(rep) - {"missing", "estimates", "sections"}:
        raise SystemExit("%s: REPORT keys are missing, estimates, sections" % name)
    for k in ("missing", "estimates"):
        v = rep.get(k)
        if v is not None and not (isinstance(v, (list, tuple)) and
                                  all(isinstance(b, int) and not isinstance(b, bool) for b in v)):
            raise SystemExit("%s: REPORT %s must be a list of bar numbers" % (name, k))
        for b in v or []:
            if b not in song["bars"]:
                raise SystemExit("%s: REPORT %s names bar %d, which is not in BARS" % (name, k, b))
    listed = list(rep.get("missing") or []) + list(rep.get("estimates") or [])
    if len(listed) != len(set(listed)):
        raise SystemExit("%s: REPORT names a bar more than once (in missing or estimates)" % name)
    if rep.get("sections") is not None and not isinstance(rep["sections"], dict):
        raise SystemExit("%s: REPORT sections must map a section start bar to its source" % name)
    for b in (rep.get("sections") or {}):
        if b not in song["sections"]:
            raise SystemExit("%s: REPORT sections key %r is not a section start bar" % (name, b))


def report_hidden(rep, parts):
    """True when the report says nothing: absent, None, or no list set and no section source named.
    An explicit empty missing or estimates list is "checked, none", so it keeps the report."""
    if not rep:
        return True
    lists = [p.key for p in parts if p.key != "sections"]
    return all(rep.get(k) is None for k in lists) and not any((rep.get("sections") or {}).values())


def report_lines(song, ranges, t):
    """[(text, bold)] for the report block: heading, then each part in template order."""
    rep, none, miss = song.get("report") or {}, t.report.none_text, t.missing_text
    if report_hidden(rep, t.report.parts):
        return []                                  # every line would read "not shown": leave it out
    out = [(t.report.heading, True)]
    for p in t.report.parts:
        v = rep.get(p.key)
        if p.key == "sections":
            out.append((p.label + ":", False))
            for s in sorted(song["sections"]):
                a, b = ranges[s]
                src = (v or {}).get(s) or miss
                out.append(("%s (bars %d-%d): %s" % (song["sections"][s]["name"], a, b, src), False))
        elif v is None:
            out.append(("%s: %s" % (p.label, miss), False))
        else:
            out.append(("%s: %s" % (p.label, ", ".join(str(x) for x in v) if v else none), False))
    return out
