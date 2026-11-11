"""The chart's one format template: loader, header block and source report text.

GENERAL - the layout lives in templates/chart-format.json; this reads it, checks
it, and turns a song's fields into the header and report lines it asks for.
Code keeps the fitting algorithm and the BAS-3 limits; the template cannot loosen them.
"""

from __future__ import annotations

import json
import os
from types import SimpleNamespace

DEFAULT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "templates",
                       "chart-format.json")
MIN_FS = 9.0                     # tab digits are never smaller (BAS-3)
REQUIRED = ["missing_text", "title_row.left", "title_row.right", "title_row.size",
            "title_row.right_size", "header", "header_size", "report.heading", "report.size",
            "report.parts", "report.none_text", "section.size", "section.repeat",
            "section.ref", "staff.label_size", "staff.gap", "staff.clef", "chords.size",
            "lyrics.size", "ladder"]


def _bad(path, why):
    raise SystemExit("chart2pdf: template %s %s" % (path, why))


def _ns(x):
    if isinstance(x, dict):
        return SimpleNamespace(**{k: _ns(v) for k, v in x.items()})
    return [_ns(v) for v in x] if isinstance(x, list) else x


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
            r["fs"], r["pad"], r["maxp"] = float(r["fs"]), float(r["pad"]), int(r["maxp"])
            r["secref"], r["rhythm"] = bool(r["secref"]), bool(r["rhythm"])
        raw["ladder"] = [r for r in raw["ladder"] if r["fs"] >= MIN_FS]
        raw["section"]["repeat"].format(n=2)
        raw["section"]["ref"].format(other="x", a=1, b=2)
        for h in raw["header"]:
            h["field"], h["label"]
        for p in raw["report"]["parts"]:
            p["key"], p["label"]
    except (KeyError, IndexError, ValueError, TypeError):
        _bad(path, "has a bad value (a ladder rung, a placeholder or a field entry)")
    if not raw["ladder"]:
        _bad(path, "has no ladder rung at %.0f pt or more" % MIN_FS)
    if any(p["key"] not in ("missing", "estimates", "sections") for p in raw["report"]["parts"]):
        _bad(path, "report parts must be missing, estimates, sections")
    return _ns(raw)


def _val(meta, field, t):
    if field == "sources":
        v = meta.get("sources") or ([meta["source"]] if meta.get("source") else [])
        v = "; ".join(str(s) for s in v)
    else:
        v = meta.get(field)
    return str(v) if v not in (None, "", []) else t.missing_text


def title_parts(meta, t):
    return [(str(meta.get(k)) if meta.get(k) else t.missing_text)
            for k in (t.title_row.left, t.title_row.right)]


def header_text(meta, t):
    return "   ·   ".join("%s: %s" % (h.label, _val(meta, h.field, t)) for h in t.header)


def check_song(song, name):
    """Refuse a song whose own fields contradict each other (one line, naming it)."""
    meta, rep = song["meta"], song["report"]
    if meta.get("source") and meta.get("sources"):
        raise SystemExit("%s sets both source and sources; keep one" % name)
    rows = song["rows"]
    if len(rows) == 4 and "B" in (meta.get("open") or {}):
        raise SystemExit("%s: META open names a B string, but the song is 4-string" % name)
    for n, bar in song["bars"].items():
        for slot in bar:
            for st in (slot or {}):
                if st not in rows:
                    raise SystemExit("%s: bar %s uses string %s, which a %d-string bass lacks"
                                     % (name, n, st, len(rows)))
    if not isinstance(rep, dict) or set(rep) - {"missing", "estimates", "sections"}:
        raise SystemExit("%s: REPORT keys are missing, estimates, sections" % name)
    for k in ("missing", "estimates"):
        for b in rep.get(k) or []:
            if isinstance(b, int) and b not in song["bars"]:
                raise SystemExit("%s: REPORT %s names bar %d, which is not in BARS" % (name, k, b))
    for b in (rep.get("sections") or {}):
        if b not in song["sections"]:
            raise SystemExit("%s: REPORT sections key %r is not a section start bar" % (name, b))


def report_lines(song, ranges, t):
    """[(text, bold)] for the report block: heading, then each part in template order."""
    rep, none, miss = song["report"], t.report.none_text, t.missing_text
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
